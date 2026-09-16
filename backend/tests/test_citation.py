from datetime import date

from app.schemas.paper import Paper, PaperSource
from app.services.citation import generate_apa_citation, generate_bibtex_citation


def _paper(**overrides) -> Paper:
    defaults = dict(
        external_id="1706.03762",
        source=PaperSource.ARXIV,
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer"],
        abstract="A transformer paper.",
        published_date=date(2017, 6, 12),
        pdf_url="https://arxiv.org/pdf/1706.03762",
        doi="10.48550/arXiv.1706.03762",
        url="https://arxiv.org/abs/1706.03762",
    )
    defaults.update(overrides)
    return Paper(**defaults)


def test_apa_citation_two_authors():
    citation = generate_apa_citation(_paper())
    assert "Vaswani, A." in citation
    assert "& Shazeer, N." in citation
    assert "(2017)" in citation
    assert "Attention Is All You Need" in citation
    assert "https://doi.org/10.48550/arXiv.1706.03762" in citation


def test_apa_citation_single_author():
    paper = _paper(authors=["Ashish Vaswani"])
    citation = generate_apa_citation(paper)
    assert citation.startswith("Vaswani, A.")


def test_apa_citation_no_authors_falls_back():
    paper = _paper(authors=[])
    citation = generate_apa_citation(paper)
    assert "Unknown Author" in citation


def test_apa_citation_no_date_uses_nd():
    paper = _paper(published_date=None)
    citation = generate_apa_citation(paper)
    assert "(n.d.)" in citation


def test_apa_citation_falls_back_to_url_without_doi():
    paper = _paper(doi=None)
    citation = generate_apa_citation(paper)
    assert "https://arxiv.org/abs/1706.03762" in citation


def test_bibtex_citation_has_required_fields():
    citation = generate_bibtex_citation(_paper())
    assert citation.startswith("@article{vaswani2017attention,")
    assert "title = {Attention Is All You Need}" in citation
    assert "author = {Ashish Vaswani and Noam Shazeer}" in citation
    assert "year = {2017}" in citation
    assert "doi = {10.48550/arXiv.1706.03762}" in citation


def test_bibtex_key_handles_no_authors():
    paper = _paper(authors=[])
    citation = generate_bibtex_citation(paper)
    assert citation.startswith("@article{unknown2017attention,")