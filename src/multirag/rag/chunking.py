"""Recursive character text splitter.

Splits on progressively finer separators (paragraph -> line -> sentence -> word)
so semantic boundaries are preserved when possible.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


@dataclass
class Chunk:
    text: str
    index: int
    char_start: int
    char_end: int


def chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    separators: list[str] | None = None,
) -> list[Chunk]:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")
    if not text.strip():
        return []

    seps = separators or DEFAULT_SEPARATORS
    pieces = _recursive_split(text, seps, chunk_size)

    # Now merge pieces greedily into windows of ~chunk_size with overlap.
    chunks: list[Chunk] = []
    buffer = ""
    buffer_start = 0
    cursor = 0
    idx = 0

    for piece in pieces:
        piece_start = cursor
        cursor += len(piece)

        if not buffer:
            buffer = piece
            buffer_start = piece_start
            continue

        if len(buffer) + len(piece) <= chunk_size:
            buffer += piece
            continue

        # flush buffer
        chunks.append(
            Chunk(
                text=buffer.strip(),
                index=idx,
                char_start=buffer_start,
                char_end=buffer_start + len(buffer),
            )
        )
        idx += 1
        # Start a new buffer with overlap tail of the previous one.
        tail = buffer[-chunk_overlap:] if chunk_overlap else ""
        buffer = tail + piece
        buffer_start = (buffer_start + len(buffer) - len(tail) - len(piece))

    if buffer.strip():
        chunks.append(
            Chunk(
                text=buffer.strip(),
                index=idx,
                char_start=buffer_start,
                char_end=buffer_start + len(buffer),
            )
        )
    return chunks


def _recursive_split(text: str, separators: list[str], chunk_size: int) -> list[str]:
    if len(text) <= chunk_size or not separators:
        return [text]

    sep = separators[0]
    rest = separators[1:]

    if sep == "":
        # last-ditch: hard character split
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    parts = text.split(sep)
    if len(parts) == 1:
        return _recursive_split(text, rest, chunk_size)

    # re-attach separator to each part except the last so lengths are preserved
    out: list[str] = []
    for i, p in enumerate(parts):
        pretty = p + (sep if i < len(parts) - 1 else "")
        if len(pretty) > chunk_size:
            out.extend(_recursive_split(pretty, rest, chunk_size))
        else:
            out.append(pretty)
    return out
