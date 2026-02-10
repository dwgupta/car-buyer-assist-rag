"""
Car Buyer Assist RAG - Learning Page

A simple educational page that introduces the application.
"""

import logging

import streamlit as st

from config import APP_DESCRIPTION, APP_TITLE, EXAMPLE_QUERIES, VEHICLE_MODELS
from utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=f"{APP_TITLE} - Learn",
    page_icon="🚗",
    layout="wide",
)

st.title(APP_TITLE)
st.caption(APP_DESCRIPTION)

logger.debug("Rendering learning page")

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
