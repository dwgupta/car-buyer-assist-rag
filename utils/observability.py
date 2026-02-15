"""
Observability utilities: fetch LangSmith runs by category and compute aggregate metrics.

Used by the Observability page to display document_processing, context_resolution,
and rag_invoke traces in-app without leaving for smith.langchain.com.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Trace names used by @traceable in the codebase
NAME_DOCUMENT_PROCESSING = "document_processing"
NAME_DOCUMENT_PROCESSING_GENERATOR = "document_processing_generator"
NAME_CONTEXT_RESOLUTION = "context_resolution"
NAME_RAG_INVOKE = "rag_invoke"

# Categories returned to the UI
CATEGORY_DOCUMENT_PROCESSING = "document_processing"
CATEGORY_CONTEXT_RESOLUTION = "context_resolution"
CATEGORY_RAG_INVOKE = "rag_invoke"


def get_langsmith_project_url(project_name: str) -> str:
    """
    Return the LangSmith observability URL for the given project (traces page).
    Derives the URL from a run's get_run_url() and strips the run part, so the path
    format matches what the LangSmith UI expects (avoids 404).
    """
    if not project_name or not os.getenv("LANGSMITH_API_KEY"):
        return "https://smith.langchain.com"
    try:
        from langsmith import Client

        client = Client()
        # Get one run from this project; use its URL to derive the project page URL
        runs = list(
            client.list_runs(project_name=project_name, limit=1)
        )
        if runs:
            run_url = client.get_run_url(run=runs[0], project_name=project_name)
            # Project page = run URL with /r/{run_id} removed (trailing path segment)
            if "/r/" in run_url:
                return run_url.rsplit("/r/", 1)[0]
            return run_url
    except Exception as e:
        logger.warning("Could not resolve LangSmith project URL for %s: %s", project_name, e)
    return "https://smith.langchain.com"


@dataclass
class RunRow:
    """Flattened run data for display in the Observability page."""
    id: str
    name: str
    start_time: datetime
    latency_ms: float | None
    latency_s: float | None  # seconds, for display
    error: str | None
    total_tokens: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    input_snippet: str  # truncated for table
    trace_url: str | None
    # Full inputs/outputs for context_resolution and other tabs
    inputs_full: dict | str | None = None
    outputs_full: dict | str | None = None
    # Cost (RAG/LLM runs)
    total_cost: float | None = None
    prompt_cost: float | None = None
    completion_cost: float | None = None


@dataclass
class CategoryMetrics:
    """Aggregate metrics for one trace category."""
    total_runs: int
    success_count: int
    avg_latency_s: float | None
    total_tokens: int


@dataclass
class ObservabilityData:
    """All data for the Observability page."""
    runs_by_category: dict[str, list[RunRow]] = field(default_factory=dict)
    metrics_by_category: dict[str, CategoryMetrics] = field(default_factory=dict)
    summary_total_runs: int = 0
    summary_total_tokens: int = 0
    error_message: str | None = None


def _run_to_row(run: Any, trace_url: str | None) -> RunRow:
    """Convert a LangSmith Run to RunRow."""
    latency_ms = getattr(run, "latency_ms", None)
    if latency_ms is None and getattr(run, "latency", None) is not None:
        try:
            latency_ms = float(run.latency) * 1000 if float(run.latency) < 1000 else float(run.latency)
        except (TypeError, ValueError):
            pass
    if latency_ms is None:
        start = getattr(run, "start_time", None)
        end = getattr(run, "end_time", None)
        if start and end:
            delta = (end - start).total_seconds()
            latency_ms = delta * 1000
    latency_s = (latency_ms / 1000.0) if latency_ms is not None else None
    err = getattr(run, "error", None)
    error_str = str(err) if err else None
    total_tokens = getattr(run, "total_tokens", None)
    prompt_tokens = getattr(run, "prompt_tokens", None)
    completion_tokens = getattr(run, "completion_tokens", None)
    inputs = getattr(run, "inputs", None) or {}
    outputs = getattr(run, "outputs", None)
    if isinstance(inputs, dict):
        # Truncate for table: show query or file_paths key if present
        parts = []
        if "query" in inputs:
            q = str(inputs["query"])[:80]
            parts.append(q + ("..." if len(str(inputs["query"])) > 80 else ""))
        if "file_paths" in inputs:
            fp = inputs["file_paths"]
            parts.append(f"{len(fp) if isinstance(fp, list) else '?'} file(s)")
        input_snippet = " | ".join(parts) if parts else str(inputs)[:100]
    else:
        input_snippet = str(inputs)[:100]
    # Cost fields (LLM runs may have total_cost, prompt_cost, completion_cost)
    total_cost = getattr(run, "total_cost", None)
    prompt_cost = getattr(run, "prompt_cost", None)
    completion_cost = getattr(run, "completion_cost", None)
    if total_cost is not None and hasattr(total_cost, "__float__"):
        total_cost = float(total_cost)
    if prompt_cost is not None and hasattr(prompt_cost, "__float__"):
        prompt_cost = float(prompt_cost)
    if completion_cost is not None and hasattr(completion_cost, "__float__"):
        completion_cost = float(completion_cost)
    return RunRow(
        id=str(getattr(run, "id", "")),
        name=getattr(run, "name", ""),
        start_time=getattr(run, "start_time", datetime.now(timezone.utc)),
        latency_ms=latency_ms,
        latency_s=latency_s,
        error=error_str,
        total_tokens=total_tokens,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        input_snippet=input_snippet,
        trace_url=trace_url,
        inputs_full=inputs if isinstance(inputs, dict) else str(inputs),
        outputs_full=outputs,
        total_cost=total_cost,
        prompt_cost=prompt_cost,
        completion_cost=completion_cost,
    )


def _compute_metrics(rows: list[RunRow]) -> CategoryMetrics:
    """Compute aggregate metrics for a list of runs."""
    total = len(rows)
    success = sum(1 for r in rows if not r.error)
    latencies = [r.latency_s for r in rows if r.latency_s is not None]
    avg_s = (sum(latencies) / len(latencies)) if latencies else None
    tokens = sum(r.total_tokens or 0 for r in rows)
    return CategoryMetrics(total_runs=total, success_count=success, avg_latency_s=avg_s, total_tokens=tokens)


def get_runs_by_category(
    project_name: str,
    start_time: datetime | None = None,
    limit_per_type: int = 50,
) -> ObservabilityData:
    """
    Fetch runs from LangSmith grouped by document_processing, context_resolution, rag_invoke.

    Uses LANGSMITH_API_KEY from env. Returns ObservabilityData with runs_by_category,
    metrics_by_category, and summary totals. On failure, error_message is set and lists are empty.
    """
    result = ObservabilityData(
        runs_by_category={
            CATEGORY_DOCUMENT_PROCESSING: [],
            CATEGORY_CONTEXT_RESOLUTION: [],
            CATEGORY_RAG_INVOKE: [],
        },
        metrics_by_category={},
    )
    if not os.getenv("LANGSMITH_API_KEY"):
        result.error_message = "LANGSMITH_API_KEY is not set. Set it in .env to view traces."
        return result

    try:
        from langsmith import Client

        client = Client()

        def run_trace_url(run: Any) -> str | None:
            """Use the SDK to build the correct run URL (uses project UUID internally)."""
            try:
                return client.get_run_url(run=run, project_name=project_name)
            except Exception:
                return None

        filters = [
            (CATEGORY_DOCUMENT_PROCESSING, f'or(eq(name, "{NAME_DOCUMENT_PROCESSING}"), eq(name, "{NAME_DOCUMENT_PROCESSING_GENERATOR}"))'),
            (CATEGORY_CONTEXT_RESOLUTION, f'eq(name, "{NAME_CONTEXT_RESOLUTION}")'),
            (CATEGORY_RAG_INVOKE, f'eq(name, "{NAME_RAG_INVOKE}")'),
        ]
        for category, filter_expr in filters:
            runs = list(
                client.list_runs(
                    project_name=project_name,
                    filter=filter_expr,
                    start_time=start_time,
                    limit=limit_per_type,
                )
            )
            rows = [_run_to_row(r, run_trace_url(r)) for r in runs]
            # Sort by start_time descending
            rows.sort(key=lambda r: r.start_time, reverse=True)
            result.runs_by_category[category] = rows
            result.metrics_by_category[category] = _compute_metrics(rows)

        result.summary_total_runs = sum(m.total_runs for m in result.metrics_by_category.values())
        result.summary_total_tokens = sum(m.total_tokens for m in result.metrics_by_category.values())
    except Exception as e:
        logger.exception("Failed to fetch LangSmith runs: %s", e)
        result.error_message = f"Could not load traces: {e}"
    return result
