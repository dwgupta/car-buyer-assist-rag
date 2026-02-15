"""
Car Buyer Assist RAG - Home Page (Landing with Dashboard)

Welcome screen with quick stats, system status, navigation cards, and sample queries.
"""

import logging

import streamlit as st
from dotenv import load_dotenv

from config import (
    APP_DESCRIPTION,
    APP_TITLE,
    CHROMA_DB_PATH,
    EXAMPLE_QUERIES,
    VEHICLE_MODELS,
    VERTEX_AI_MODEL,
)
from utils.connectivity import run_all_checks
from utils.document_processor import (
    get_chromadb_chunk_count,
    get_documents_in_knowledge_base,
    get_models_in_knowledge_base,
)
from utils.logging_config import setup_logging

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=f"{APP_TITLE} - Home",
    page_icon="🚗",
    layout="wide",
)

st.title(APP_TITLE)
st.caption(APP_DESCRIPTION)

logger.debug("Rendering home page")

# Quick statistics (robust to ChromaDB errors)
try:
    chunk_count = get_chromadb_chunk_count()
    doc_sources = get_documents_in_knowledge_base()
    doc_count = len(doc_sources)
    models_in_kb = get_models_in_knowledge_base()
except Exception as e:
    logger.warning("Could not load KB stats for dashboard: %s", e)
    chunk_count = 0
    doc_count = 0
    models_in_kb = []

st.subheader("Quick statistics")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total chunks", chunk_count)
with col2:
    st.metric("Total documents", doc_count)
with col3:
    models_str = ", ".join(models_in_kb) if models_in_kb else "None"
    st.metric("Models in KB", models_str)

# System status
if chunk_count and chunk_count > 0:
    st.success("**Knowledge base:** Ready. You can ask questions in the Interactive Assistant.")
else:
    st.info("**Knowledge base:** Empty. Process documents on the **Document Processing** page to get started.")

try:
    with st.spinner("Checking services..."):
        connectivity_results = run_all_checks(
            chroma_path=CHROMA_DB_PATH,
            vertex_model=VERTEX_AI_MODEL,
        )
    all_ok = all(success for _, (success, _) in connectivity_results.items())
    if all_ok:
        st.success("**System:** Healthy")
    else:
        st.error("**System:** Unhealthy")
except Exception as e:
    logger.warning("Connectivity check failed on home dashboard: %s", e)
    st.error("**System:** Unhealthy")

# Navigation cards
st.subheader("Navigate")
card_cols = st.columns(4)
cards = [
    ("pages/1_Connectivity.py", "Connectivity", "🔌", "Verify ChromaDB, Vertex AI, LangSmith"),
    ("pages/2_Document_Processing.py", "Document Processing", "📄", "Upload and process Toyota PDFs"),
    ("pages/3_Interactive_Assistant.py", "Interactive Assistant", "💬", "Chat and ask questions"),
    ("pages/4_Observability.py", "Observability", "📊", "View traces and metrics"),
]
for col, (page_path, title, icon, desc) in zip(card_cols, cards):
    with col:
        with st.container():
            st.markdown(f"**{icon} {title}**")
            st.caption(desc)
            st.page_link(page_path, label="Open", icon=icon)

st.divider()

st.write(
    "Car Buyer Assist helps prospective car buyers get instant answers about Toyota vehicles "
    "by asking natural language questions. It uses official specification documents to ground "
    "responses, so you can skip manual PDF searching and get accurate information on demand."
)

st.write("**Models covered:** " + ", ".join(VEHICLE_MODELS))

st.write("**Example questions:**")
for query in EXAMPLE_QUERIES:
    st.markdown(f"- {query}")
