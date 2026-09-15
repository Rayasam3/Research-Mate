from datetime import date
from pathlib import Path

import pytest

from app.schemas.ingest import IngestStatus
from app.schemas.paper import Paper, PaperSource
from ingestion import pipeline
from ingestion.pdf_downloader import PdfDownloadError


def _paper(**overrides) -> Paper:
    defaults = dict(
        external_id="1706.03762",
        source=PaperSource.ARXIV,
        title="Attention Is All You Need",
        authors=["A. Vaswani"],
        abstract="A transformer paper.",
        published_date=date(2017, 6, 12),
        pdf_url="https://arxiv.org/pdf/1706.03762",
        doi=None,
        url="https://arxiv.org/abs/1706.03762",
    )
    defaults.update(overrides)
    return Paper(**defaults)


def test_make_paper_id_is_stable_and_filesystem_safe():
    paper = _paper(external_id="1706.03762v2")
    paper_id = pipeline.make_paper_id(paper)
    assert paper_id == "arxiv_1706.03762v2"
    assert "/" not in paper_id


@pytest.mark.asyncio
async def test_ingest_paper_no_pdf_url_returns_early():
    paper = _paper(pdf_url=None)
    result = await pipeline.ingest_paper(paper)
    assert result["status"] == IngestStatus.NO_PDF_AVAILABLE
    assert result["chunk_count"] == 0


@pytest.mark.asyncio
async def test_ingest_paper_download_failure_reported_not_raised(monkeypatch):
    async def fake_download(url, dest_path):
        raise PdfDownloadError("boom")

    monkeypatch.setattr(pipeline, "download_pdf", fake_download)
    monkeypatch.setattr(pipeline, "_read_cache_marker", lambda paper_id: None)

    paper = _paper()
    result = await pipeline.ingest_paper(paper)
    assert result["status"] == IngestStatus.DOWNLOAD_FAILED


@pytest.mark.asyncio
async def test_ingest_paper_uses_cache_when_available(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "_read_cache_marker",
        lambda paper_id: {"chunk_count": 7, "page_count": 3},
    )

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("download_pdf should not be called when cached")

    monkeypatch.setattr(pipeline, "download_pdf", fail_if_called)

    paper = _paper()
    result = await pipeline.ingest_paper(paper, force=False)
    assert result["status"] == IngestStatus.ALREADY_CACHED
    assert result["chunk_count"] == 7


@pytest.mark.asyncio
async def test_ingest_paper_full_success_path(monkeypatch, text_pdf_path, tmp_path):
    monkeypatch.setattr(pipeline, "_read_cache_marker", lambda paper_id: None)
    monkeypatch.setattr(pipeline, "_cache_marker_path", lambda paper_id: tmp_path / f"{paper_id}.json")
    monkeypatch.setattr(pipeline, "_pdf_path", lambda paper_id: text_pdf_path)

    async def fake_download(url, dest_path):
        pass  # text_pdf_path already exists on disk via the fixture

    monkeypatch.setattr(pipeline, "download_pdf", fake_download)

    stored_calls = {}

    def fake_upsert_chunks(paper_id, title, chunks):
        stored_calls["paper_id"] = paper_id
        stored_calls["title"] = title
        stored_calls["chunks"] = chunks
        return len(chunks)

    monkeypatch.setattr(pipeline, "upsert_chunks", fake_upsert_chunks)

    paper = _paper()
    result = await pipeline.ingest_paper(paper)

    assert result["status"] == IngestStatus.SUCCESS
    assert result["chunk_count"] > 0
    assert result["page_count"] == 3
    assert stored_calls["title"] == paper.title


@pytest.mark.asyncio
async def test_ingest_paper_scanned_pdf_reported(monkeypatch, blank_pdf_path, tmp_path):
    monkeypatch.setattr(pipeline, "_read_cache_marker", lambda paper_id: None)
    monkeypatch.setattr(pipeline, "_pdf_path", lambda paper_id: blank_pdf_path)

    async def fake_download(url, dest_path):
        pass

    monkeypatch.setattr(pipeline, "download_pdf", fake_download)

    paper = _paper()
    result = await pipeline.ingest_paper(paper)
    assert result["status"] == IngestStatus.SCANNED_PDF