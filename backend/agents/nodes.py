"""
Individual LangGraph nodes. Each node takes the current AgentState and
returns a dict of fields to merge back in. Every node catches its own
exceptions and records them in `errors` rather than raising - a single
bad paper (bad PDF, LLM hiccup) should never crash the whole agent run.
"""
import logging
from agents.state import AgentState
from app.schemas.paper import PaperSource
from app.services.search_service import search_all_sources
from app.services.summarizer import summarize_paper
from ingestion.pipeline import ingest_paper, make_paper_id

logger = logging.getLogger(__name__)


async def search_node(state: AgentState) -> dict:
    try:
        papers = await search_all_sources(
            topic=state["topic"],
            max_results=state.get("max_papers", 5) * 2,  # over-fetch, filter node trims down
            year_from=state.get("year_from"),
            year_to=state.get("year_to"),
        )
        return {"candidate_papers": papers}
    except Exception as exc:
        logger.exception("search_node failed")
        return {"candidate_papers": [], "errors": state.get("errors", []) + [f"Search failed: {exc}"]}


async def filter_node(state: AgentState) -> dict:
    """
    Picks which candidate papers actually get processed. For now: prefer
    papers that have a real pdf_url (so ingestion has a chance of
    succeeding), then take the first N. A smarter relevance-ranking pass
    is a reasonable future improvement, not needed for this phase.
    """
    max_papers = state.get("max_papers", 5)
    candidates = state.get("candidate_papers", [])

    with_pdf = [p for p in candidates if p.pdf_url]
    without_pdf = [p for p in candidates if not p.pdf_url]
    ordered = with_pdf + without_pdf

    return {"selected_papers": ordered[:max_papers]}


async def ingest_node(state: AgentState) -> dict:
    results: dict[str, dict] = {}
    errors = list(state.get("errors", []))

    for paper in state.get("selected_papers", []):
        paper_id = make_paper_id(paper)
        try:
            result = await ingest_paper(paper)
            results[paper_id] = result
        except Exception as exc:
            logger.exception("ingest_node failed for paper_id=%s", paper_id)
            errors.append(f"Ingest failed for {paper_id}: {exc}")

    return {"ingest_results": results, "errors": errors}


async def summarize_node(state: AgentState) -> dict:
    results: dict[str, dict] = {}
    errors = list(state.get("errors", []))
    ingest_results = state.get("ingest_results", {})
    print(f"DEBUG summarize_node received ingest_results: {ingest_results!r}", flush=True)

    for paper_id, ingest_result in ingest_results.items():
        if ingest_result.get("status") not in ("success", "already_cached"):
            continue  # nothing to summarize if ingestion truly failed
        try:
            summary = await summarize_paper(paper_id)
            results[paper_id] = summary
        except Exception as exc:
            logger.exception("summarize_node failed for paper_id=%s", paper_id)
            errors.append(f"Summarize failed for {paper_id}: {exc}")

    return {"summary_results": results, "errors": errors}