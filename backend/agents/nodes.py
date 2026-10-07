"""
Individual LangGraph nodes. Each node takes the current AgentState and
returns a dict of fields to merge back in. Every node catches its own
exceptions and records them in `errors` rather than raising - a single
bad paper (bad PDF, LLM hiccup) should never crash the whole agent run.
"""
import logging
from agents.state import AgentState
from app.services.domain import detect_field, select_papers
from app.services.search_service import search_all_sources
from app.services.summarizer import summarize_paper
from ingestion.pipeline import ingest_paper, make_paper_id

logger = logging.getLogger(__name__)


async def search_node(state: AgentState) -> dict:
    wanted = state.get("max_papers", 5)
    try:
        papers = await search_all_sources(
            topic=state["topic"],
            # Fetch many more than needed: some papers have no readable PDF,
            # so we need spares to replace them.
            max_results=min(max(8, wanted * 3), 30),
            year_from=state.get("year_from"),
            year_to=state.get("year_to"),
        )
        return {"candidate_papers": papers}
    except Exception as exc:
        logger.exception("search_node failed")
        return {"candidate_papers": [], "errors": state.get("errors", []) + [f"Search failed: {exc}"]}


async def domain_node(state: AgentState) -> dict:
    """Votes on the research field of the topic using the found papers."""
    field, counts = detect_field(state.get("candidate_papers", []))
    logger.info("Detected field for topic %r: %s %s", state["topic"], field, counts)
    return {"detected_field": field, "field_counts": counts}


async def filter_node(state: AgentState) -> dict:
    """
    Ranks the papers that are really about the topic (and the user's
    field), best first. The best `max_papers` are `selected_papers`; the
    rest are kept in `reserve_papers` as spares, used when a selected paper
    turns out to be unreadable. See app/services/domain.py for the rules.
    """
    papers = state.get("candidate_papers", [])
    wanted = state.get("max_papers", 5)
    ranked, info = select_papers(
        topic=state["topic"],
        papers=papers,
        max_papers=wanted,
        user_field=state.get("user_field"),
        keep=len(papers),
    )
    return {
        "selected_papers": ranked[:wanted],
        "reserve_papers": ranked[wanted:],
        "selection_info": info,
    }


def _is_ok(result: dict | None) -> bool:
    return bool(result) and result.get("status") in ("success", "already_cached")


async def _try_ingest(paper) -> tuple[str, dict | None, str | None]:
    """Ingests one paper. Returns (paper_id, result, reason it failed or None)."""
    paper_id = make_paper_id(paper)
    try:
        result = await ingest_paper(paper)
    except Exception as exc:
        logger.exception("ingest failed for paper_id=%s", paper_id)
        return paper_id, None, f"error: {exc}"
    if _is_ok(result):
        return paper_id, result, None
    return paper_id, result, result.get("message") or str(result.get("status"))


async def ingest_node(state: AgentState) -> dict:
    """
    Downloads and reads papers in ranked order until we have `max_papers`
    readable ones. A paper that cannot be read is skipped (and its reason
    recorded) and the next best paper is tried instead.
    """
    queue = list(state.get("selected_papers", [])) + list(state.get("reserve_papers", []))
    target = state.get("max_papers") or len(state.get("selected_papers", []))
    results: dict[str, dict] = {}
    readable = []
    skipped = list(state.get("skipped_papers", []))

    while queue and len(readable) < target:
        paper = queue.pop(0)
        paper_id, result, reason = await _try_ingest(paper)
        if reason is None:
            results[paper_id] = result
            readable.append(paper)
        else:
            skipped.append({"title": paper.title, "reason": reason})

    return {
        "ingest_results": results,
        "selected_papers": readable,
        "reserve_papers": queue,        # papers we never needed to try
        "skipped_papers": skipped,
    }


async def summarize_node(state: AgentState) -> dict:
    """
    Summarizes every readable paper. If a summary fails (for example the
    AI service timed out), the next spare paper is ingested and summarized
    instead, so the user still gets the number of papers they asked for.
    """
    results: dict[str, dict] = {}
    errors = list(state.get("errors", []))
    skipped = list(state.get("skipped_papers", []))
    user_id = state.get("user_id")
    ingest_results = state.get("ingest_results", {})
    target = state.get("max_papers") or len(ingest_results)
    reserve = list(state.get("reserve_papers", []))
    selected = list(state.get("selected_papers", []))
    by_id = {make_paper_id(p): p for p in selected}

    async def summarize_one(paper_id: str) -> bool:
        try:
            summary = await summarize_paper(paper_id, user_id=user_id)
        except Exception as exc:
            logger.exception("summarize_node failed for paper_id=%s", paper_id)
            errors.append(f"Summarize failed for {paper_id}: {exc}")
            return False
        if _is_ok(summary):
            results[paper_id] = summary
            return True
        title = by_id[paper_id].title if paper_id in by_id else paper_id
        skipped.append({"title": title, "reason": summary.get("message") or "summary failed"})
        return False

    for paper_id, ingest_result in ingest_results.items():
        if ingest_result.get("status") in ("success", "already_cached"):
            await summarize_one(paper_id)

    # Top up from the spares if some summaries failed.
    while len(results) < target and reserve:
        paper = reserve.pop(0)
        paper_id, ingest_result, reason = await _try_ingest(paper)
        if reason is not None:
            skipped.append({"title": paper.title, "reason": reason})
            continue
        by_id[paper_id] = paper
        ingest_results[paper_id] = ingest_result
        if await summarize_one(paper_id):
            selected.append(paper)

    # Keep only the papers that really have a summary.
    final_selected = [p for p in selected if make_paper_id(p) in results]
    return {
        "summary_results": results,
        "selected_papers": final_selected,
        "reserve_papers": reserve,
        "skipped_papers": skipped,
        "errors": errors,
    }
