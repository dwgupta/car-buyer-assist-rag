"""
Document processing pipeline for Car Buyer Assist RAG.

Loads PDFs via LangChain PyPDFLoader, chunks text, generates embeddings via Vertex AI,
and stores in ChromaDB. Supports page selection and progress callbacks.
Integrates with LangSmith for observability (traces, latency, costs).
"""

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Callable, Generator

from langchain_community.document_loaders import PyPDFLoader
from langsmith import traceable
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_PATH,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, float], None]


def _page_matches(doc, selected_pages: list[int]) -> bool:
    """
    Check if document's page is in selected_pages.
    UI uses 1-indexed (1,2,3...). PyPDFLoader metadata can be 0 or 1-indexed.
    """
    p = doc.metadata.get("page", 0)
    if isinstance(p, str):
        try:
            p = int(p)
        except ValueError:
            return False
    return (p + 1) in selected_pages or p in selected_pages


def _extract_model_name(filename: str) -> str:
    """Extract vehicle model name from filename (e.g. Toyota_Camry_Specifications.pdf -> Camry)."""
    name = Path(filename).stem
    # Remove common prefixes
    for prefix in ("Toyota_", "Introduction_to_", "Introduction_to_Toyota_"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    # Remove _Specifications suffix
    name = re.sub(r"_Specifications?$", "", name, flags=re.I)
    return name or "Unknown"


def get_pdf_page_count(file_path: str) -> int:
    """
    Get the number of pages in a PDF without full text extraction.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Number of pages in the PDF.
    """
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    return len(reader.pages)


def get_chromadb_chunk_count() -> int:
    """Return the number of chunks in the ChromaDB knowledge base."""
    try:
        import chromadb

        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
        return collection.count()
    except Exception:
        return 0


def get_documents_in_knowledge_base() -> set[str]:
    """Return set of source filenames that have chunks in the knowledge base."""
    try:
        import chromadb

        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
        if collection.count() == 0:
            return set()
        data = collection.get(include=["metadatas"])
        sources = set()
        for m in (data.get("metadatas") or []):
            if m and "source" in m:
                sources.add(m["source"])
        return sources
    except Exception:
        return set()


def clear_chromadb_knowledge_base() -> bool:
    """Delete the ChromaDB collection (clears all chunks). Returns True on success."""
    try:
        import chromadb

        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        try:
            client.delete_collection(name=CHROMA_COLLECTION_NAME)
        except Exception:
            pass  # Collection may not exist
        return True
    except Exception as e:
        logger.exception("Failed to clear ChromaDB: %s", e)
        return False


def remove_documents_from_knowledge_base(filenames: list[str]) -> tuple[bool, int]:
    """Remove chunks for given source filenames from the knowledge base. Returns (success, chunks_removed)."""
    if not filenames:
        return True, 0
    try:
        import chromadb

        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
        count_before = collection.count()
        collection.delete(where={"source": {"$in": filenames}})
        count_after = collection.count()
        return True, count_before - count_after
    except Exception as e:
        logger.exception("Failed to remove documents: %s", e)
        return False, 0


def load_and_preview_pdf(
    file_path: str,
    max_preview_chars: int = 500,
) -> tuple[list[dict], int]:
    """
    Load a PDF and return page-level preview info without full processing.

    Args:
        file_path: Path to the PDF file.
        max_preview_chars: Maximum characters to include in preview text.

    Returns:
        Tuple of (list of dicts with page_num, preview_text), total_page_count.
    """
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    if not docs:
        return [], 0

    previews = []
    for doc in docs:
        page_num = doc.metadata.get("page", 0)
        text = (doc.page_content or "").strip()
        preview_text = text[:max_preview_chars] + ("..." if len(text) > max_preview_chars else "")
        previews.append({"page": page_num, "preview": preview_text})

    return previews, len(docs)


@traceable(
    name="document_processing",
    run_type="chain",
    tags=["document_processing", "ingestion"],
)
def process_documents(
    file_paths: list[str],
    page_selections: dict[str, list[int] | None],
    progress_callback: ProgressCallback | None = None,
    path_to_filename: dict[str, str] | None = None,
) -> dict:
    """
    Process PDF documents: extract, chunk, embed, and store in ChromaDB.

    Args:
        file_paths: List of paths to PDF files.
        page_selections: Dict mapping filename to list of page numbers to process,
            or None to process all pages. Page numbers are 1-indexed.
        progress_callback: Optional callback(status: str, progress: float) for UI updates.
        path_to_filename: Optional mapping from file_path to display filename for
            page_selection lookup (used when file_paths are temp files).

    Returns:
        Dict with keys: documents_processed, total_chunks, processing_time_sec, models_covered, errors.
    """
    if progress_callback:
        progress_callback("Initializing...", 0.0)

    # Enable LangSmith tracing for observability
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_TRACING_V2"] = "true"

    results = {
        "documents_processed": 0,
        "total_chunks": 0,
        "processing_time_sec": 0.0,
        "models_covered": [],
        "errors": [],
    }

    import time

    start_time = time.perf_counter()

    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            vertexai=True,
            project=os.getenv("GOOGLE_PROJECT_ID"),
            location=os.getenv("GOOGLE_REGION", "us-central1"),
        )
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )

        vectorstore = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH,
        )

        all_chunks: list = []
        total_files = len(file_paths)

        for idx, file_path in enumerate(file_paths):
            filename = (path_to_filename or {}).get(file_path) or Path(file_path).name
            selected_pages = page_selections.get(filename) or page_selections.get(file_path)

            if progress_callback:
                pct = idx / total_files * 100
                progress_callback(f"Extracting text from {filename}...", pct)

            try:
                loader = PyPDFLoader(file_path)
                docs = loader.load()

                if selected_pages is not None:
                    docs = [d for d in docs if _page_matches(d, selected_pages)]

                if not docs:
                    results["errors"].append(f"No content from {filename} (selected pages may be empty)")
                    continue

                model_name = _extract_model_name(filename)
                if model_name not in results["models_covered"]:
                    results["models_covered"].append(model_name)

                if progress_callback:
                    progress_callback(f"Chunking {filename}...", (idx + 0.3) / total_files * 100)

                chunks = text_splitter.split_documents(docs)

                for i, chunk in enumerate(chunks):
                    chunk.metadata["source"] = filename
                    chunk.metadata["chunk_index"] = i
                    chunk.metadata["model_name"] = model_name
                    if "page" not in chunk.metadata:
                        chunk.metadata["page"] = chunk.metadata.get("page", 0)

                all_chunks.extend(chunks)
                results["documents_processed"] += 1

            except Exception as e:
                logger.exception("Error processing %s", file_path)
                results["errors"].append(f"{filename}: {str(e)}")

        if not all_chunks:
            results["processing_time_sec"] = time.perf_counter() - start_time
            return results

        if progress_callback:
            progress_callback("Generating embeddings...", 85.0)

        vectorstore.add_documents(all_chunks)

        if progress_callback:
            progress_callback("Storing vectors...", 95.0)

        results["total_chunks"] = len(all_chunks)
        results["processing_time_sec"] = time.perf_counter() - start_time

        if progress_callback:
            progress_callback("Complete", 100.0)

    except Exception as e:
        logger.exception("Document processing failed")
        results["errors"].append(str(e))
        if progress_callback:
            progress_callback("Error", 100.0)

    return results


@traceable(
    name="document_processing_generator",
    run_type="chain",
    tags=["document_processing", "ingestion"],
)
def process_documents_generator(
    file_paths: list[str],
    page_selections: dict[str, list[int] | None],
    path_to_filename: dict[str, str] | None = None,
) -> Generator[tuple[str, float, dict | None], None, None]:
    """
    Generator version of process_documents that yields (status, progress, result) for Streamlit UI.
    Yields after each step so the UI can update in real time.
    Final yield has result dict; all other yields have result=None.
    """
    yield "Initializing...", 0.0, None

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_TRACING_V2"] = "true"

    results = {
        "documents_processed": 0,
        "total_chunks": 0,
        "processing_time_sec": 0.0,
        "models_covered": [],
        "errors": [],
    }

    import time

    start_time = time.perf_counter()

    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            vertexai=True,
            project=os.getenv("GOOGLE_PROJECT_ID"),
            location=os.getenv("GOOGLE_REGION", "us-central1"),
        )
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )

        vectorstore = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH,
        )

        all_chunks: list = []
        total_files = len(file_paths)

        for idx, file_path in enumerate(file_paths):
            filename = (path_to_filename or {}).get(file_path) or Path(file_path).name
            selected_pages = page_selections.get(filename) or page_selections.get(file_path)

            yield f"Extracting text from {filename}...", (idx / total_files) * 80, None

            try:
                loader = PyPDFLoader(file_path)
                docs = loader.load()

                if selected_pages is not None:
                    docs = [d for d in docs if _page_matches(d, selected_pages)]

                if not docs:
                    results["errors"].append(f"No content from {filename} (selected pages may be empty)")
                    continue

                model_name = _extract_model_name(filename)
                if model_name not in results["models_covered"]:
                    results["models_covered"].append(model_name)

                yield f"Chunking {filename}...", ((idx + 0.5) / total_files) * 80, None

                chunks = text_splitter.split_documents(docs)

                for i, chunk in enumerate(chunks):
                    chunk.metadata["source"] = filename
                    chunk.metadata["chunk_index"] = i
                    chunk.metadata["model_name"] = model_name
                    if "page" not in chunk.metadata:
                        chunk.metadata["page"] = chunk.metadata.get("page", 0)

                all_chunks.extend(chunks)
                results["documents_processed"] += 1

            except Exception as e:
                logger.exception("Error processing %s", file_path)
                results["errors"].append(f"{filename}: {str(e)}")

        if not all_chunks:
            results["processing_time_sec"] = time.perf_counter() - start_time
            yield "Complete (no chunks created)", 100.0, results
            return

        yield "Generating embeddings...", 85.0, None

        vectorstore.add_documents(all_chunks)

        yield "Storing vectors...", 95.0, None

        results["total_chunks"] = len(all_chunks)
        results["processing_time_sec"] = time.perf_counter() - start_time

        yield "Complete", 100.0, results

    except Exception as e:
        logger.exception("Document processing failed")
        results["errors"].append(str(e))
        yield "Error", 100.0, results


def process_uploaded_files(
    uploaded_files: list,
    page_selections: dict[str, list[int] | None],
    progress_callback: ProgressCallback | None = None,
) -> dict:
    """
    Process Streamlit uploaded file objects.

    Writes each to a temp file and delegates to process_documents.

    Args:
        uploaded_files: List of Streamlit UploadedFile objects.
        page_selections: Dict mapping filename to list of page numbers or None.
        progress_callback: Optional callback for progress updates.

    Returns:
        Same as process_documents.
    """
    temp_paths = []
    path_to_filename = {}
    try:
        for uf in uploaded_files:
            suffix = Path(uf.name).suffix or ".pdf"
            fd, path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            with open(path, "wb") as f:
                f.write(uf.getvalue())
            temp_paths.append(path)
            path_to_filename[path] = uf.name

        selections = {uf.name: page_selections.get(uf.name) for uf in uploaded_files}

        return process_documents(
            temp_paths, selections, progress_callback, path_to_filename=path_to_filename
        )
    finally:
        for p in temp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass


def process_uploaded_files_generator(
    uploaded_files: list,
    page_selections: dict[str, list[int] | None],
) -> Generator[tuple[str, float, dict | None], None, None]:
    """
    Generator version for Streamlit: yields (status, progress, result) for real-time UI updates.
    """
    temp_paths = []
    path_to_filename = {}
    try:
        for uf in uploaded_files:
            suffix = Path(uf.name).suffix or ".pdf"
            fd, path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            with open(path, "wb") as f:
                f.write(uf.getvalue())
            temp_paths.append(path)
            path_to_filename[path] = uf.name

        selections = {uf.name: page_selections.get(uf.name) for uf in uploaded_files}

        for status, progress, result in process_documents_generator(
            temp_paths, selections, path_to_filename=path_to_filename
        ):
            yield status, progress, result
    finally:
        for p in temp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass
