"""
Structured record extracted from one paper. Phase 2 fills this from the
full text; the graph is built from it. Every field is optional so a
partial extraction is still usable.
"""
from typing import Literal

from pydantic import BaseModel, Field


class MethodMention(BaseModel):
    name: str
    role: Literal["proposed", "baseline", "used"] = "used"
    novelty: str | None = None  # what is new about it, if the paper says


class ResultItem(BaseModel):
    method: str
    dataset: str
    metric: str | None = None
    value: str | None = None


class PaperRecord(BaseModel):
    domain: str | None = None
    task: str | None = None
    methods: list[MethodMention] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    results: list[ResultItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    future_work: list[str] = Field(default_factory=list)