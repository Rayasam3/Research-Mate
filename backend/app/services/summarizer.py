"""
Orchestrates Phase 3: given a paper_id that's already been ingested, pull
its stored chunks, ask the LLM for a structured plain-English summary,
attach mechanically-generated citations, and cache the result so a
paper's card is only ever generated once.
"""
import json
import logging
from pathlib import Path

from app.core.config import settings
from app.schemas.summary import PaperSummaryCard, SummaryStatus
from app.services.citation import generate_apa_citation, generate_bibtex_citation
from app.services.entity_extraction import extract_entities
from app.services.graph_ingestion import index_paper_in_graph
from app.services.llm_client import LlmError, generate_json
from ingestion.pipeline import load_paper_metadata
from ingestion.vector_store import get_chunks_for_paper

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = ["tldr", "problem", "method_explained", "key_results", "limitations"]

_PROMPT_TEMPLATE = """You are summarizing an academic paper for someone who wants a clear, \
plain-English understanding without reading the full text. Base every claim strictly on the \
excerpts below - do not invent numbers, results, or claims that aren't supported by the text.

Paper title: {title}

Excerpts from the paper:
---
{chunks}
---

Respond with ONLY a JSON object with exactly these fields, each a plain string:
{{
  "tldr": "One or two sentence summary of what this paper does and why it matters.",
  "problem": "What problem or question this paper addresses.",
  "method_explained": "How their approach works, explained simply, avoiding unexplained jargon.",
  "key_results": "The concrete results reported, with real numbers from the text if present.",
  "limitations": "Limitations or weaknesses the paper itself acknowledges, or reasonable ones if none are stated."
}}"""


def _summary_cache_path(paper_id: str) -> Path:
    return Path(settings.cache_dir) / "summaries" / f"{paper_id}.json"


def _read_cached_summary(paper_id: str) -> dict | None:
    path = _summary_cache_path(paper_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt summary cache for %s, ignoring", paper_id)
        return None


def _write_cached_summary(paper_id: str, card: PaperSummaryCard) -> None:
    path = _summary_cache_path(paper_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(card.model_dump_json(), encoding="utf-8")


def build_prompt(title: str, chunks: list[str]) -> str:
    joined_chunks = "\n\n".join(chunks)
    return _PROMPT_TEMPLATE.format(title=title, chunks=joined_chunks)


async def summarize_paper(paper_id: str, force: bool = False, user_id: str | None = None) -> dict:
    """
    Returns a dict matching SummarizeResponse's fields. Never raises -
    every failure mode is caught and returned as a status the caller can
    act on or display.
    """
    if not force:
        cached = _read_cached_summary(paper_id)
        if cached is not None:
            logger.info("Summary for %s already cached, skipping LLM call", paper_id)
            # Still attempt graph indexing (best-effort) - a summary cached
            # from before Phase 5 existed would otherwise never get its
            # entities extracted and written to the graph.
            try:
                paper = load_paper_metadata(paper_id)
                if paper is not None:
                    entity_chunks = get_chunks_for_paper(paper_id, limit=settings.entity_extraction_chunks_used)
                    entities = await extract_entities(paper.title, entity_chunks)
                    await index_paper_in_graph(paper_id, paper, entities["methods"], entities["datasets"], user_id)
            except Exception:
                logger.exception("Graph indexing failed for cached summary paper_id=%s", paper_id)

            return {
                "paper_id": paper_id,
                "status": SummaryStatus.ALREADY_CACHED,
                "card": PaperSummaryCard(**cached),
                "message": "Already summarized; pass force=true to regenerate.",
            }

    paper = load_paper_metadata(paper_id)
    if paper is None:
        return {
            "paper_id": paper_id,
            "status": SummaryStatus.NOT_INGESTED,
            "card": None,
            "message": "No metadata found for this paper_id. Ingest it first via /api/ingest.",
        }

    chunks = get_chunks_for_paper(paper_id, limit=settings.summary_chunks_used)
    if not chunks:
        return {
            "paper_id": paper_id,
            "status": SummaryStatus.NO_CHUNKS_AVAILABLE,
            "card": None,
            "message": "This paper has no stored chunks to summarize (was it ingested successfully?).",
        }

    prompt = build_prompt(paper.title, chunks)

    try:
        raw = await generate_json(prompt)
    except LlmError as exc:
        return {
            "paper_id": paper_id,
            "status": SummaryStatus.LLM_FAILED,
            "card": None,
            "message": str(exc),
        }

    missing = [f for f in _REQUIRED_FIELDS if not raw.get(f)]
    if missing:
        logger.error("LLM response missing fields %s for paper_id=%s: %r", missing, paper_id, raw)
        return {
            "paper_id": paper_id,
            "status": SummaryStatus.LLM_FAILED,
            "card": None,
            "message": f"LLM response was missing expected fields: {missing}",
        }

    card = PaperSummaryCard(
        tldr=raw["tldr"],
        problem=raw["problem"],
        method_explained=raw["method_explained"],
        key_results=raw["key_results"],
        limitations=raw["limitations"],
        citation_apa=generate_apa_citation(paper),
        citation_bibtex=generate_bibtex_citation(paper),
    )

    _write_cached_summary(paper_id, card)

    # Best-effort graph indexing: a failure here should never break the
    # summary response itself, since the summary is the primary deliverable
    # and the graph is an enrichment on top of it (Phase 5).
    try:
        entity_chunks = get_chunks_for_paper(paper_id, limit=settings.entity_extraction_chunks_used)
        entities = await extract_entities(paper.title, entity_chunks)
        await index_paper_in_graph(paper_id, paper, entities["methods"], entities["datasets"], user_id)
    except Exception:
        logger.exception("Graph indexing failed for paper_id=%s (summary still succeeded)", paper_id)

    return {
        "paper_id": paper_id,
        "status": SummaryStatus.SUCCESS,
        "card": card,
        "message": None,
    }