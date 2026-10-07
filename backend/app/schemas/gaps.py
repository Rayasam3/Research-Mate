from pydantic import BaseModel, Field


class Evidence(BaseModel):
    title: str
    year: int | None = None


class AuthorHint(BaseModel):
    kind: str          # "future_work" or "limitation"
    text: str
    paper_title: str


class UntestedCombination(BaseModel):
    method: str
    dataset: str
    statement: str
    strength: str      # "strong" | "moderate" | "weak"
    score: float
    method_evidence: list[Evidence]
    dataset_evidence: list[Evidence]
    author_hint: AuthorHint | None = None
    caveats: list[str]


class StatedItem(BaseModel):
    text: str
    paper_id: str
    paper_title: str
    year: int | None = None
    citations: int | None = None


class GapSummary(BaseModel):
    papers: int
    core_methods: int
    datasets: int
    pairs_not_tested: int


class GapAnalysisResponse(BaseModel):
    untested_combinations: list[UntestedCombination]
    future_work: list[StatedItem]
    limitations: list[StatedItem]
    summary: GapSummary


class DraftRelatedWorkRequest(BaseModel):
    paper_ids: list[str] = Field(..., min_length=1, max_length=20)


class DraftRelatedWorkResponse(BaseModel):
    paragraph: str
    bibtex_references: list[str]
    skipped_paper_ids: list[str]
