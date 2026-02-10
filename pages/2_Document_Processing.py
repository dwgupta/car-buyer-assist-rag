"""
Document Processing Page

Upload Toyota specification PDFs, select pages for processing, preview documents,
and ingest into the vector database with progress tracking.
"""

import logging
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dotenv import load_dotenv

from config import APP_TITLE
from utils.document_processor import (
    clear_chromadb_knowledge_base,
    get_chromadb_chunk_count,
    get_documents_in_knowledge_base,
    get_pdf_page_count,
    load_and_preview_pdf,
    process_uploaded_files_generator,
    remove_documents_from_knowledge_base,
)
from utils.logging_config import setup_logging

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=f"Document Processing - {APP_TITLE}",
    page_icon="📄",
    layout="wide",
)

st.title("Document Processing")
st.caption("Upload and process Toyota specification PDFs to build the knowledge base")

# Knowledge base stats (always visible)
chunk_count_placeholder = st.empty()
with chunk_count_placeholder.container():
    st.metric("Chunks in knowledge base", get_chromadb_chunk_count())

with st.expander("Clear knowledge base", expanded=False):
    st.caption(
        "This will permanently delete all chunks in the knowledge base. "
        "You will need to re-process documents to add them back."
    )
    confirm_clear = st.checkbox(
        "I understand this will delete all chunks in the knowledge base",
        key="confirm_clear_kb",
    )
    if st.button(
        "Clear knowledge base",
        type="secondary",
        disabled=not confirm_clear,
        key="clear_kb_btn",
    ):
        if clear_chromadb_knowledge_base():
            st.success("Knowledge base cleared.")
            st.rerun()
        else:
            st.error("Failed to clear knowledge base.")

st.divider()

# File upload
uploaded_files = st.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True,
    help="Select one or more Toyota specification PDFs for processing.",
)

if not uploaded_files:
    st.info("Upload one or more PDF files to get started.")

else:
    # Session state for page selections and document info
    if "page_selections" not in st.session_state:
        st.session_state.page_selections = {}
    if "doc_info" not in st.session_state:
        st.session_state.doc_info = {}

    # Build doc info (page count) for newly uploaded files
    for uf in uploaded_files:
        if uf.name not in st.session_state.doc_info:
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(uf.getvalue())
                    tmp_path = tmp.name
                try:
                    page_count = get_pdf_page_count(tmp_path)
                    st.session_state.doc_info[uf.name] = {
                        "pages": page_count,
                        "size_kb": len(uf.getvalue()) / 1024,
                    }
                finally:
                    os.unlink(tmp_path)
            except Exception as e:
                logger.exception("Error reading %s", uf.name)
                st.session_state.doc_info[uf.name] = {"pages": 0, "size_kb": 0, "error": str(e)}

    # File selection for processing
    file_options = [uf.name for uf in uploaded_files]
    files_to_process = st.multiselect(
        "Files to process",
        options=file_options,
        default=file_options,
        help="Select which files to process. Choose all or a subset.",
    )

    kb_sources = get_documents_in_knowledge_base()

    # Page selection and document preview per file
    for uf in uploaded_files:
        info = st.session_state.doc_info.get(uf.name, {})
        page_count = info.get("pages", 0)
        size_kb = info.get("size_kb", 0)

        with st.expander(f"**{uf.name}** — {page_count} pages, {size_kb:.1f} KB", expanded=True):
            # Page selection
            if page_count > 0:
                page_options = list(range(1, page_count + 1))
                default = list(range(1, page_count + 1))  # All pages by default

                selected = st.multiselect(
                    "Pages to process",
                    options=page_options,
                    default=default,
                    key=f"pages_{uf.name}",
                    help="Select which pages to include. Select all for full document, or empty for none.",
                )
                st.session_state.page_selections[uf.name] = selected
            else:
                st.warning("Could not read page count.")
                st.session_state.page_selections[uf.name] = None

            # Document preview
            if st.button("Preview text", key=f"preview_{uf.name}"):
                try:
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(uf.getvalue())
                        tmp_path = tmp.name
                    try:
                        previews, _ = load_and_preview_pdf(tmp_path, max_preview_chars=500)
                        for p in previews:
                            st.markdown(f"**Page {p['page'] + 1}**")
                            st.text(p["preview"][:500] + ("..." if len(p["preview"]) > 500 else ""))
                            st.divider()
                    finally:
                        os.unlink(tmp_path)
                except Exception as e:
                    st.error(f"Preview failed: {e}")

            # Remove from knowledge base (only if file is in KB)
            if uf.name in kb_sources:
                if st.button("Remove from knowledge base", key=f"remove_{uf.name}"):
                    success, removed = remove_documents_from_knowledge_base([uf.name])
                    if success:
                        st.success(f"Removed {removed} chunks. You can re-upload and re-process if needed.")
                        st.rerun()
                    else:
                        st.error("Failed to remove from knowledge base.")

    st.divider()

    # Process button
    if st.button("Process Documents", type="primary"):
        if not files_to_process:
            st.warning("Select at least one file to process.")
        else:
            selected_files = [uf for uf in uploaded_files if uf.name in files_to_process]
            page_selections = st.session_state.get("page_selections", {})
            for uf in selected_files:
                if uf.name not in page_selections:
                    page_selections[uf.name] = None

            progress_bar = st.progress(0.0)
            status_container = st.empty()

            result = None
            for status, progress, res in process_uploaded_files_generator(
                selected_files, page_selections
            ):
                progress_bar.progress(progress / 100.0)
                status_container.write(status)
                if res is not None:
                    result = res

            progress_bar.empty()
            status_container.empty()

            if result:
                # Update the top metric with fresh count
                with chunk_count_placeholder.container():
                    st.metric("Chunks in knowledge base", get_chromadb_chunk_count())
                st.divider()
                st.subheader("Processing Complete")

                if result["errors"]:
                    for err in result["errors"]:
                        st.error(err)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Documents processed", result["documents_processed"])
                with col2:
                    st.metric("Total chunks created", result["total_chunks"])
                with col3:
                    st.metric("Time (seconds)", f"{result['processing_time_sec']:.1f}")
                with col4:
                    st.metric("Chunks in knowledge base (updated)", get_chromadb_chunk_count())

                if result["models_covered"]:
                    st.write("**Models covered:**", ", ".join(result["models_covered"]))

                st.success("Documents have been added to the knowledge base.")
                st.info("Go to the **Interactive Assistant** to start asking questions.")

    # Document status table (refresh kb_sources for accurate status after processing or removal)
    st.subheader("Document status")
    kb_sources = get_documents_in_knowledge_base()
    table_rows = []
    for uf in uploaded_files:
        info = st.session_state.doc_info.get(uf.name, {})
        page_count = info.get("pages", 0)
        size_kb = info.get("size_kb", 0)
        status = "In knowledge base" if uf.name in kb_sources else "Not in knowledge base"
        table_rows.append({
            "Document": uf.name,
            "Pages": page_count,
            "Size (KB)": round(size_kb, 1),
            "Status": status,
        })
    st.dataframe(table_rows, use_container_width=True)
