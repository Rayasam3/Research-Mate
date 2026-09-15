import pytest

from ingestion.text_extractor import (
    PdfExtractionError,
    ScannedPdfError,
    extract_text,
)


def test_extract_text_from_normal_pdf(text_pdf_path):
    result = extract_text(text_pdf_path)
    assert result.page_count == 3
    assert "transformer attention" in result.full_text
    assert "94.2%" in result.full_text
    assert len(result.pages) == 3


def test_extract_text_raises_on_scanned_pdf(blank_pdf_path):
    with pytest.raises(ScannedPdfError):
        extract_text(blank_pdf_path)


def test_extract_text_raises_on_corrupt_pdf(corrupt_pdf_path):
    with pytest.raises(PdfExtractionError):
        extract_text(corrupt_pdf_path)