from pydantic import BaseModel


class ComparisonRow(BaseModel):
    paper_id: str
    title: str
    year: int | None
    methods: list[str]
    datasets: list[str]


class ComparisonResponse(BaseModel):
    rows: list[ComparisonRow]


class RelatedPaper(BaseModel):
    paper_id: str
    title: str
    year: int | None


class RelatedPapersResponse(BaseModel):
    entity_type: str
    entity_name: str
    related_papers: list[RelatedPaper]