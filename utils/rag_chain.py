"""
RAG chain for Car Buyer Assist: retrieval from ChromaDB and response generation via Vertex AI.

Provides get_vectorstore(), retrieve(), and invoke() for the Interactive Assistant.
Answers are grounded only in retrieved Toyota specification context; citations included.
"""

import logging
import os
from typing import Any

from langchain_community.vectorstores import Chroma
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langsmith import traceable

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_PATH,
    EMBEDDING_MODEL,
    VERTEX_AI_MODEL,
)

logger = logging.getLogger(__name__)

# System prompt per Design doc §3.2: answer only from context, cite sources, decline when not in context
RAG_SYSTEM_PROMPT = """You are a helpful Toyota car sales assistant. Answer questions based ONLY on the provided context from Toyota specification documents.

Rules:
- If the information is not in the context, say "I don't have that information in the available Toyota specifications."
- Do not use external knowledge or guess.
- Always cite the source document when providing answers (e.g. "According to [filename]...").
- Give complete answers: finish every sentence and section. For comparisons, cover both options fully before ending."""

# Number of chunks to retrieve (Design doc §3.2)
RETRIEVE_K = 5

# LLM settings per Design doc §3.2 (higher max for comparison/long answers)
LLM_TEMPERATURE = 0.3
LLM_MAX_OUTPUT_TOKENS = 2048

# Relevance gate: Chroma returns cosine *distance* (lower = more relevant).
# If the best retrieval distance is above this, we skip the LLM and return out-of-scope message.
RELEVANCE_DISTANCE_THRESHOLD = 0.85

OUT_OF_CONTEXT_ANSWER = "I don't have that information in the available Toyota specifications. I can only answer questions about Toyota vehicles using the uploaded specification documents."


def get_vectorstore() -> Chroma:
    """Build and return Chroma vectorstore using existing config and embeddings."""
    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        vertexai=True,
        project=os.getenv("GOOGLE_PROJECT_ID"),
        location=os.getenv("GOOGLE_REGION", "us-central1"),
    )
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_PATH,
    )


def retrieve(query: str, k: int = RETRIEVE_K) -> list[dict[str, Any]]:
    """
    Embed the query, run similarity search, return list of doc dicts with content and metadata.

    Each dict has: content (str), source (str), page (optional), model_name (optional).
    """
    vectorstore = get_vectorstore()
    docs = vectorstore.similarity_search(query, k=k)
    return [
        {
            "content": d.page_content,
            "source": d.metadata.get("source", "Unknown"),
            "page": d.metadata.get("page"),
            "model_name": d.metadata.get("model_name"),
        }
        for d in docs
    ]


def _retrieve_with_scores(query: str, k: int = RETRIEVE_K) -> tuple[list[dict[str, Any]], list[float]]:
    """
    Same as retrieve but also returns similarity scores (cosine distance; lower = more relevant).
    """
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_score(query, k=k)
    docs = []
    scores = []
    for d, score in results:
        docs.append({
            "content": d.page_content,
            "source": d.metadata.get("source", "Unknown"),
            "page": d.metadata.get("page"),
            "model_name": d.metadata.get("model_name"),
        })
        scores.append(float(score))
    return docs, scores


def _build_context_block(docs: list[dict[str, Any]]) -> str:
    """Format retrieved chunks as a single context string for the prompt."""
    parts = []
    for i, d in enumerate(docs, 1):
        source = d.get("source", "Unknown")
        content = d.get("content", "")
        parts.append(f"[{i}] Source: {source}\n{content}")
    return "\n\n---\n\n".join(parts)


def _build_conversation_block(conversation_history: list[dict]) -> str:
    """Format last 1-2 exchanges for context."""
    if not conversation_history:
        return ""
    lines = []
    for msg in conversation_history[-4:]:  # last 2 exchanges (user + assistant each)
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
    if not lines:
        return ""
    return "Recent conversation:\n" + "\n".join(lines) + "\n\n"


@traceable(name="rag_invoke", run_type="chain", tags=["rag", "assistant"])
def invoke(
    query: str,
    conversation_history: list[dict],
    resolved_query: str | None = None,
) -> dict[str, Any]:
    """
    Run RAG: retrieve using resolved_query or query, then generate answer from context.

    Args:
        query: Original user question (used in prompt for clarity).
        conversation_history: List of {"role": "user"|"assistant", "content": str}.
        resolved_query: If set, use for retrieval (e.g. "What is the base price of the Corolla?").

    Returns:
        {"answer": str, "sources": list[dict]} with source metadata for citations.
    """
    search_query = resolved_query if resolved_query else query
    docs, scores = _retrieve_with_scores(search_query, k=RETRIEVE_K)

    # Skip LLM for out-of-context queries: if best match is too far (high distance), return decline message.
    best_distance = min(scores) if scores else float("inf")
    if not docs or best_distance > RELEVANCE_DISTANCE_THRESHOLD:
        logger.info("Skipping LLM: query out of context (best distance=%.3f, threshold=%.2f)", best_distance, RELEVANCE_DISTANCE_THRESHOLD)
        return {"answer": OUT_OF_CONTEXT_ANSWER, "sources": []}

    context_block = _build_context_block(docs)
    conversation_block = _build_conversation_block(conversation_history)

    user_prompt = f"""{conversation_block}Current question: {query}

Use the following context from Toyota specification documents to answer. If the answer is not in the context, say you don't have that information.

Context:
{context_block}"""

    llm = ChatGoogleGenerativeAI(
        model=VERTEX_AI_MODEL,
        vertexai=True,
        project=os.getenv("GOOGLE_PROJECT_ID"),
        location=os.getenv("GOOGLE_REGION", "us-central1"),
        temperature=LLM_TEMPERATURE,
        max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
    )

    messages = [
        SystemMessage(content=RAG_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)

    answer = getattr(response, "content", str(response))
    if not isinstance(answer, str):
        answer = str(answer)

    # Deduplicate sources by filename for citation list
    seen = set()
    sources = []
    for d in docs:
        src = d.get("source")
        if src and src not in seen:
            seen.add(src)
            sources.append({"source": src, "page": d.get("page"), "model_name": d.get("model_name")})

    return {"answer": answer, "sources": sources}
