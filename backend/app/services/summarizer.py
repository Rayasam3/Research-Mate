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
from app.services.llm_client import LlmError, generate_json
from app.services.record_extraction import extract_and_index_record, reassemble, split_sections
from ingestion.pipeline import load_paper_metadata
from ingestion.text_extractor import find_abstract
from ingestion.vector_store import get_chunks_for_paper

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = ["tldr", "problem", "method_explained", "key_results", "limitations"]

_PROMPT_TEMPLATE = """You are summarizing an academic paper for a student who wants a clear, \
plain-English understanding without reading the full text. Base every claim strictly on the \
text below - do not invent numbers, results, or claims that are not supported by it.

Paper title: {title}

ABSTRACT (written by the authors):
{abstract}

EXCERPTS FROM THE REST OF THE PAPER:
---
{excerpts}
---

Respond with ONLY a JSON object with exactly these fields, each a plain string:
{{
  "tldr": "3 to 4 sentences: the problem, what the authors did or propose, and the main finding or contribution. Be specific (name the method, data or categories), not generic.",
  "problem": "The problem or question the paper addresses and why it matters (2 to 3 sentences).",
  "method_explained": "How the approach works or how the survey is organised, explained simply (3 to 5 sentences).",
  "key_results": "The concrete results with real numbers if the text has them. For a survey with no experiments, give its main findings, taxonomy or conclusions instead.",
  "limitations": "Limitations, open challenges or future directions the paper itself states."
}}"""

# How much of each part of the paper is shown to the AI (characters).
_ABSTRACT_MAX = 2500
_INTRO_TAIL = 1800        # end of the introduction usually lists the contributions
_EXPERIMENTS_HEAD = 1500
_CONCLUSION_HEAD = 1500


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


def get_abstract(paper, text: str) -> str:
    """The abstract printed in the PDF if we can find it, else the one from the search source."""
    from_pdf = find_abstract(text)
    if from_pdf:
        return from_pdf
    return (paper.abstract or "").strip()[:_ABSTRACT_MAX]


def pick_excerpts(text: str, abstract: str) -> list[str]:
    """
    Chooses the parts of the whole paper that matter most for a summary:
    the end of the introduction (contributions), the start of the
    experiments (results) and the conclusion (findings and limitations).
    """
    sections = split_sections(text)
    intro = sections.get("intro", "")
    if abstract and abstract[:80] in intro:
        intro = intro.split(abstract[:80], 1)[1][len(abstract) - 80:]   # drop the abstract itself
    excerpts = []
    if intro.strip():
        excerpts.append("[Introduction / contributions]\n" + intro.strip()[-_INTRO_TAIL:])
    if sections.get("experiments"):
        excerpts.append("[Experiments / results]\n" + sections["experiments"][:_EXPERIMENTS_HEAD])
    if sections.get("conclusion"):
        excerpts.append("[Conclusion]\n" + sections["conclusion"][:_CONCLUSION_HEAD])
    return excerpts


def build_prompt(title: str, abstract: str, excerpts: list[str]) -> str:
    return _PROMPT_TEMPLATE.format(
        title=title,
        abstract=abstract or "(no abstract available)",
        excerpts="\n\n".join(excerpts) or "(no further text available)",
    )


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
            # Still index the paper in the graph (best-effort). The extracted
            # record is cached on disk, so this costs no extra LLM calls.
            try:
                paper = load_paper_metadata(paper_id)
                if paper is not None:
                    await extract_and_index_record(paper_id, paper, user_id)
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

    chunks = get_chunks_for_paper(paper_id)   # every chunk: the whole paper is used
    if not chunks:
        return {
            "paper_id": paper_id,
            "status": SummaryStatus.NO_CHUNKS_AVAILABLE,
            "card": None,
            "message": "This paper has no stored chunks to summarize (was it ingested successfully?).",
        }

    text = reassemble(chunks)
    abstract = get_abstract(paper, text)
    prompt = build_prompt(paper.title, abstract, pick_excerpts(text, abstract))

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
        abstract=abstract,
        citation_apa=generate_apa_citation(paper),
        citation_bibtex=generate_bibtex_citation(paper),
    )

    _write_cached_summary(paper_id, card)

    # Best-effort graph indexing: a failure here must never break the summary
    # itself. The whole paper is read section by section (Phase 2).
    try:
        await extract_and_index_record(paper_id, paper, user_id)
    except Exception:
        logger.exception("Graph indexing failed for paper_id=%s (summary still succeeded)", paper_id)

    return {
        "paper_id": paper_id,
        "status": SummaryStatus.SUCCESS,
        "card": card,
        "message": None,
    }