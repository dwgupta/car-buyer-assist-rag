"""
Observability / Monitoring Page

Displays LangSmith traces in-app, grouped by document_processing, context_resolution,
and rag_invoke. Summary metrics and per-category tables with links to LangSmith.
"""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dotenv import load_dotenv

from config import APP_TITLE
from utils.logging_config import setup_logging
from utils.observability import (
    CATEGORY_CONTEXT_RESOLUTION,
    CATEGORY_DOCUMENT_PROCESSING,
    CATEGORY_RAG_INVOKE,
    get_langsmith_project_url,
    get_runs_by_category,
)

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=f"Observability - {APP_TITLE}",
    page_icon="📊",
    layout="wide",
)

st.title("Observability")
st.caption("Monitor traces and metrics from LangSmith without leaving the app.")

# Require LangSmith config
project_name = os.getenv("LANGSMITH_PROJECT", "").strip()
if not os.getenv("LANGSMITH_API_KEY") or not project_name:
    st.warning(
        "**LangSmith is not configured.** Set `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT` in your `.env` to view traces. "
        "You can validate the connection on the **Connectivity** page."
    )
    langsmith_url = get_langsmith_project_url(project_name or "car-buyer-assist-rag")
    st.info(f"Full traces: [Open LangSmith]({langsmith_url})")
    st.stop()

# Time range
time_range = st.selectbox(
    "Time range",
    options=["Last 1 hour", "Last 24 hours", "Last 7 days"],
    index=1,
    key="observability_time_range",
)
now = datetime.now(timezone.utc)
if time_range == "Last 1 hour":
    start_time = now - timedelta(hours=1)
elif time_range == "Last 24 hours":
    start_time = now - timedelta(days=1)
else:
    start_time = now - timedelta(days=7)

if st.button("Refresh traces", type="primary"):
    st.rerun()

st.divider()

# Fetch data
with st.spinner("Loading traces from LangSmith..."):
    data = get_runs_by_category(project_name=project_name, start_time=start_time, limit_per_type=50)

if data.error_message:
    st.error(data.error_message)
    langsmith_url = get_langsmith_project_url(project_name)
    st.info(f"Full traces: [Open in LangSmith]({langsmith_url})")
    st.stop()

# Link to LangSmith project observability page (car-buyer-assist-rag)
langsmith_url = get_langsmith_project_url(project_name)
st.markdown(f"**Full traces:** [Open in LangSmith]({langsmith_url}) (project: `{project_name}`)")

# Summary metrics
st.subheader("Summary")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total runs", data.summary_total_runs)
with col2:
    st.metric("Total tokens", data.summary_total_tokens or "—")
with col3:
    doc_metrics = data.metrics_by_category.get(CATEGORY_DOCUMENT_PROCESSING)
    st.metric("Document processing runs", doc_metrics.total_runs if doc_metrics else 0)
with col4:
    rag_metrics = data.metrics_by_category.get(CATEGORY_RAG_INVOKE)
    st.metric("RAG invoke runs", rag_metrics.total_runs if rag_metrics else 0)

# Per-category metrics (avg latency, success rate)
st.subheader("Metrics by category")
for cat_key, display_name in [
    (CATEGORY_DOCUMENT_PROCESSING, "Document processing"),
    (CATEGORY_CONTEXT_RESOLUTION, "Context resolution"),
    (CATEGORY_RAG_INVOKE, "RAG invoke"),
]:
    m = data.metrics_by_category.get(cat_key)
    if not m:
        continue
    success_pct = (100 * m.success_count / m.total_runs) if m.total_runs else 0
    avg_s = f"{m.avg_latency_s:.2f}s" if m.avg_latency_s is not None else "—"
    line = f"**{display_name}:** {m.total_runs} runs, avg latency {avg_s}, success rate {success_pct:.0f}%, tokens {m.total_tokens or 0}"
    if cat_key == CATEGORY_RAG_INVOKE:
        cost_str = f"${m.total_cost:.4f}" if m.total_cost > 0 else "—"
        line += f", total cost {cost_str}"
    st.markdown(line)

st.divider()

# Tabs: Document processing | Context resolution | RAG invoke
tab_doc, tab_ctx, tab_rag = st.tabs(["Document processing", "Context resolution", "RAG invoke"])


def _render_run_table(runs: list, category_label: str) -> None:
    if not runs:
        st.info(f"No {category_label} traces in the selected time range.")
        return
    # Header row
    header_cols = st.columns([1.2, 0.8, 0.6, 0.6, 2, 1])
    with header_cols[0]:
        st.markdown("**Time**")
    with header_cols[1]:
        st.markdown("**Latency (s)**")
    with header_cols[2]:
        st.markdown("**Status**")
    with header_cols[3]:
        st.markdown("**Tokens**")
    with header_cols[4]:
        st.markdown("**Input**")
    with header_cols[5]:
        st.markdown("**Link**")
    st.divider()
    for r in runs:
        with st.container():
            time_str = r.start_time.strftime("%Y-%m-%d %H:%M:%S") if r.start_time else "—"
            latency_str = f"{r.latency_s:.2f}s" if r.latency_s is not None else "—"
            status = "OK" if not r.error else "Error"
            tokens_str = str(r.total_tokens) if r.total_tokens is not None else "—"
            row_cols = st.columns([1.2, 0.8, 0.6, 0.6, 2, 1])
            with row_cols[0]:
                st.text(time_str)
            with row_cols[1]:
                st.text(latency_str)
            with row_cols[2]:
                st.text(status)
            with row_cols[3]:
                st.text(tokens_str)
            with row_cols[4]:
                st.text(r.input_snippet[:120] + ("..." if len(r.input_snippet) > 120 else ""))
            with row_cols[5]:
                if r.trace_url:
                    st.link_button("Open in LangSmith", r.trace_url, type="secondary")
            if r.error:
                with st.expander("Error details"):
                    st.code(r.error)
            st.divider()


def _render_context_resolution_runs(runs: list) -> None:
    """Context resolution tab: table + expander with full query, last_user, last_assistant, and output."""
    if not runs:
        st.info("No context resolution traces in the selected time range.")
        return
    header_cols = st.columns([1.2, 0.8, 0.6, 0.6, 2, 1])
    with header_cols[0]:
        st.markdown("**Time**")
    with header_cols[1]:
        st.markdown("**Latency (s)**")
    with header_cols[2]:
        st.markdown("**Status**")
    with header_cols[3]:
        st.markdown("**Tokens**")
    with header_cols[4]:
        st.markdown("**Input (snippet)**")
    with header_cols[5]:
        st.markdown("**Link**")
    st.divider()
    for r in runs:
        time_str = r.start_time.strftime("%Y-%m-%d %H:%M:%S") if r.start_time else "—"
        latency_str = f"{r.latency_s:.2f}s" if r.latency_s is not None else "—"
        status = "OK" if not r.error else "Error"
        tokens_str = str(r.total_tokens) if r.total_tokens is not None else "—"
        row_cols = st.columns([1.2, 0.8, 0.6, 0.6, 2, 1])
        with row_cols[0]:
            st.text(time_str)
        with row_cols[1]:
            st.text(latency_str)
        with row_cols[2]:
            st.text(status)
        with row_cols[3]:
            st.text(tokens_str)
        with row_cols[4]:
            st.text(r.input_snippet[:120] + ("..." if len(r.input_snippet) > 120 else ""))
        with row_cols[5]:
            if r.trace_url:
                st.link_button("Open in LangSmith", r.trace_url, type="secondary")
        # Full query and last_assistant (and last_user) in expander
        with st.expander("Query & context (full)"):
            if isinstance(r.inputs_full, dict):
                st.markdown("**Current query:**")
                st.text(r.inputs_full.get("current_query", r.inputs_full.get("query", "—")))
                st.markdown("**Last user message:**")
                st.text(r.inputs_full.get("last_user") or "—")
                st.markdown("**Last assistant message:**")
                st.text(r.inputs_full.get("last_assistant") or "—")
            else:
                st.text(r.inputs_full or "—")
            if r.outputs_full is not None:
                st.markdown("**Output (resolved query):**")
                if isinstance(r.outputs_full, dict) and "content" in r.outputs_full:
                    st.text(r.outputs_full["content"])
                else:
                    st.text(str(r.outputs_full))
        if r.error:
            with st.expander("Error details"):
                st.code(r.error)
        st.divider()


def _render_rag_invoke_runs(runs: list) -> None:
    """RAG invoke tab: table with Cost column."""
    if not runs:
        st.info("No RAG invoke traces in the selected time range.")
        return
    header_cols = st.columns([1.2, 0.8, 0.6, 0.6, 0.8, 2, 1])
    with header_cols[0]:
        st.markdown("**Time**")
    with header_cols[1]:
        st.markdown("**Latency (s)**")
    with header_cols[2]:
        st.markdown("**Status**")
    with header_cols[3]:
        st.markdown("**Tokens**")
    with header_cols[4]:
        st.markdown("**Cost**")
    with header_cols[5]:
        st.markdown("**Input**")
    with header_cols[6]:
        st.markdown("**Link**")
    st.divider()
    for r in runs:
        time_str = r.start_time.strftime("%Y-%m-%d %H:%M:%S") if r.start_time else "—"
        latency_str = f"{r.latency_s:.2f}s" if r.latency_s is not None else "—"
        status = "OK" if not r.error else "Error"
        tokens_str = str(r.total_tokens) if r.total_tokens is not None else "—"
        cost_str = "—"
        if r.total_cost is not None:
            cost_str = f"${r.total_cost:.4f}"
        elif r.prompt_cost is not None or r.completion_cost is not None:
            total = (r.prompt_cost or 0) + (r.completion_cost or 0)
            cost_str = f"${total:.4f}"
        row_cols = st.columns([1.2, 0.8, 0.6, 0.6, 0.8, 2, 1])
        with row_cols[0]:
            st.text(time_str)
        with row_cols[1]:
            st.text(latency_str)
        with row_cols[2]:
            st.text(status)
        with row_cols[3]:
            st.text(tokens_str)
        with row_cols[4]:
            st.text(cost_str)
        with row_cols[5]:
            st.text(r.input_snippet[:120] + ("..." if len(r.input_snippet) > 120 else ""))
        with row_cols[6]:
            if r.trace_url:
                st.link_button("Open in LangSmith", r.trace_url, type="secondary")
        if r.error:
            with st.expander("Error details"):
                st.code(r.error)
        st.divider()


with tab_doc:
    _render_run_table(data.runs_by_category.get(CATEGORY_DOCUMENT_PROCESSING, []), "document processing")

with tab_ctx:
    _render_context_resolution_runs(data.runs_by_category.get(CATEGORY_CONTEXT_RESOLUTION, []))

with tab_rag:
    _render_rag_invoke_runs(data.runs_by_category.get(CATEGORY_RAG_INVOKE, []))
