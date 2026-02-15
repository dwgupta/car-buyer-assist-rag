"""
Car Buyer Assist RAG - Main entry point.

Run with: streamlit run main.py

Uses st.navigation and st.Page so the sidebar shows custom titles and icons
for Home, Connectivity, Document Processing, Interactive Assistant, and Observability.
"""

import streamlit as st

pages = [
    st.Page("app.py", title="Home", icon="🚗", default=True),
    st.Page("pages/1_Connectivity.py", title="Connectivity", icon="🔌"),
    st.Page("pages/2_Document_Processing.py", title="Document Processing", icon="📄"),
    st.Page("pages/3_Interactive_Assistant.py", title="Interactive Assistant", icon="💬"),
    st.Page("pages/4_Observability.py", title="Observability", icon="📊"),
]

st.navigation(pages).run()
