from pydantic import BaseModel, Field


class GapAnalysisResponse(BaseModel):
    isolated_methods: list[str]
    isolated_datasets: list[str]
    method_gaps: list[str]
    dataset_gaps: list[str]


class DraftRelatedWorkRequest(BaseModel):
    paper_ids: list[str] = Field(..., min_length=1, max_length=20)


class DraftRelatedWorkResponse(BaseModel):
    paragraph: str
    bibtex_references: list[str]
    skipped_paper_ids: list[str]