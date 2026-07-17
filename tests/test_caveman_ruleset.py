"""Tests for the ResponseForge ruleset prompt optimizer."""



from __future__ import annotations

import asyncio

import pytest

from forgecli.optimizer.responseforge import (
    ResponseForgeCompositeOptimizer,
    ResponseForgeIntensity,
    ResponseForgePromptOptimizer,
    ResponseForgeRulesetOptimizer,
    OptimizedRequest,
)
from forgecli.providers.base import ChatMessage, ChatRequest, Role


def _request(*messages: ChatMessage) -> ChatRequest:

    return ChatRequest(model="test-model", messages=list(messages))





def _user(text: str) -> ChatMessage:

    return ChatMessage(role=Role.USER, content=text)





def _system(text: str) -> ChatMessage:

    return ChatMessage(role=Role.SYSTEM, content=text)





def test_intensity_parse_accepts_known_values() -> None:

    assert ResponseForgeIntensity.parse("off") is ResponseForgeIntensity.OFF

    assert ResponseForgeIntensity.parse("LITE") is ResponseForgeIntensity.LITE

    assert ResponseForgeIntensity.parse("Full") is ResponseForgeIntensity.FULL

    assert ResponseForgeIntensity.parse("ULTRA") is ResponseForgeIntensity.ULTRA

    assert ResponseForgeIntensity.parse("WENYAN") is ResponseForgeIntensity.WENYAN





def test_intensity_parse_defaults_to_lite() -> None:

    assert ResponseForgeIntensity.parse(None) is ResponseForgeIntensity.LITE

    assert ResponseForgeIntensity.parse("") is ResponseForgeIntensity.LITE

    assert ResponseForgeIntensity.parse(ResponseForgeIntensity.LITE) is ResponseForgeIntensity.LITE





def test_intensity_parse_rejects_unknown() -> None:

    with pytest.raises(ValueError):

        ResponseForgeIntensity.parse("ferocious")





def test_ruleset_off_returns_passthrough() -> None:

    optimizer = ResponseForgeRulesetOptimizer(intensity=ResponseForgeIntensity.OFF)

    request = _request(_user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    assert result.intensity is ResponseForgeIntensity.OFF

    assert result.source == "responseforge-ruleset"

    assert result.notes == ("responseforge off",)

    assert [m.content for m in result.request.messages] == ["hi"]





def test_ruleset_lite_appends_guidance_when_no_system_message() -> None:

    optimizer = ResponseForgeRulesetOptimizer(intensity=ResponseForgeIntensity.LITE)

    request = _request(_user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    assert result.intensity is ResponseForgeIntensity.LITE

    assert len(result.request.messages) == 2

    first = result.request.messages[0]

    assert first.role is Role.SYSTEM

    assert "CAVEMAN (lite)" in first.content

    assert "filler" in first.content





def test_ruleset_full_includes_rules() -> None:

    optimizer = ResponseForgeRulesetOptimizer(intensity=ResponseForgeIntensity.FULL)

    request = _request(_user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    system = result.request.messages[0].content

    assert "CAVEMAN (full)" in system

    assert "[subject] [action] [reason]" in system

    assert "fragments" in system

    assert any("responseforge full mode" in n for n in result.notes)





def test_ruleset_ultra_compresses() -> None:

    optimizer = ResponseForgeRulesetOptimizer(intensity=ResponseForgeIntensity.ULTRA)

    request = _request(_user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    system = result.request.messages[0].content

    assert "CAVEMAN (ultra)" in system

    assert "communication compression" in system

    assert any("responseforge ultra" in n for n in result.notes)





def test_ruleset_wenyan_uses_classical_chinese() -> None:

    optimizer = ResponseForgeRulesetOptimizer(intensity=ResponseForgeIntensity.WENYAN)

    request = _request(_user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    system = result.request.messages[0].content

    assert "CAVEMAN (wenyan)" in system

    assert "Classical Chinese" in system

    assert any("responseforge wenyan" in n for n in result.notes)





def test_ruleset_prepends_to_existing_system_message() -> None:

    optimizer = ResponseForgeRulesetOptimizer(intensity=ResponseForgeIntensity.FULL)

    request = _request(_system("You are a Python assistant."), _user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    assert len(result.request.messages) == 2

    system = result.request.messages[0].content

    assert "CAVEMAN (full)" in system

    assert "You are a Python assistant." in system

    assert system.index("CAVEMAN (full)") < system.index("You are a Python assistant.")





def test_ruleset_replaces_empty_system_message() -> None:

    optimizer = ResponseForgeRulesetOptimizer(intensity=ResponseForgeIntensity.LITE)

    request = _request(_system(""), _user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    system = result.request.messages[0].content

    assert "CAVEMAN (lite)" in system





def test_ruleset_passthrough_when_no_user_message() -> None:

    optimizer = ResponseForgeRulesetOptimizer(intensity=ResponseForgeIntensity.FULL)

    request = _request(_system("hello"))

    result = asyncio.run(optimizer.optimize_chat(request))

    assert result.notes == ("no user message; responseforge passthrough",)

    assert [m.content for m in result.request.messages] == ["hello"]





def test_ruleset_does_not_mutate_input_request() -> None:

    optimizer = ResponseForgeRulesetOptimizer(intensity=ResponseForgeIntensity.FULL)

    request = _request(_user("hi"))

    snapshot_messages = list(request.messages)

    asyncio.run(optimizer.optimize_chat(request))

    assert list(request.messages) == snapshot_messages





def test_composite_off_short_circuits() -> None:

    composite = ResponseForgeCompositeOptimizer(

        intensity=ResponseForgeIntensity.OFF,

        ruleset=ResponseForgeRulesetOptimizer(),

    )

    request = _request(_user("hi"))

    result = asyncio.run(composite.optimize_chat(request))

    assert result.intensity is ResponseForgeIntensity.OFF

    assert result.source == "responseforge-passthrough"





def test_composite_uses_external_when_available() -> None:

    class _External(ResponseForgePromptOptimizer):

        name = "ext-responseforge"



        async def is_available(self) -> bool:

            return True



        async def optimize_chat(self, request):

            return OptimizedRequest(

                request=request,

                notes=("from external responseforge",),

                intensity=ResponseForgeIntensity.LITE,

                source="responseforge-external",

            )



    composite = ResponseForgeCompositeOptimizer(

        intensity=ResponseForgeIntensity.LITE,

        ruleset=ResponseForgeRulesetOptimizer(),

        external=_External(),

    )

    request = _request(_user("hi"))

    result = asyncio.run(composite.optimize_chat(request))

    assert result.source == "responseforge-external"

    assert "from external responseforge" in result.notes





def test_composite_falls_back_to_ruleset_when_external_unavailable() -> None:

    class _External(ResponseForgePromptOptimizer):

        name = "ext-responseforge"



        async def is_available(self) -> bool:

            return False



        async def optimize_chat(self, request):

            raise AssertionError("should not be called")



    composite = ResponseForgeCompositeOptimizer(

        intensity=ResponseForgeIntensity.FULL,

        ruleset=ResponseForgeRulesetOptimizer(),

        external=_External(),

    )

    request = _request(_user("hi"))

    result = asyncio.run(composite.optimize_chat(request))

    assert result.source == "responseforge-ruleset"

    assert "CAVEMAN (full)" in result.request.messages[0].content





def test_composite_no_ruleset_no_external_returns_passthrough() -> None:

    composite = ResponseForgeCompositeOptimizer(intensity=ResponseForgeIntensity.LITE)

    request = _request(_user("hi"))

    result = asyncio.run(composite.optimize_chat(request))

    assert result.source == "responseforge-passthrough"

    assert "no responseforge ruleset registered" in result.notes

