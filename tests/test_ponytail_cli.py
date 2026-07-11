"""Tests for the Ponytail CLI adapter and the OptimizedProvider decorator."""



from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import patch

import pytest

from forgecli.optimizer.ponytail import (
    Intensity,
    PonytailCLIOptimizer,
    PonytailRulesetOptimizer,
    PromptOptimizer,
)
from forgecli.optimizer.ponytail.decorator import OptimizedProvider
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

    opt = PonytailCLIOptimizer(executable="ponytail")

    monkeypatch.setattr(

        "shutil.which", lambda name: "/usr/bin/ponytail" if name == "ponytail" else None

    )

    assert asyncio.run(opt.is_available()) is True

    monkeypatch.setattr("shutil.which", lambda name: None)

    assert asyncio.run(opt.is_available()) is False





def test_optimize_chat_pipes_json_through_subprocess(monkeypatch) -> None:

    opt = PonytailCLIOptimizer(executable="ponytail")

    monkeypatch.setattr(

        "shutil.which", lambda name: "/usr/bin/ponytail" if name == "ponytail" else None

    )



    captured: dict[str, Any] = {}



    class _Proc:

        returncode = 0

        _stdout = json.dumps(

            {

                "model": "m",

                "temperature": 0.1,

                "max_tokens": 100,

                "intensity": "full",

                "notes": ["from external"],

                "messages": [

                    {"role": "system", "content": "guidance"},

                    {"role": "user", "content": "hi"},

                ],

            }

        ).encode("utf-8")

        _stderr = b""



        async def communicate(self):

            return self._stdout, self._stderr



    async def fake_exec(*args, **kwargs):

        captured["args"] = args

        captured["kwargs"] = kwargs

        return _Proc()



    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    result = asyncio.run(opt.optimize_chat(_request(ChatMessage(role=Role.USER, content="hi"))))

    assert captured["args"][0] == "/usr/bin/ponytail"

    assert captured["args"][1] == "optimize"

    assert captured["args"][2] == "--stdin"

    assert result.intensity is Intensity.FULL

    assert result.notes == ("from external",)

    assert result.request.messages[0].role is Role.SYSTEM





def test_optimize_chat_raises_on_nonzero_exit(monkeypatch) -> None:

    opt = PonytailCLIOptimizer(executable="ponytail")

    monkeypatch.setattr(

        "shutil.which", lambda name: "/usr/bin/ponytail" if name == "ponytail" else None

    )



    class _Proc:

        returncode = 1

        _stdout = b""

        _stderr = b"boom"



        async def communicate(self):

            return self._stdout, self._stderr



    async def fake_exec(*args, **kwargs):

        return _Proc()



    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    with pytest.raises(Exception, match="ponytail"):

        asyncio.run(opt.optimize_chat(_request(ChatMessage(role=Role.USER, content="hi"))))





def test_optimize_chat_raises_on_invalid_json(monkeypatch) -> None:

    opt = PonytailCLIOptimizer(executable="ponytail")

    monkeypatch.setattr(

        "shutil.which", lambda name: "/usr/bin/ponytail" if name == "ponytail" else None

    )



    class _Proc:

        returncode = 0

        _stdout = b"not json"

        _stderr = b""



        async def communicate(self):

            return self._stdout, self._stderr



    async def fake_exec(*args, **kwargs):

        return _Proc()



    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)

    with pytest.raises(Exception, match="invalid JSON"):

        asyncio.run(opt.optimize_chat(_request(ChatMessage(role=Role.USER, content="hi"))))





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





def test_optimized_provider_runs_optimizer_before_chat() -> None:

    base = _StubProvider()

    ruleset = PonytailRulesetOptimizer(intensity=Intensity.FULL)

    wrapped = OptimizedProvider(base=base, optimizer=ruleset)

    response = asyncio.run(wrapped.chat(_request(ChatMessage(role=Role.USER, content="hi"))))

    assert response.message.content == "ok"

    assert len(base.calls) == 1

    sent = base.calls[0]



    assert sent.messages[0].role is Role.SYSTEM

    assert "Ponytail (full)" in sent.messages[0].content





def test_optimized_provider_passes_through_when_optimizer_off() -> None:

    from forgecli.optimizer.ponytail import OptimizedRequest



    class _PassthroughOpt(PromptOptimizer):

        name = "passthrough"



        async def optimize_chat(self, request: ChatRequest) -> OptimizedRequest:

            return OptimizedRequest(

                request=request,

                notes=("noop",),

                intensity=Intensity.OFF,

                source="passthrough",

            )



    base = _StubProvider()

    wrapped = OptimizedProvider(base=base, optimizer=_PassthroughOpt())

    asyncio.run(wrapped.chat(_request(ChatMessage(role=Role.USER, content="hi"))))

    sent = base.calls[0]

    assert [m.content for m in sent.messages] == ["hi"]





def test_optimized_provider_embed_passthrough() -> None:

    from forgecli.providers.base import EmbeddingRequest, EmbeddingResponse



    class _Stub(_StubProvider):

        async def embed(self, request):  # type: ignore[override]

            return EmbeddingResponse(model="m", vectors=[[0.1, 0.2]])



    base = _Stub()

    ruleset = PonytailRulesetOptimizer(intensity=Intensity.FULL)

    wrapped = OptimizedProvider(base=base, optimizer=ruleset)  # type: ignore[arg-type]

    response = asyncio.run(wrapped.embed(EmbeddingRequest(inputs=["hi"])))

    assert response.vectors == [[0.1, 0.2]]







_pytest = pytest

_patch = patch

