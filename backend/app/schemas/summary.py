"""
The primary user-facing output of Phase 3: a plain-English summary card
for one paper, plus ready-to-use citations. Citations are generated
directly from stored metadata (no LLM involved), so they're always
accurate; the narrative fields come from the LLM, grounded in the paper's
actual stored chunks.
"""
from enum import Enum

from pydantic import BaseModel


class SummaryStatus(str, Enum):
    SUCCESS = "success"
    ALREADY_CACHED = "already_cached"
    NOT_INGESTED = "not_ingested"
    NO_CHUNKS_AVAILABLE = "no_chunks_available"
    LLM_FAILED = "llm_failed"


class PaperSummaryCard(BaseModel):
    tldr: str
    problem: str
    method_explained: str
    key_results: str
    limitations: str
    citation_apa: str
    citation_bibtex: str


class SummarizeRequest(BaseModel):
    force: bool = False  # bypass cache and regenerate even if already summarized


class SummarizeResponse(BaseModel):
    paper_id: str
    status: SummaryStatus
    card: PaperSummaryCard | None = None
    message: str | None = None