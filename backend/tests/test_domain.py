from datetime import date

from app.schemas.paper import Paper, PaperSource
from app.services import domain


def _paper(i, title, field="Computer Science", **kw):
    data = dict(
        external_id=str(i), source=PaperSource.ARXIV, title=title, abstract="text",
        published_date=date(2024, 1, 1), pdf_url="http://x/p.pdf", field=field,
    )
    data.update(kw)
    return Paper(**data)


def test_canonical_field_maps_source_labels():
    assert domain.canonical_field("Computer Science") == "Computer Science"
    assert domain.canonical_field("Biochemistry, Genetics and Molecular Biology") == "Biology & Life Sciences"
    assert domain.canonical_field("Physics and Astronomy") == "Physics"
    assert domain.canonical_field("Chemical Engineering") == "Engineering"
    assert domain.canonical_field("Something unknown") == "Other"
    assert domain.canonical_field(None) is None


def test_field_from_arxiv_category():
    assert domain.field_from_arxiv_category("cs.LG") == "Computer Science"
    assert domain.field_from_arxiv_category("q-bio.NC") == "Biology & Life Sciences"
    assert domain.field_from_arxiv_category("hep-th") == "Physics"
    assert domain.field_from_arxiv_category(None) is None


def test_detect_field_majority_vote():
    papers = [_paper(1, "a"), _paper(2, "b"), _paper(3, "c", field="Medicine & Health")]
    field, counts = domain.detect_field(papers)
    assert field == "Computer Science"
    assert counts == {"Computer Science": 2, "Medicine & Health": 1}


def test_detect_field_without_labels():
    assert domain.detect_field([_paper(1, "a", field=None)]) == (None, {})


def test_select_papers_drops_off_topic(monkeypatch):
    # Fake embeddings: the topic and "good" papers point the same way, "bad" the opposite.
    def fake_embed(texts):
        return [[1.0, 0.0] if ("good" in t or t == "topic") else [0.0, 1.0] for t in texts]

    monkeypatch.setattr(domain, "_embed", fake_embed)
    papers = [_paper(1, "good one"), _paper(2, "bad one"), _paper(3, "good two")]
    chosen, info = domain.select_papers("topic", papers, max_papers=5)
    assert [p.title for p in chosen] == ["good one", "good two"] or {p.title for p in chosen} == {"good one", "good two"}
    assert info["dropped_off_topic"] == 1


def test_select_papers_uses_user_field_when_enough_papers(monkeypatch):
    monkeypatch.setattr(domain, "_embed", lambda texts: [[1.0, 0.0] for _ in texts])
    papers = [_paper(1, "a"), _paper(2, "b"), _paper(3, "c", field="Medicine & Health")]
    chosen, info = domain.select_papers("topic", papers, max_papers=2, user_field="Computer Science")
    assert all(p.field == "Computer Science" for p in chosen)
    assert info["dropped_other_field"] == 1


def test_select_papers_never_returns_nothing(monkeypatch):
    monkeypatch.setattr(domain, "_embed", lambda texts: [[1.0, 0.0]] + [[0.0, 1.0]] * (len(texts) - 1))
    chosen, _ = domain.select_papers("topic", [_paper(1, "a"), _paper(2, "b")], max_papers=2)
    assert len(chosen) == 2


def test_select_papers_empty():
    assert domain.select_papers("topic", [], 3)[0] == []


def test_select_papers_keep_returns_whole_ranked_list_with_pdf_first(monkeypatch):
    from app.services import domain

    monkeypatch.setattr(domain, "_embed", lambda texts: [[1.0, 0.0] for _ in texts])
    from app.schemas.paper import Paper, PaperSource

    def mk(i, pdf):
        return Paper(external_id=str(i), source=PaperSource.ARXIV, title=f"p{i}", pdf_url=pdf)

    papers = [mk(1, None), mk(2, "https://x/2.pdf"), mk(3, None), mk(4, "https://x/4.pdf")]
    ranked, _ = domain.select_papers("t", papers, max_papers=1, keep=4)
    assert len(ranked) == 4
    assert {p.external_id for p in ranked[:2]} == {"2", "4"}
