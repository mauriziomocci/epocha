"""Text chunking service using langchain_text_splitters.

Produces sentence-aware chunks with overlap. Chunk size and overlap are
configured in versions.py. The service returns lightweight ChunkResult
dataclasses; persistence is handled separately so the chunker remains
pure and testable without a database.
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .versions import (
    CHUNK_CHARS_PER_TOKEN,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_SIZE_TOKENS,
)

_SEPARATORS: list[str] = ["\n\n", "\n", ". ", "; ", " -- ", " ", ""]


@dataclass(frozen=True)
class ChunkResult:
    """A single chunk with offsets into the original text."""

    chunk_index: int
    text: str
    start_char: int
    end_char: int


def split_text_into_chunks(
    text: str,
    *,
    chunk_size_chars: int | None = None,
    chunk_overlap_chars: int | None = None,
    max_chunks: int = 50,
) -> list[ChunkResult]:
    """Split text into overlapping chunks with sentence-aware boundaries."""
    if not text:
        return []

    size = chunk_size_chars or (CHUNK_SIZE_TOKENS * CHUNK_CHARS_PER_TOKEN)
    overlap = chunk_overlap_chars or (CHUNK_OVERLAP_TOKENS * CHUNK_CHARS_PER_TOKEN)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )

    raw_chunks = splitter.split_text(text)

    results: list[ChunkResult] = []
    cursor = 0
    for i, chunk_text in enumerate(raw_chunks):
        if i >= max_chunks:
            break
        search_start = max(0, cursor - overlap)
        idx = text.find(chunk_text, search_start)
        if idx == -1:
            idx = text.find(chunk_text)
            if idx == -1:
                continue
        results.append(ChunkResult(
            chunk_index=i,
            text=chunk_text,
            start_char=idx,
            end_char=idx + len(chunk_text),
        ))
        cursor = idx + len(chunk_text)

    return results
