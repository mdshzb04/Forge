"""High-level context orchestrator: chunk → rank → (optionally) summarize."""



from __future__ import annotations

from dataclasses import dataclass, field

from forgecli.core.service import Service
from forgecli.optimizer.chunker import Chunk, Chunker
from forgecli.optimizer.ranker import Ranker
from forgecli.optimizer.summarizer import Summarizer


@dataclass

class OptimizedContext:

    """The output of :meth:`ContextOptimizer.optimize`."""



    chunks: list[Chunk] = field(default_factory=list)

    summary: str = ""

    total_chars: int = 0





class ContextOptimizer(Service):

    """Orchestrates chunking, ranking, and summarization."""



    name = "optimizer"



    def __init__(

        self,

        *,

        chunker: Chunker | None = None,

        ranker: Ranker | None = None,

        summarizer: Summarizer | None = None,

        max_context_tokens: int = 200_000,

    ) -> None:

        super().__init__()

        self._chunker = chunker or Chunker()

        self._ranker = ranker or Ranker()

        self._summarizer = summarizer

        self._max_tokens = max_context_tokens



    @property

    def chunker(self) -> Chunker:

        return self._chunker



    @property

    def ranker(self) -> Ranker:

        return self._ranker



    @property

    def summarizer(self) -> Summarizer | None:

        return self._summarizer



    def optimize(

        self,

        text: str,

        *,

        query: str = "",

        source_id: str | None = None,

    ) -> OptimizedContext:

        """Chunk ``text`` and rank it against ``query`` (no AI call)."""

        chunks = self._chunker.split(text, source_id=source_id)

        if query:

            ranked = self._ranker.rank(query, chunks)

            chunks = [chunk for chunk, _score in ranked]

        return OptimizedContext(

            chunks=chunks,

            total_chars=sum(len(c.text) for c in chunks),

        )



    async def optimize_and_summarize(

        self,

        text: str,

        *,

        query: str = "",

        source_id: str | None = None,

    ) -> OptimizedContext:

        """Like :meth:`optimize` but produces a summary when a summarizer is set."""

        ctx = self.optimize(text, query=query, source_id=source_id)

        if self._summarizer is not None and ctx.chunks:

            ctx.summary = await self._summarizer.summarize(ctx.chunks)

        return ctx

