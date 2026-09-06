"""
The normalized shape every search source (ArXiv, Semantic Scholar, PubMed)
gets mapped into. Later phases (ingestion, summary cards, knowledge graph)
all build on top of this same object, so keep it source-agnostic.
"""
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class PaperSource(str, Enum):
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PUBMED = "pubmed"


class Paper(BaseModel):
    external_id: str = Field(..., description="Source-native ID, e.g. arxiv id or DOI")
    source: PaperSource
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    published_date: date | None = None
    pdf_url: str | None = None
    doi: str | None = None
    url: str | None = None


class SearchRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=300)
    max_results: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="Cap on total merged results returned. Defaults to settings value.",
    )
    sources: list[PaperSource] | None = Field(
        default=None,
        description="Restrict to specific sources. Defaults to all three.",
    )


class SearchResponse(BaseModel):
    topic: str
    total_results: int
    results: list[Paper]
