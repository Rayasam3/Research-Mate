"""
Splits full paper text into overlapping chunks. A sliding window over
characters (not a fancier section-aware split) is a deliberate simple
first pass - it's reliable across every paper's formatting, and section-
aware chunking is a reasonable improvement to revisit later without
changing anything downstream (chunks are just strings either way).
"""
from app.core.config import settings


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[str]:
    size = chunk_size or settings.chunk_size_chars
    step = size - (overlap if overlap is not None else settings.chunk_overlap_chars)

    if step <= 0:
        raise ValueError("chunk_overlap_chars must be smaller than chunk_size_chars")

    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == text_len:
            break
        start += step

    return chunks