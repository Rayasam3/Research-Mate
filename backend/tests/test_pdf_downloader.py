import pytest

from ingestion import pdf_downloader
from ingestion.pdf_downloader import PdfDownloadError, download_pdf, find_pdf_link, is_pdf_bytes

PDF_BYTES = b"%PDF-1.5\nfake pdf body"


def test_is_pdf_bytes():
    assert is_pdf_bytes(PDF_BYTES)
    assert not is_pdf_bytes(b"<html><body>landing page</body></html>")


def test_find_pdf_link_prefers_citation_meta_tag():
    html = '<html><head><meta name="citation_pdf_url" content="/files/paper.pdf"></head></html>'
    assert find_pdf_link(html, "https://example.org/article/1") == "https://example.org/files/paper.pdf"


def test_find_pdf_link_falls_back_to_pdf_href():
    html = '<a href="https://cdn.example.org/x.pdf">Download</a>'
    assert find_pdf_link(html, "https://example.org/a") == "https://cdn.example.org/x.pdf"


def test_find_pdf_link_none_when_absent():
    assert find_pdf_link("<html>nothing</html>", "https://example.org") is None


@pytest.mark.asyncio
async def test_download_saves_a_real_pdf(monkeypatch, tmp_path):
    async def fake_fetch(url):
        return PDF_BYTES

    monkeypatch.setattr(pdf_downloader, "_fetch", fake_fetch)
    dest = tmp_path / "a.pdf"
    await download_pdf("https://example.org/a.pdf", dest)
    assert dest.read_bytes() == PDF_BYTES


@pytest.mark.asyncio
async def test_download_follows_landing_page_to_real_pdf(monkeypatch, tmp_path):
    pages = {
        "https://example.org/article": b'<meta name="citation_pdf_url" content="https://example.org/real.pdf">',
        "https://example.org/real.pdf": PDF_BYTES,
    }

    async def fake_fetch(url):
        return pages[url]

    monkeypatch.setattr(pdf_downloader, "_fetch", fake_fetch)
    dest = tmp_path / "a.pdf"
    await download_pdf("https://example.org/article", dest)
    assert dest.read_bytes() == PDF_BYTES


@pytest.mark.asyncio
async def test_download_rejects_html_page_without_pdf_link(monkeypatch, tmp_path):
    async def fake_fetch(url):
        return b"<html>Please log in</html>"

    monkeypatch.setattr(pdf_downloader, "_fetch", fake_fetch)
    dest = tmp_path / "a.pdf"
    with pytest.raises(PdfDownloadError):
        await download_pdf("https://example.org/article", dest)
    assert not dest.exists()
