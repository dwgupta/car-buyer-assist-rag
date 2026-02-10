"""
Connectivity Validation Page

Validates connections to ChromaDB, Vertex AI, and LangSmith.
Displays green tick for success, red tick for failure.
"""

import logging
import os
import sys
from pathlib import Path

# Ensure project root is on path when running as Streamlit page
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dotenv import load_dotenv

from config import CHROMA_DB_PATH, VERTEX_AI_MODEL
from utils.connectivity import run_all_checks
from utils.logging_config import setup_logging

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Connectivity - Car Buyer Assist",
    page_icon="🔌",
    layout="wide",
)

st.title("Connectivity Validation")
st.caption("Verify all external service connections before processing documents or queries")

st.divider()

if st.button("Test All Connections", type="primary"):
    logger.info("User triggered connectivity validation")
    with st.spinner("Running connectivity checks..."):
        results = run_all_checks(
            chroma_path=CHROMA_DB_PATH,
            vertex_model=VERTEX_AI_MODEL,
        )

    st.divider()

    for service, (success, message) in results.items():
        if success:
            st.markdown(f"**{service}** — :green[✓ Connected]")
        else:
            st.markdown(f"**{service}** — :red[✗ Failed]")
        st.caption(message)
        st.write("")

else:
    st.info(
        "Click **Test All Connections** to validate ChromaDB, Vertex AI, and LangSmith."
    )

with st.expander("Configuration", expanded=False):
    st.write("**ChromaDB:**", os.path.abspath(CHROMA_DB_PATH))
    st.write(
        "**Vertex AI:**",
        f"Project: {os.getenv('GOOGLE_PROJECT_ID', 'Not set')}, "
        f"Region: {os.getenv('GOOGLE_REGION', 'Not set')}",
    )
    st.write("**LangSmith:**", f"Project: {os.getenv('LANGSMITH_PROJECT', 'Not set')}")
