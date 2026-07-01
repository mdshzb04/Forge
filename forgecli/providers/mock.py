"""A deterministic provider used in tests and offline development."""

from __future__ import annotations

import hashlib
from typing import ClassVar

from forgecli.providers.base import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelInfo,
    Provider,
    Role,
    StreamChunk,
)
from forgecli.providers.conversation import (
    greeting_reply,
    is_greeting,
    offline_build_notice,
)


class MockProviderConfig:
    """Configuration for :class:`MockProvider`."""

    def __init__(self, default_model: str = "mock-model", max_tokens: int = 1024) -> None:
        self.default_model = default_model
        self.max_tokens = max_tokens


class MockProvider(Provider[MockProviderConfig]):
    """Offline provider for tests and explicit ``--mock`` mode."""

    name: ClassVar[str] = "mock"
    _MODELS: ClassVar[list[ModelInfo]] = [
        ModelInfo(id="mock-model", name="Mock Model", context_window=8192),
    ]

    def __init__(self, config: MockProviderConfig | None = None) -> None:
        super().__init__(config or MockProviderConfig())

    async def chat(self, request: ChatRequest) -> ChatResponse:
        last_user = next(
            (m for m in reversed(request.messages) if m.role is Role.USER),
            None,
        )
        text = last_user.content if last_user else ""

        has_diff_request = any(
            m.role is Role.SYSTEM and "unified diff" in m.content.lower()
            for m in request.messages
        )

        has_commit_request = any(
            "commit" in m.content.lower()
            for m in request.messages
        ) or "commit" in text.lower()

        if has_commit_request:
            content = (
                "feat(auth): add secure provider authentication\n\n"
                "- add OS keychain credential storage\n"
                "- support provider selection\n"
                "- improve onboarding flow\n"
                "- add regression tests"
            )
        elif has_diff_request:
            content = offline_build_notice()
        elif is_greeting(text):
            content = greeting_reply(text)
        else:
            content = (
                "I'm running in offline mode without a configured AI provider. "
                "Ask a question about your codebase after configuring an API key, "
                "or pass `--mock` explicitly to stay offline."
            )

        return ChatResponse(
            model=request.model or self.config.default_model,
            message=ChatMessage(role=Role.ASSISTANT, content=content),
            finish_reason="stop",
            prompt_tokens=len(text),
            completion_tokens=len(content),
            total_tokens=len(text) + len(content),
        )

    async def stream(self, request: ChatRequest):
        response = await self.chat(request)
        if response.message.content:
            yield StreamChunk(delta=response.message.content, raw=response.raw)
        yield StreamChunk(delta="", finish_reason="stop")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        vectors: list[list[float]] = []
        for text in request.inputs:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vec = [b / 255.0 for b in digest[:16]]
            vectors.append(vec)
        return EmbeddingResponse(
            model=request.model or self.config.default_model,
            vectors=vectors,
            prompt_tokens=sum(len(t) for t in request.inputs),
            total_tokens=sum(len(t) for t in request.inputs),
        )

    async def list_models(self) -> list[ModelInfo]:
        return list(self._MODELS)


__all__ = ["MockProvider", "MockProviderConfig"]
