"""Tests for the ResponseForge CLI adapter and the ResponseForgeProvider decorator."""



from __future__ import annotations

import asyncio
from typing import Any

import pytest

from forgecli.optimizer.responseforge import (
    ResponseForgeIntensity,
    ResponseForgePromptOptimizer,
    ResponseForgeRulesetOptimizer,
)
from forgecli.optimizer.responseforge.cli import ResponseForgeCLIOptimizer
from forgecli.optimizer.responseforge.decorator import ResponseForgeProvider
from forgecli.providers.base import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Provider,
    Role,
)


def _request(*messages: ChatMessage) -> ChatRequest:

    return ChatRequest(model="m", messages=list(messages))





def test_is_available_uses_path(monkeypatch) -> None:

    opt = ResponseForgeCLIOptimizer(executable="responseforge")

    monkeypatch.setattr(

        "shutil.which", lambda name: "/usr/bin/responseforge" if name == "responseforge" else None

    )

    assert asyncio.run(opt.is_available()) is True

    monkeypatch.setattr("shutil.which", lambda name: None)

    assert asyncio.run(opt.is_available()) is False





def test_cli_stub_returns_passthrough(monkeypatch) -> None:

    opt = ResponseForgeCLIOptimizer(executable="responseforge")

    monkeypatch.setattr(

        "shutil.which", lambda name: "/usr/bin/responseforge" if name == "responseforge" else None

    )

    result = asyncio.run(opt.optimize_chat(_request(ChatMessage(role=Role.USER, content="hi"))))

    assert result.source == "responseforge-cli"

    assert any("CLI stub" in n for n in result.notes)





class _StubProvider(Provider[Any]):

    """Minimal Provider stand-in used by the decorator tests."""



    name = "stub"



    def __init__(self) -> None:

        super().__init__(object())

        self.calls: list[ChatRequest] = []



    async def chat(self, request: ChatRequest) -> ChatResponse:

        self.calls.append(request)

        return ChatResponse(

            model="m",

            message=ChatMessage(role=Role.ASSISTANT, content="ok"),

            finish_reason="stop",

        )



    async def embed(self, request: Any) -> Any:  # pragma: no cover - not exercised

        raise NotImplementedError



    async def list_models(self) -> list[Any]:  # pragma: no cover

        return []





def test_responseforge_provider_runs_optimizer_before_chat() -> None:

    base = _StubProvider()

    ruleset = ResponseForgeRulesetOptimizer(intensity=ResponseForgeIntensity.FULL)

    wrapped = ResponseForgeProvider(base=base, optimizer=ruleset)

    response = asyncio.run(wrapped.chat(_request(ChatMessage(role=Role.USER, content="hi"))))

    assert response.message.content == "ok"

    assert len(base.calls) == 1

    sent = base.calls[0]

    assert sent.messages[0].role is Role.SYSTEM

    assert "CAVEMAN (full)" in sent.messages[0].content





def test_responseforge_provider_passes_through_when_optimizer_off() -> None:

    from forgecli.optimizer.responseforge import OptimizedRequest



    class _PassthroughOpt(ResponseForgePromptOptimizer):

        name = "responseforge-passthrough"



        async def optimize_chat(self, request: ChatRequest) -> OptimizedRequest:

            return OptimizedRequest(

                request=request,

                notes=("responseforge noop",),

                intensity=ResponseForgeIntensity.OFF,

                source="responseforge-passthrough",

            )



    base = _StubProvider()

    wrapped = ResponseForgeProvider(base=base, optimizer=_PassthroughOpt())

    asyncio.run(wrapped.chat(_request(ChatMessage(role=Role.USER, content="hi"))))

    sent = base.calls[0]

    assert [m.content for m in sent.messages] == ["hi"]





def test_responseforge_provider_embed_passthrough() -> None:

    from forgecli.providers.base import EmbeddingRequest, EmbeddingResponse



    class _Stub(_StubProvider):

        async def embed(self, request):

            return EmbeddingResponse(model="m", vectors=[[0.1, 0.2]])



    base = _Stub()

    ruleset = ResponseForgeRulesetOptimizer(intensity=ResponseForgeIntensity.FULL)

    wrapped = ResponseForgeProvider(base=base, optimizer=ruleset)

    response = asyncio.run(wrapped.embed(EmbeddingRequest(inputs=["hi"])))

    assert response.vectors == [[0.1, 0.2]]







_ = pytest

_ = Any  # type: ignore[assignment]

