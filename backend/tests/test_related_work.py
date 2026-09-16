from datetime import date

import pytest

from app.schemas.paper import Paper, PaperSource
from app.services import related_work
from app.services.llm_client import LlmError


def _paper(**overrides) -> Paper:
    defaults = dict(
        external_id="1706.03762",
        source=PaperSource.ARXIV,
        title="Attention Is All You Need",
        authors=["Ashish Vaswani"],
        abstract="A transformer paper.",
        published_date=date(2017, 6, 12),
        pdf_url="https://arxiv.org/pdf/1706.03762",
        doi=None,
        url="https://arxiv.org/abs/1706.03762",
    )
    defaults.update(overrides)
    return Paper(**defaults)


@pytest.mark.asyncio
async def test_build_draft_skips_papers_with_no_cached_summary(monkeypatch):
    monkeypatch.setattr(related_work, "_load_cached_summary", lambda paper_id: None)
    monkeypatch.setattr(related_work, "load_paper_metadata", lambda paper_id: _paper())

    result = await related_work.build_related_work_draft(["missing_paper"])
    assert result["paragraph"] == ""
    assert result["skipped_paper_ids"] == ["missing_paper"]


@pytest.mark.asyncio
async def test_build_draft_success(monkeypatch):
    monkeypatch.setattr(
        related_work,
        "_load_cached_summary",
        lambda paper_id: {"tldr": "Introduces the Transformer.", "citation_bibtex": "@article{vaswani2017,...}"},
    )
    monkeypatch.setattr(related_work, "load_paper_metadata", lambda paper_id: _paper())

    async def fake_generate_json(prompt):
        return {"paragraph": "Vaswani (2017) introduced the Transformer architecture."}

    monkeypatch.setattr(related_work, "generate_json", fake_generate_json)

    result = await related_work.build_related_work_draft(["arxiv_1706.03762"])
    assert "Transformer" in result["paragraph"]
    assert result["bibtex_references"] == ["@article{vaswani2017,...}"]
    assert result["skipped_paper_ids"] == []


@pytest.mark.asyncio
async def test_build_draft_all_papers_missing_returns_empty(monkeypatch):
    monkeypatch.setattr(related_work, "_load_cached_summary", lambda paper_id: None)
    monkeypatch.setattr(related_work, "load_paper_metadata", lambda paper_id: None)

    result = await related_work.build_related_work_draft(["p1", "p2"])
    assert result["paragraph"] == ""
    assert result["bibtex_references"] == []
    assert set(result["skipped_paper_ids"]) == {"p1", "p2"}


@pytest.mark.asyncio
async def test_build_draft_llm_failure_returns_empty_paragraph_but_keeps_references(monkeypatch):
    monkeypatch.setattr(
        related_work,
        "_load_cached_summary",
        lambda paper_id: {"tldr": "Some summary.", "citation_bibtex": "@article{x,...}"},
    )
    monkeypatch.setattr(related_work, "load_paper_metadata", lambda paper_id: _paper())

    async def fake_generate_json(prompt):
        raise LlmError("boom")

    monkeypatch.setattr(related_work, "generate_json", fake_generate_json)

    result = await related_work.build_related_work_draft(["arxiv_1706.03762"])
    assert result["paragraph"] == ""
    assert result["bibtex_references"] == ["@article{x,...}"]