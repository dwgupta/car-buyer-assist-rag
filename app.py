"""
Car Buyer Assist RAG - Learning Page

A simple educational page that introduces the application and guides users
on what queries they can ask. No dashboard, no navigation to other pages.
"""

import streamlit as st

# Page config
st.set_page_config(
    page_title="Car Buyer Assist - Learn",
    page_icon="🚗",
    layout="wide",
)

# Header
st.title("Car Buyer Assist")
st.caption("Get instant, accurate answers about Toyota vehicles using conversational AI")

st.divider()

# What & Why sections
with st.container():
    st.subheader("What is Car Buyer Assist?")
    st.write(
        "Car Buyer Assist is a conversational AI system that helps prospective car buyers "
        "get instant, accurate answers about Toyota vehicles by asking natural language questions. "
        "The system uses **Retrieval-Augmented Generation (RAG)** to ground responses in official "
        "Toyota specification documents, ensuring accuracy while providing a natural chat experience."
    )

    st.subheader("Why does it exist?")
    st.write(
        "Current car buying research is frustrating: customers must manually search through dense PDF spec sheets, "
        "comparing features across models requires significant effort, and sales representatives aren't always "
        "available for quick questions. This application demonstrates how RAG technology can provide immediate, "
        "accurate vehicle information through conversational queries."
    )

st.divider()

# Vehicle models
st.subheader("Vehicle Coverage")
st.write("The system covers **8 Toyota models** across diverse segments:")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown("**Sedans**")
    st.write("Corolla")
    st.write("Camry")
with col2:
    st.markdown("**SUVs**")
    st.write("RAV4")
    st.write("Highlander")
with col3:
    st.markdown("**Hybrids**")
    st.write("Prius")
    st.write("Prius Prime")
with col4:
    st.markdown("**Truck**")
    st.write("Tacoma")
with col5:
    st.markdown("**Electric**")
    st.write("bZ4X")

st.divider()

# Sample queries (grouped by type, in expanders)
st.subheader("Sample Query Types")
st.write("You can ask questions across these categories:")

with st.expander("Specification Queries", expanded=False):
    st.markdown("- \"What is the fuel efficiency of the Camry hybrid?\"")
    st.markdown("- \"How much horsepower does the RAV4 Prime have?\"")
    st.markdown("- \"What is the towing capacity of the Tacoma V6?\"")
    st.markdown("- \"What is the electric range of the bZ4X?\"")

with st.expander("Comparison Queries", expanded=False):
    st.markdown("- \"Compare fuel efficiency between Prius and Prius Prime\"")
    st.markdown("- \"What are the differences between RAV4 and Highlander?\"")
    st.markdown("- \"Which sedan is better for first-time buyers?\"")
    st.markdown("- \"How does the Camry compare to the Honda Accord?\"")

with st.expander("Feature & Safety Queries", expanded=False):
    st.markdown("- \"What safety features does the Corolla have?\"")
    st.markdown("- \"Does the Highlander have third-row seating?\"")
    st.markdown("- \"What technology features are in the RAV4?\"")
    st.markdown("- \"Is AWD available on the Camry?\"")

with st.expander("Pricing & Value Queries", expanded=False):
    st.markdown("- \"What is the starting price of the Corolla?\"")
    st.markdown("- \"Which Toyota SUV offers the best value?\"")
    st.markdown("- \"What trim levels are available for the Tacoma?\"")

with st.expander("Recommendation Queries", expanded=False):
    st.markdown("- \"What Toyota vehicle is best for a family of five?\"")
    st.markdown("- \"I need a fuel-efficient car for city driving, what do you recommend?\"")
    st.markdown("- \"Which hybrid has the longest electric range?\"")

st.divider()

# RAG explained
st.subheader("What is RAG?")
st.write(
    "**Retrieval-Augmented Generation (RAG)** means the AI does not guess or fabricate answers. "
    "When you ask a question, the system first searches the official Toyota specification documents, "
    "retrieves the most relevant passages, and then generates a response grounded in that retrieved context. "
    "If the information is not in the documents, the system will acknowledge that rather than inventing an answer."
)

st.divider()

# Footer
st.caption("Coming soon: document upload and chat assistant")
