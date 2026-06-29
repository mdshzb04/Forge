"""A :class:`Provider` decorator that runs a :class:`PromptOptimizer`
on every chat request before delegating to the wrapped provider.

The decorator is transparent for every other operation (``stream``,
``embed``, ``list_models``) — those either pass through unchanged or
inherit the base behaviour.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from forgecli.optimizer.ponytail import OptimizedRequest, PromptOptimizer
from forgecli.providers.base import (
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelInfo,
    Provider,
    StreamChunk,
)


class OptimizedProvider(Provider[Any]):
    """Wrap a :class:`Provider` so every chat call is pre-optimized."""

    name = "optimized"

    def __init__(
        self,
        base: Provider[Any],
        optimizer: PromptOptimizer,
    ) -> None:
        # The wrapped provider already has its own concrete config; we
        # expose it via ``.config`` for compatibility.
        super().__init__(base.config)
        self._base = base
        self._optimizer = optimizer

    @property
    def base(self) -> Provider[Any]:
        return self._base

    @property
    def optimizer(self) -> PromptOptimizer:
        return self._optimizer

    async def chat(self, request: ChatRequest) -> ChatResponse:
        optimized: OptimizedRequest = await self._optimizer.optimize_chat(request)
        return await self._base.chat(optimized.request)

    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        optimized: OptimizedRequest = await self._optimizer.optimize_chat(request)
        async for chunk in self._base.stream(optimized.request):
            yield chunk

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        # Embedding calls don't carry chat messages; pass through.
        return await self._base.embed(request)

    async def list_models(self) -> list[ModelInfo]:
        return await self._base.list_models()

    def validate(self) -> None:
        return self._base.validate()


__all__ = ["OptimizedProvider"]
