"""
Finds under-explored areas across a set of papers using simple, grounded
graph analytics (not the LLM) - specifically, methods or datasets that
appear in only one of the given papers. The LLM's only job afterward is
to phrase these real facts in plain English; it never decides what counts
as a gap, which keeps gap statements grounded in actual graph data rather
than invented.
"""
import logging

from app.services.comparison import get_comparison_table
from app.services.llm_client import LlmError, generate_json

logger = logging.getLogger(__name__)

_GAP_PROMPT_TEMPLATE = """You are helping a researcher spot under-explored areas across a set of \
papers. Below are facts about which methods and datasets appear in only ONE of the papers reviewed \
(meaning they haven't been cross-validated or compared against other approaches in this set).

Isolated methods (used in only one paper each):
{isolated_methods}

Isolated datasets (used in only one paper each):
{isolated_datasets}

For each isolated method or dataset, write one short, plain-English sentence noting it as a \
potential area worth further exploration or cross-validation. Do NOT invent any method or dataset \
names beyond what's listed above. If a list is empty, return an empty array for that field.

Respond with ONLY valid JSON in exactly this format:
{{"method_gaps": ["sentence1", "sentence2"], "dataset_gaps": ["sentence1", "sentence2"]}}"""


def _find_isolated_items(rows: list[dict], key: str) -> list[str]:
    """Returns items (methods or datasets) that appear in exactly one row's list."""
    counts: dict[str, int] = {}
    for row in rows:
        for item in row.get(key, []):
            counts[item] = counts.get(item, 0) + 1
    return sorted(name for name, count in counts.items() if count == 1)


async def analyze_gaps(paper_ids: list[str]) -> dict:
    """
    Returns {"isolated_methods": [...], "isolated_datasets": [...],
    "method_gaps": [...], "dataset_gaps": [...]}. The isolated_* lists are
    pure graph facts (no LLM); the *_gaps lists are LLM-phrased sentences
    built strictly from those facts.
    """
    rows = await get_comparison_table(paper_ids)

    isolated_methods = _find_isolated_items(rows, "methods")
    isolated_datasets = _find_isolated_items(rows, "datasets")

    if not isolated_methods and not isolated_datasets:
        return {
            "isolated_methods": [],
            "isolated_datasets": [],
            "method_gaps": [],
            "dataset_gaps": [],
        }

    prompt = _GAP_PROMPT_TEMPLATE.format(
        isolated_methods=", ".join(isolated_methods) or "(none)",
        isolated_datasets=", ".join(isolated_datasets) or "(none)",
    )

    try:
        raw = await generate_json(prompt)
        method_gaps = raw.get("method_gaps") or []
        dataset_gaps = raw.get("dataset_gaps") or []
    except LlmError:
        logger.exception("Gap statement generation failed; returning raw facts without phrasing")
        method_gaps = []
        dataset_gaps = []

    return {
        "isolated_methods": isolated_methods,
        "isolated_datasets": isolated_datasets,
        "method_gaps": method_gaps,
        "dataset_gaps": dataset_gaps,
    }