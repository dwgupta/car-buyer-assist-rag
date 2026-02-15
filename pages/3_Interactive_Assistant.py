"""
Interactive Assistant Page

Chat interface for asking questions about Toyota vehicles using the RAG system.
Maintains conversation context so follow-ups (e.g. "What is the base price of it?")
refer to the last discussed vehicle. Answers are grounded only in Toyota specification documents.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dotenv import load_dotenv

from config import APP_TITLE, CONVERSATION_STARTERS
from utils.context_resolution import resolve_reference
from utils.document_processor import get_chromadb_chunk_count
from utils.logging_config import setup_logging
from utils.rag_chain import invoke as rag_invoke

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=f"Assistant - {APP_TITLE}",
    page_icon="💬",
    layout="wide",
)

st.title("Interactive Assistant")
st.caption("Ask questions about Toyota vehicles. Answers are based only on the uploaded specification documents.")

# Session state for chat messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Warn if knowledge base is empty
chunk_count = get_chromadb_chunk_count()
if chunk_count == 0:
    st.warning(
        "The knowledge base has no documents yet. Process PDFs on the **Document Processing** page first, then return here to ask questions."
    )
    st.stop()

def _get_last_exchange(messages: list) -> tuple[str | None, str | None]:
    """Return (last_user_content, last_assistant_content) from message list."""
    last_user = None
    last_assistant = None
    for m in reversed(messages):
        if m["role"] == "assistant" and last_assistant is None:
            last_assistant = m.get("content", "")
        elif m["role"] == "user" and last_user is None:
            last_user = m.get("content", "")
            break
    return last_user, last_assistant


def _generate_response(prompt: str, history: list) -> tuple[str, list]:
    """Resolve reference if needed, call RAG, return (answer, sources)."""
    resolved_query = None
    if len(history) >= 1:
        last_user, last_assistant = _get_last_exchange(history)
        resolved = resolve_reference(prompt, last_user, last_assistant)
        if resolved != prompt:
            resolved_query = resolved

    try:
        result = rag_invoke(
            query=prompt,
            conversation_history=history,
            resolved_query=resolved_query,
        )
        return result.get("answer", "I couldn't generate an answer."), result.get("sources", [])
    except Exception as e:
        logger.exception("RAG invoke failed: %s", e)
        return "Sorry, something went wrong while answering. Please try again.", []


# Conversation starters: clickable buttons (append user message and rerun; response generated on next run)
st.subheader("Conversation starters")
cols = st.columns(min(len(CONVERSATION_STARTERS), 4))
for i, starter in enumerate(CONVERSATION_STARTERS):
    with cols[i % len(cols)]:
        if st.button(starter, key=f"starter_{i}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": starter})
            st.rerun()

st.divider()

# Chat history: render all messages so the user query shows as soon as it's added
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("Sources"):
                for s in msg["sources"]:
                    st.caption(f"- {s.get('source', 'Unknown')}")

# If the last message is from the user, we have an unanswered query: show "Thinking..." and generate response
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    pending_content = st.session_state.messages[-1]["content"]
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]][-6:]
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer, sources = _generate_response(pending_content, history)
        st.markdown(answer)
        if sources:
            with st.expander("Sources"):
                for s in sources:
                    st.caption(f"- {s.get('source', 'Unknown')}")
    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
    st.rerun()

# Clear conversation
if st.session_state.messages and st.button("Clear conversation", type="secondary"):
    st.session_state.messages = []
    st.rerun()

# Chat input: append user message and rerun immediately so the query appears, then next run will generate response
if prompt := st.chat_input("Ask about Toyota vehicles..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()
