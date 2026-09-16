"""
Uses the LLM to pull structured entities (methods, datasets) out of a
paper's stored chunks, so they can become graph nodes. Reuses Phase 3's
generate_json() - same provider (Ollama/Groq), same JSON-mode reliability.
"""
import logging

from app.core.config import settings
from app.services.llm_client import LlmError, generate_json

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT_TEMPLATE = """Extract the key methods and datasets mentioned in this paper excerpt. \
Only include methods/datasets actually named in the text - do not invent or guess ones that seem likely \
but aren't explicitly mentioned.

Paper title: {title}

Excerpt:
---
{chunks}
---

Respond with ONLY valid JSON, no other text, in exactly this format:
{{"methods": ["method1", "method2"], "datasets": ["dataset1", "dataset2"]}}
Use empty arrays if none are found."""


def build_extraction_prompt(title: str, chunks: list[str]) -> str:
    joined = "\n\n".join(chunks)
    return _EXTRACTION_PROMPT_TEMPLATE.format(title=title, chunks=joined)


async def extract_entities(title: str, chunks: list[str]) -> dict:
    """
    Returns {"methods": [...], "datasets": [...]}. On any LLM failure,
    returns empty lists rather than raising - a paper with no extracted
    entities should just have fewer graph connections, not break ingestion.
    """
    if not chunks:
        return {"methods": [], "datasets": []}

    prompt = build_extraction_prompt(title, chunks)
    try:
        raw = await generate_json(prompt)
    except LlmError:
        logger.exception("Entity extraction LLM call failed for title=%r", title)
        return {"methods": [], "datasets": []}

    methods = raw.get("methods") or []
    datasets = raw.get("datasets") or []

    # Defensive cleanup: dedupe, strip whitespace, drop empties.
    methods = sorted({m.strip() for m in methods if isinstance(m, str) and m.strip()})
    datasets = sorted({d.strip() for d in datasets if isinstance(d, str) and d.strip()})

    return {"methods": methods, "datasets": datasets}