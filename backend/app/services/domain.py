"""
Phase 3: find out WHICH research field a topic belongs to, and keep only the
papers that are really about the user's topic.

Why this matters: "transformer" means one thing in computer science and
something else in power engineering. Every paper source tells us the field
of each paper (ArXiv category, OpenAlex topic, Semantic Scholar field).
We vote on those labels to find the topic's field, then rank the papers by
how close they are to the topic (embedding similarity) and drop the rest.
"""
import logging
import math
from datetime import date

from app.core.config import settings
from app.schemas.paper import Paper

logger = logging.getLogger(__name__)

# The short list of fields shown in the frontend dropdown.
FIELDS = [
    "Computer Science",
    "Medicine & Health",
    "Biology & Life Sciences",
    "Physics",
    "Mathematics & Statistics",
    "Engineering",
    "Chemistry & Materials",
    "Economics & Business",
    "Social Sciences & Humanities",
    "Environmental & Earth Science",
    "Other",
]

# If a source's field name contains one of these words, it maps to that field.
# The order matters: the first match wins.
_KEYWORDS = [
    ("Computer Science", ["computer", "artificial intelligence", "machine learning", "informatics"]),
    ("Medicine & Health", ["medic", "health", "nursing", "dentistry", "pharmac", "clinical", "veterinary"]),
    ("Biology & Life Sciences", ["biolog", "biochem", "genetic", "neuroscience", "immunolog", "agricultur"]),
    ("Physics", ["physic", "astronom"]),
    ("Mathematics & Statistics", ["math", "statistic"]),
    ("Engineering", ["engineer", "electrical"]),
    ("Chemistry & Materials", ["chemi", "material"]),
    ("Economics & Business", ["econom", "business", "financ", "management"]),
    ("Social Sciences & Humanities", ["social", "psycholog", "education", "humanit", "arts"]),
    ("Environmental & Earth Science", ["environment", "earth", "geolog", "energy"]),
]

# ArXiv category prefix (the part before the dot) -> field.
_ARXIV_PREFIXES = {
    "cs": "Computer Science",
    "stat": "Mathematics & Statistics",
    "math": "Mathematics & Statistics",
    "eess": "Engineering",
    "q-bio": "Biology & Life Sciences",
    "q-fin": "Economics & Business",
    "econ": "Economics & Business",
    "physics": "Physics",
    "astro-ph": "Physics",
    "cond-mat": "Physics",
    "quant-ph": "Physics",
    "gr-qc": "Physics",
    "nlin": "Physics",
    "hep-th": "Physics",
    "hep-ph": "Physics",
    "hep-ex": "Physics",
    "hep-lat": "Physics",
    "nucl-th": "Physics",
    "nucl-ex": "Physics",
}


def canonical_field(raw: str | None) -> str | None:
    """Turn any source's field name into one of our short FIELDS (or None)."""
    if not raw:
        return None
    text = raw.lower()
    for field, words in _KEYWORDS:
        if any(word in text for word in words):
            return field
    return "Other"


def field_from_arxiv_category(category: str | None) -> str | None:
    """'cs.LG' -> 'Computer Science'."""
    if not category:
        return None
    return _ARXIV_PREFIXES.get(category.split(".")[0].lower(), "Other")


def detect_field(papers: list[Paper]) -> tuple[str | None, dict[str, int]]:
    """Vote: the most common field among the found papers is the topic's field."""
    counts: dict[str, int] = {}
    for paper in papers:
        if paper.field:
            counts[paper.field] = counts.get(paper.field, 0) + 1
    if not counts:
        return None, {}
    best = max(counts, key=counts.get)
    return best, counts


# --------------------------------------------------------------------------
# Relevance ranking
# --------------------------------------------------------------------------

def _embed(texts: list[str]) -> list[list[float]]:
    """Embeds texts with the same small ONNX model ChromaDB uses (no PyTorch)."""
    from ingestion.embeddings import get_embedding_function

    return [[float(x) for x in vec] for vec in get_embedding_function()(texts)]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def _paper_text(paper: Paper) -> str:
    return f"{paper.title}. {(paper.abstract or '')[:600]}"


def _score(similarity: float, paper: Paper, target_field: str | None) -> float:
    """Combine similarity with a few simple signals into one ranking score."""
    score = similarity
    if target_field and paper.field == target_field:
        score += 0.15                       # same field as the user / topic
    citations = paper.citation_count or 0
    score += 0.10 * min(math.log10(1 + citations) / 4, 1.0)   # well-cited
    if paper.published_date:
        years_old = date.today().year - paper.published_date.year
        score += 0.10 * max(0, 1 - years_old / 10)             # recent
    if paper.pdf_url:
        score += 0.10                       # we can actually read the full text
    return score


def select_papers(
    topic: str,
    papers: list[Paper],
    max_papers: int,
    user_field: str | None = None,
    keep: int | None = None,
) -> tuple[list[Paper], dict]:
    """
    Ranks the papers for the topic, best first, and returns the top `keep`
    (default: `max_papers`).
    Returns (selected papers, info) where info explains what was decided.
    """
    detected, counts = detect_field(papers)
    target_field = user_field or detected
    info = {
        "detected_field": detected,
        "field_counts": counts,
        "user_field": user_field,
        "target_field": target_field,
        "considered": len(papers),
        "dropped_off_topic": 0,
        "dropped_other_field": 0,
    }
    if not papers:
        return [], info

    # 1. If the user told us their field and enough papers match it, ignore other fields.
    pool = papers
    if user_field:
        same_field = [p for p in papers if p.field == user_field]
        if len(same_field) >= max_papers:
            info["dropped_other_field"] = len(papers) - len(same_field)
            pool = same_field

    # 2. Similarity between the topic and every paper.
    try:
        vectors = _embed([topic] + [_paper_text(p) for p in pool])
        sims = [_cosine(vectors[0], v) for v in vectors[1:]]
    except Exception:
        logger.exception("Embedding failed; ranking without similarity")
        sims = [0.5] * len(pool)

    # Papers with a PDF link always come before papers without one,
    # because a paper we cannot download cannot be read or summarized.
    ranked = sorted(
        ((p, s, _score(s, p, target_field)) for p, s in zip(pool, sims)),
        key=lambda item: (bool(item[0].pdf_url), item[2]),
        reverse=True,
    )

    # 3. Drop papers that are not about the topic at all.
    on_topic = [item for item in ranked if item[1] >= settings.relevance_min_similarity]
    if not on_topic:
        on_topic = ranked[:3]          # never return nothing just because of the threshold
    info["dropped_off_topic"] = len(ranked) - len(on_topic)

    chosen = on_topic[: keep or max_papers]
    info["ranking"] = [
        {"title": p.title, "field": p.field, "similarity": round(s, 3), "score": round(sc, 3)}
        for p, s, sc in chosen
    ]
    return [p for p, _, _ in chosen], info
