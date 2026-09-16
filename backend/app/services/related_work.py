"""
Synthesizes stored per-paper summary cards into one academic-style
"Related Work" paragraph with inline citations, plus a BibTeX reference
list. Reuses Phase 3's cached summaries and citation generator - no new
LLM calls needed for the citations themselves, only for the synthesis
paragraph.
"""
import json
import logging
from pathlib import Path

from app.core.config import settings
from app.services.llm_client import LlmError, generate_json
from ingestion.pipeline import load_paper_metadata

logger = logging.getLogger(__name__)

_DRAFT_PROMPT_TEMPLATE = """Write a short academic "Related Work" paragraph synthesizing the \
following papers. Reference each paper by its (Author, Year) citation inline. Base every claim \
strictly on the summaries provided - do not invent findings, comparisons, or details not present \
in the summaries below.

Papers:
{paper_summaries}

Respond with ONLY valid JSON in exactly this format:
{{"paragraph": "The related work paragraph text with inline (Author, Year) citations."}}"""


def _load_cached_summary(paper_id: str) -> dict | None:
    path = Path(settings.cache_dir) / "summaries" / f"{paper_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _first_author_last_name(paper) -> str:
    if not paper.authors:
        return "Unknown"
    return paper.authors[0].strip().split()[-1]


async def build_related_work_draft(paper_ids: list[str]) -> dict:
    """
    Returns {"paragraph": str, "bibtex_references": [str], "skipped_paper_ids": [str]}.
    Papers with no cached summary are skipped (reported, not errored on) -
    they simply weren't summarized yet, which isn't a failure of this
    feature.
    """
    included_summaries = []
    bibtex_references = []
    skipped_paper_ids = []

    for paper_id in paper_ids:
        cached = _load_cached_summary(paper_id)
        paper = load_paper_metadata(paper_id)

        if cached is None or paper is None:
            skipped_paper_ids.append(paper_id)
            continue

        author_year = f"{_first_author_last_name(paper)}, {paper.published_date.year if paper.published_date else 'n.d.'}"
        included_summaries.append(f"({author_year}) {paper.title}: {cached['tldr']}")
        bibtex_references.append(cached["citation_bibtex"])

    if not included_summaries:
        return {
            "paragraph": "",
            "bibtex_references": [],
            "skipped_paper_ids": skipped_paper_ids,
        }

    prompt = _DRAFT_PROMPT_TEMPLATE.format(paper_summaries="\n".join(included_summaries))

    try:
        raw = await generate_json(prompt)
        paragraph = raw.get("paragraph", "")
    except LlmError:
        logger.exception("Related work draft generation failed")
        paragraph = ""

    return {
        "paragraph": paragraph,
        "bibtex_references": bibtex_references,
        "skipped_paper_ids": skipped_paper_ids,
    }