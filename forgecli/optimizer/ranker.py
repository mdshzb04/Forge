"""Ranks chunks by relevance to a query."""

from __future__ import annotations

from collections.abc import Iterable

from forgecli.optimizer.chunker import Chunk


class Ranker:
    """Default ranker based on simple lexical overlap.

    The interface is deliberately small: ``score(query, chunk)`` returns a
    float; higher is more relevant. Real implementations may use
    embeddings, BM25, or graph-based signals.
    """

    def score(self, query: str, chunk: Chunk) -> float:
        """Score a single ``chunk`` against ``query``."""
        if not query or not chunk.text:
            return 0.0
        q_tokens = self._tokenize(query)
        c_tokens = set(self._tokenize(chunk.text))
        if not q_tokens:
            return 0.0
        hits = sum(1 for token in q_tokens if token in c_tokens)
        return hits / max(len(q_tokens), 1)

    def rank(self, query: str, chunks: Iterable[Chunk]) -> list[tuple[Chunk, float]]:
        """Return ``chunks`` paired with scores, sorted descending by score."""
        scored = [(chunk, self.score(query, chunk)) for chunk in chunks]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [tok.lower() for tok in text.split() if tok]
