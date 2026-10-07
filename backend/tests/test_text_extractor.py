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

# ---- new: column order, tables, cleanup, abstract -------------------------

from ingestion.text_extractor import (
    find_abstract,
    find_figure_captions,
    fix_hyphenation,
    normalize_text,
    order_blocks,
    remove_repeated_lines,
)


def test_order_blocks_reads_left_column_before_right_column():
    width = 600
    blocks = [
        (320, 100, 560, 200, "right top"),
        (40, 100, 280, 200, "left top"),
        (40, 220, 280, 300, "left bottom"),
        (320, 220, 560, 300, "right bottom"),
    ]
    texts = [b[4] for b in order_blocks(blocks, width)]
    assert texts == ["left top", "left bottom", "right top", "right bottom"]


def test_order_blocks_keeps_full_width_title_first():
    blocks = [
        (40, 200, 280, 300, "left"),
        (40, 20, 560, 60, "TITLE"),
        (320, 200, 560, 300, "right"),
    ]
    assert [b[4] for b in order_blocks(blocks, 600)] == ["TITLE", "left", "right"]


def test_table_in_pdf_is_extracted_as_rows(tmp_path):
    import fitz

    path = tmp_path / "table.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 60), "Results on benchmark data. " * 6)
    x0, y0, cw, rh = 72, 120, 90, 24
    for r in range(3):
        for c in range(3):
            rect = fitz.Rect(x0 + c * cw, y0 + r * rh, x0 + (c + 1) * cw, y0 + (r + 1) * rh)
            page.draw_rect(rect, color=(0, 0, 0), width=0.8)
            page.insert_text((rect.x0 + 4, rect.y0 + 16), ["Model", "Acc", "F1", "GCN", "81.5", "80.1", "GAT", "83.0", "82.2"][r * 3 + c])
    doc.save(str(path))
    doc.close()

    result = extract_text(path)
    assert result.tables, "the table should be found"
    assert "81.5" in result.tables[0]
    assert "[TABLE]" in result.full_text


def test_fix_hyphenation_and_ligatures():
    assert fix_hyphenation("graph auto-\ncoders") == "graph autocoders"
    assert normalize_text("signiﬁcant ﬁelds") == "significant fields"


def test_normalize_text_removes_arxiv_side_stamp():
    assert "arXiv" not in normalize_text("text\narXiv:1901.00596v4  [cs.LG]  4 Dec 2019\nmore")


def test_remove_repeated_lines_drops_running_header():
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    pages = [f"JOURNAL OF TEST, VOL. 1\nreal {w} content\n{i}" for i, w in enumerate(words)]
    cleaned = remove_repeated_lines(pages)
    assert all("JOURNAL" not in p for p in cleaned)
    assert "real delta content" in cleaned[3]


def test_find_figure_captions():
    text = "body\nFig. 1: 2D convolution vs graph convolution.\nmore\nTable 2: Results on Cora."
    assert find_figure_captions(text) == ["Fig. 1: 2D convolution vs graph convolution.", "Table 2: Results on Cora."]


def test_find_abstract_stops_at_index_terms():
    text = "Title\nAuthors\nAbstract—" + "Deep learning on graphs is hard. " * 12 + "\nIndex Terms—graphs\nI. INTRODUCTION"
    abstract = find_abstract(text)
    assert abstract.startswith("Deep learning on graphs")
    assert "Index Terms" not in abstract


def test_find_abstract_returns_none_when_missing():
    assert find_abstract("Just some text without the word.") is None
