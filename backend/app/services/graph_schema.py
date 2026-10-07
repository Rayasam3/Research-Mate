"""
Graph schema helpers: name normalization (so variants of the same method
or dataset merge into one node) and the Neo4j uniqueness constraints.
Phase 2 will extend merging with LLM-assisted canonicalization.
"""
import hashlib
import re

from app.services.graph_client import run_query

_PAREN = re.compile(r"\s*\([^)]*\)")
_WS = re.compile(r"\s+")

# Small starter alias map; Phase 2 grows this.
_ALIASES = {
    "gnn": "graph neural network",
    "gnns": "graph neural network",
    "graph neural networks": "graph neural network",
    "cnn": "convolutional neural network",
    "cnns": "convolutional neural network",
    "convolutional neural networks": "convolutional neural network",
    "rnn": "recurrent neural network",
    "rnns": "recurrent neural network",
    "lstm": "long short-term memory",
    "llm": "large language model",
    "llms": "large language model",
    "large language models": "large language model",
    "vit": "vision transformer",
    "gan": "generative adversarial network",
    "gans": "generative adversarial network",
}


def normalize_key(name: str) -> str:
    """Lowercase, drop parenthetical abbreviations, collapse spaces, map aliases."""
    text = _PAREN.sub("", name or "").lower()
    text = re.sub(r"[^\w\s\-+./]", " ", text)
    text = _WS.sub(" ", text).strip(" -._/")
    return _ALIASES.get(text, text)


def statement_key(paper_id: str, text: str) -> str:
    """Per-paper key for limitation / future-work sentences (never merged across papers)."""
    cleaned = _WS.sub(" ", (text or "").strip().lower())
    digest = hashlib.sha1(cleaned.encode("utf-8")).hexdigest()[:12]
    return f"{paper_id}:{digest}"


# Old per-name constraints replaced by key-based ones.
_LEGACY_CONSTRAINTS = ["method_name", "dataset_name"]

_CONSTRAINTS = [
    ("paper_id", "Paper", "paper_id"),
    ("method_key", "Method", "key"),
    ("dataset_key", "Dataset", "key"),
    ("domain_key", "Domain", "key"),
    ("task_key", "Task", "key"),
    ("limitation_key", "Limitation", "key"),
    ("futurework_key", "FutureWork", "key"),
    ("author_name", "Author", "name"),
    ("gap_key", "Gap", "key"),
]


async def ensure_schema() -> None:
    for name in _LEGACY_CONSTRAINTS:
        await run_query(f"DROP CONSTRAINT {name} IF EXISTS")
    for name, label, prop in _CONSTRAINTS:
        await run_query(
            f"CREATE CONSTRAINT {name} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
        )