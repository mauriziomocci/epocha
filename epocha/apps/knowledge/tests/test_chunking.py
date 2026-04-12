"""Tests for the chunking service."""
import pytest

from epocha.apps.knowledge.chunking import split_text_into_chunks, ChunkResult


class TestSplitTextIntoChunks:
    def test_short_text_single_chunk(self):
        text = "This is a short text."
        chunks = split_text_into_chunks(text)
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len(text)
        assert chunks[0].chunk_index == 0

    def test_long_text_multiple_chunks(self):
        text = ("The Bastille was stormed. " * 200).strip()
        chunks = split_text_into_chunks(text)
        assert len(chunks) >= 2
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunk_indices_sequential(self):
        text = ("a. " * 2000).strip()
        chunks = split_text_into_chunks(text)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_respects_max_chunks_limit(self):
        text = ("word " * 100000).strip()
        chunks = split_text_into_chunks(text, max_chunks=5)
        assert len(chunks) == 5

    def test_offsets_are_valid(self):
        text = "First sentence. Second sentence. Third sentence."
        chunks = split_text_into_chunks(text)
        for chunk in chunks:
            assert 0 <= chunk.start_char < chunk.end_char
            assert chunk.end_char <= len(text)
            assert chunk.text.strip() != ""

    def test_empty_text(self):
        chunks = split_text_into_chunks("")
        assert chunks == []
