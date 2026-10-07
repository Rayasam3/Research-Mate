"""
Shared state object threaded through every node in the LangGraph agent.
Each node reads what it needs and returns a partial update, which
LangGraph merges into this state automatically.
"""
from typing import TypedDict

from app.schemas.paper import Paper


class AgentState(TypedDict, total=False):
    topic: str
    max_papers: int
    year_from: int | None
    year_to: int | None
    user_id: str
    user_field: str | None      # the user's own field (from the search form), or None = auto-detect

    detected_field: str | None  # field found by voting over the search results
    field_counts: dict          # e.g. {"Computer Science": 7, "Medicine & Health": 2}
    selection_info: dict        # how papers were ranked / dropped (Phase 3)

    candidate_papers: list[Paper]
    selected_papers: list[Paper]
    reserve_papers: list[Paper]          # spares, used when a selected paper cannot be read
    skipped_papers: list[dict]           # [{title, reason}] papers that were tried and skipped

    ingest_results: dict[str, dict]      # paper_id -> ingest result dict
    summary_results: dict[str, dict]     # paper_id -> summarize result dict

    errors: list[str]