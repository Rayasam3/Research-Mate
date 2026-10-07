from pydantic import BaseModel


class MethodInfo(BaseModel):
    name: str
    role: str | None = None        # proposed | baseline | used
    novelty: str | None = None     # what is new about it (proposed methods)
    shared: bool = False           # also used by another compared paper


class ComparisonRow(BaseModel):
    paper_id: str
    title: str
    year: int | None = None
    citations: int | None = None
    domain: str | None = None
    task: str | None = None
    methods: list[MethodInfo]
    unique_methods: list[str]
    datasets: list[str]
    n_limitations: int = 0
    n_future_work: int = 0


class ComparisonResponse(BaseModel):
    rows: list[ComparisonRow]


class RelatedPaper(BaseModel):
    paper_id: str
    title: str
    year: int | None = None


class RelatedPapersResponse(BaseModel):
    entity_type: str
    entity_name: str
    related_papers: list[RelatedPaper]


class GraphNode(BaseModel):
    id: str
    name: str | None = None
    type: str
    year: int | None = None
    detail: str | None = None
    strength: str | None = None
    role: str | None = None        # methods only: proposed | baseline | used


class GraphLink(BaseModel):
    source: str
    target: str
    type: str
    role: str | None = None
    metric: str | None = None
    value: str | None = None


class GraphViewResponse(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]
