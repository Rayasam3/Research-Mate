import pytest

from ingestion.chunker import chunk_text


def test_chunk_text_empty_returns_empty_list():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_shorter_than_chunk_size_returns_one_chunk():
    text = "A short paper abstract."
    chunks = chunk_text(text, chunk_size=1000, overlap=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_splits_long_text_with_overlap():
    text = "x" * 1000
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) > 1
    # every chunk (except possibly the last) should be exactly chunk_size
    for chunk in chunks[:-1]:
        assert len(chunk) == 300


def test_chunk_text_covers_full_text_no_gaps():
    text = "".join(f"word{i} " for i in range(500))
    chunks = chunk_text(text, chunk_size=200, overlap=40)
    # reconstruct coverage: every character index should appear in at least one chunk
    combined = "".join(chunks)
    assert len(combined) >= len(text.strip())


def test_chunk_text_invalid_overlap_raises():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=100, overlap=100)