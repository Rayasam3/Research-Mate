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

    candidate_papers: list[Paper]
    selected_papers: list[Paper]

    ingest_results: dict[str, dict]      # paper_id -> ingest result dict
    summary_results: dict[str, dict]     # paper_id -> summarize result dict

    errors: list[str]