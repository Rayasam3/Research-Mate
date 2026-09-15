"""
Shared pytest fixtures for ingestion tests. Builds tiny real PDFs with
PyMuPDF itself (rather than downloading fixtures), so tests never touch
the network and never need a checked-in binary file.
"""
import fitz
import pytest


@pytest.fixture
def text_pdf_path(tmp_path):
    """A small PDF with real, extractable text - simulates a normal paper."""
    path = tmp_path / "sample_text.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text(
            (72, 72),
            f"Page {i + 1}\n\n"
            "This is a sample research paper about transformer attention "
            "mechanisms. The method achieves 94.2% accuracy on the benchmark "
            "dataset, outperforming prior baselines by a significant margin. "
            "Limitations include high compute cost and sensitivity to sequence length.",
        )
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def blank_pdf_path(tmp_path):
    """A PDF with pages but no text at all - simulates a scanned document."""
    path = tmp_path / "sample_blank.pdf"
    doc = fitz.open()
    for _ in range(2):
        doc.new_page()
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def corrupt_pdf_path(tmp_path):
    """A file with a .pdf extension that isn't actually a valid PDF."""
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"this is not a real pdf file")
    return path