"""
Connectivity validation utilities.

Validates connections to ChromaDB, Vertex AI, and LangSmith.
Extracted for testability and reuse across the application.
"""

import logging
import os
from typing import TypeAlias

ValidationResult: TypeAlias = tuple[bool, str]

logger = logging.getLogger(__name__)

# ChromaDB test collection settings
CHROMA_TEST_COLLECTION = "connectivity_test"
CHROMA_TEST_EMBEDDING_DIM = 384


def validate_chromadb(chroma_path: str | None = None) -> ValidationResult:
    """
    Validate ChromaDB connection and read/write access.

    Args:
        chroma_path: Path to ChromaDB persistence directory. Defaults to ./chroma_db.

    Returns:
        Tuple of (success: bool, message: str).
    """
    path = chroma_path or "./chroma_db"
    logger.debug("Validating ChromaDB at path=%s", path)
    try:
        import chromadb

        client = chromadb.PersistentClient(path=path)
        collection = client.get_or_create_collection(
            name=CHROMA_TEST_COLLECTION,
            metadata={"description": "Ephemeral collection for connectivity test"},
        )
        collection.add(
            ids=["connectivity-test-id"],
            embeddings=[[0.0] * CHROMA_TEST_EMBEDDING_DIM],
            documents=["connectivity test"],
        )
        results = collection.get(ids=["connectivity-test-id"])
        client.delete_collection(CHROMA_TEST_COLLECTION)
        if results and len(results["ids"]) > 0:
            logger.info("ChromaDB validation succeeded")
            return True, "Connected"
        logger.warning("ChromaDB validation: read/write check failed")
        return False, "Read/write check failed"
    except Exception as e:
        logger.exception("ChromaDB validation failed: %s", e)
        return False, str(e)


def validate_vertex_ai(
    model_id: str = "gemini-2.5-pro",
    project_id: str | None = None,
    region: str | None = None,
) -> ValidationResult:
    """
    Validate Vertex AI connection and model generation.

    Args:
        model_id: Vertex AI model identifier.
        project_id: GCP project ID. Uses GOOGLE_PROJECT_ID env if not provided.
        region: GCP region. Uses GOOGLE_REGION env if not provided.

    Returns:
        Tuple of (success: bool, message: str).
    """
    proj = project_id or os.getenv("GOOGLE_PROJECT_ID")
    reg = region or os.getenv("GOOGLE_REGION", "us-central1")
    if not proj:
        logger.warning("Vertex AI validation skipped: GOOGLE_PROJECT_ID not set")
        return False, "GOOGLE_PROJECT_ID not set"

    logger.debug("Validating Vertex AI: model=%s, project=%s, region=%s", model_id, proj, reg)
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel

        vertexai.init(project=proj, location=reg)
        model = GenerativeModel(model_id)
        response = model.generate_content("Say OK in one word.")
        if response and response.text:
            logger.info("Vertex AI validation succeeded (model=%s)", model_id)
            return True, "Connected"
        logger.warning("Vertex AI validation: no response from model")
        return False, "No response from model"
    except Exception as e:
        logger.exception("Vertex AI validation failed: %s", e)
        return False, str(e)


def validate_langsmith() -> ValidationResult:
    """
    Validate LangSmith API key and trace capability.

    Returns:
        Tuple of (success: bool, message: str).
    """
    if not os.getenv("LANGSMITH_API_KEY"):
        logger.warning("LangSmith validation skipped: LANGSMITH_API_KEY not set")
        return False, "LANGSMITH_API_KEY not set"

    logger.debug("Validating LangSmith connection")
    try:
        from langsmith import Client

        client = Client()
        list(client.list_projects())
        logger.info("LangSmith validation succeeded")
        return True, "Connected"
    except Exception as e:
        logger.exception("LangSmith validation failed: %s", e)
        return False, str(e)


def run_all_checks(
    chroma_path: str | None = None,
    vertex_model: str = "gemini-2.5-pro",
) -> dict[str, ValidationResult]:
    """
    Run all connectivity checks.

    Args:
        chroma_path: Path to ChromaDB directory. Optional.
        vertex_model: Vertex AI model ID. Optional.

    Returns:
        Dict mapping service name to (success, message) tuple.
    """
    logger.info("Running all connectivity checks")
    results = {
        "ChromaDB": validate_chromadb(chroma_path),
        f"Vertex AI ({vertex_model})": validate_vertex_ai(model_id=vertex_model),
        "LangSmith": validate_langsmith(),
    }
    passed = sum(1 for ok, _ in results.values() if ok)
    logger.info("Connectivity checks complete: %d/%d passed", passed, len(results))
    return results
