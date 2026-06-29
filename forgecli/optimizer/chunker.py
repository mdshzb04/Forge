"""Chunkers split long content into model-sized pieces."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


class SupportsLen(Protocol):
    """Minimal protocol for anything with a ``text`` attribute."""

    text: str


@dataclass(frozen=True)
class Chunk:
    """A piece of content along with its provenance."""

    text: str
    index: int
    start: int
    end: int
    source_id: str | None = None


class Chunker:
    """Split text into overlapping windows of ``size`` characters.

    This is intentionally the dumbest possible chunker; smarter chunkers
    (e.g. AST-aware, sentence-aware) can be added by implementing the
    same interface and registering them with the optimizer.
    """

    def __init__(self, *, size: int = 4000, overlap: int = 200) -> None:
        if size <= 0:
            raise ValueError("chunk size must be positive")
        if overlap < 0 or overlap >= size:
            raise ValueError("overlap must be in [0, size)")
        self._size = size
        self._overlap = overlap

    @property
    def size(self) -> int:
        return self._size

    @property
    def overlap(self) -> int:
        return self._overlap

    def split(self, text: str, *, source_id: str | None = None) -> list[Chunk]:
        """Split ``text`` into chunks of up to ``self.size`` characters."""
        if not text:
            return []
        chunks: list[Chunk] = []
        step = self._size - self._overlap
        idx = 0
        pos = 0
        n = len(text)
        while pos < n:
            end = min(pos + self._size, n)
            chunks.append(
                Chunk(
                    text=text[pos:end],
                    index=idx,
                    start=pos,
                    end=end,
                    source_id=source_id,
                )
            )
            idx += 1
            if end == n:
                break
            pos += step
        return chunks

    def split_many(
        self,
        items: Iterable[tuple[str, str | None]],
    ) -> list[Chunk]:
        """Split several texts; ``items`` yields ``(text, source_id)`` pairs."""
        result: list[Chunk] = []
        for text, source_id in items:
            result.extend(self.split(text, source_id=source_id))
        return result
