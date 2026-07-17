"""Chunking behaviour."""

from __future__ import annotations

import pytest

from multirag.rag.chunking import chunk_text


def test_short_text_produces_single_chunk():
    chunks = chunk_text("Hello world.", chunk_size=800, chunk_overlap=100)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello world."


def test_empty_text_produces_no_chunks():
    assert chunk_text("", chunk_size=800) == []
    assert chunk_text("   \n  ", chunk_size=800) == []


def test_paragraph_boundaries_are_preferred():
    text = ("A" * 300) + "\n\n" + ("B" * 300) + "\n\n" + ("C" * 300)
    chunks = chunk_text(text, chunk_size=400, chunk_overlap=50)
    assert len(chunks) >= 2
    # No chunk should exceed 400 + a bit of slack from overlap merges
    assert all(len(c.text) <= 600 for c in chunks)


def test_overlap_must_be_less_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("some content", chunk_size=100, chunk_overlap=100)


def test_chunks_are_indexed_sequentially():
    text = " ".join(["word"] * 500)
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=30)
    indices = [c.index for c in chunks]
    assert indices == list(range(len(chunks)))
