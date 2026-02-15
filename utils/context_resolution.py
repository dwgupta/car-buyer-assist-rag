"""
Context resolution for the Interactive Assistant: resolve pronouns and references
(e.g. "it", "that car") to a concrete Toyota model name using the last exchange.
"""

import logging
import os
import re
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langsmith import traceable

from config import VEHICLE_MODELS, VERTEX_AI_MODEL

logger = logging.getLogger(__name__)

# Pronouns and phrases that suggest a reference to the last discussed vehicle
REFERENCE_PATTERN = re.compile(
    r"\b(it|its|that car|this (?:model|vehicle|car)|the same (?:one|vehicle|car))\b",
    re.IGNORECASE,
)

RESOLUTION_SYSTEM_PROMPT = """You are resolving references in a follow-up question about Toyota vehicles.

Given:
1. The last user question
2. The last assistant answer (about a Toyota model)
3. The current user question

Output ONLY the current question with any pronouns or vague references (e.g. "it", "that car", "this model") replaced by the specific Toyota model name from the conversation. Use only model names from this list: {models}.

If there is nothing to resolve, output the current question exactly as given. Output one line only, no explanation."""


def _needs_resolution(query: str) -> bool:
    """Return True if the query looks like it may contain a reference to resolve."""
    if not query or len(query.strip()) > 500:
        return False
    return bool(REFERENCE_PATTERN.search(query))


@traceable(name="context_resolution", run_type="chain", tags=["context", "assistant"])
def resolve_reference(
    current_query: str,
    last_user: str | None,
    last_assistant: str | None,
    vehicle_models: List[str] | None = None,
) -> str:
    """
    Resolve pronouns/references in current_query to a vehicle name using the last exchange.

    Args:
        current_query: The user's current question (e.g. "What is the base price of it?").
        last_user: Previous user message (e.g. "What are the safety features of Corolla?").
        last_assistant: Previous assistant reply (may mention the vehicle).
        vehicle_models: Allowed model names; defaults to config VEHICLE_MODELS.

    Returns:
        Resolved query (e.g. "What is the base price of the Corolla?") or current_query unchanged.
    """
    models = vehicle_models or VEHICLE_MODELS
    if not current_query or not _needs_resolution(current_query):
        return current_query.strip()

    if not (last_user or last_assistant):
        return current_query.strip()

    prompt = RESOLUTION_SYSTEM_PROMPT.format(models=", ".join(models))

    user_content = f"""Last user question: {last_user or "(none)"}

Last assistant answer: {last_assistant or "(none)"}

Current user question: {current_query}

Output the current question with references resolved (one line only):"""

    llm = ChatGoogleGenerativeAI(
        model=VERTEX_AI_MODEL,
        vertexai=True,
        project=os.getenv("GOOGLE_PROJECT_ID"),
        location=os.getenv("GOOGLE_REGION", "us-central1"),
        temperature=0.0,
        max_output_tokens=256,
    )

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=user_content),
    ]
    response = llm.invoke(messages)
    resolved = getattr(response, "content", str(response))
    if not isinstance(resolved, str):
        resolved = str(resolved)
    resolved = resolved.strip().strip('"').strip("'")
    return resolved if resolved else current_query.strip()
