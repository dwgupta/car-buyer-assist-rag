"""
Car Buyer Assist RAG - Learning Page

A simple educational page that introduces the application.
"""

import streamlit as st

st.set_page_config(
    page_title="Car Buyer Assist - Learn",
    page_icon="🚗",
    layout="wide",
)

st.title("Car Buyer Assist")
st.caption("Get instant, accurate answers about Toyota vehicles using conversational AI")

st.divider()

st.write(
    "Car Buyer Assist helps prospective car buyers get instant answers about Toyota vehicles "
    "by asking natural language questions. It uses official specification documents to ground "
    "responses, so you can skip manual PDF searching and get accurate information on demand."
)

st.write("**Models covered:** Corolla, Camry, RAV4, Highlander, Prius, Prius Prime, Tacoma, bZ4X")

st.write("**Example questions:**")
st.markdown("- What is the fuel efficiency of the Camry hybrid?")
st.markdown("- Compare RAV4 and Highlander for families")
st.markdown("- What safety features does the Corolla have?")
st.markdown("- What Toyota vehicle is best for a family of five?")
