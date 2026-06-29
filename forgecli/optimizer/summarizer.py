"""Summarization interface (placeholder)."""

from __future__ import annotations

from forgecli.core.service import Service
from forgecli.optimizer.chunker import Chunk
from forgecli.providers.base import ChatMessage, ChatRequest, Provider, Role


class Summarizer(Service):
    """Condenses a sequence of chunks using a chat provider.

    The summarizer is intentionally a thin wrapper around :class:`Provider`
    so we can swap between AI-backed and heuristic implementations without
    touching call sites.
    """

    name = "optimizer.summarizer"

    def __init__(self, provider: Provider, *, model: str | None = None) -> None:
        super().__init__()
        self._provider = provider
        self._model = model

    async def summarize(self, chunks: list[Chunk], *, max_words: int = 200) -> str:
        """Return a textual summary of ``chunks`` (placeholder)."""
        joined = "\n\n".join(c.text for c in chunks)
        if not joined:
            return ""
        request = ChatRequest(
            model=self._model,
            messages=[
                ChatMessage(
                    role=Role.SYSTEM,
                    content=(
                        "You are a concise code-aware summarizer. "
                        f"Respond in at most {max_words} words."
                    ),
                ),
                ChatMessage(role=Role.USER, content=joined),
            ],
        )
        response = await self._provider.chat(request)
        return response.message.content
