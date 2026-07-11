"""Tests for the Ponytail ruleset prompt optimizer."""



from __future__ import annotations

import asyncio

import pytest

from forgecli.optimizer.ponytail import (
    CompositeOptimizer,
    Intensity,
    OptimizedRequest,
    PonytailRulesetOptimizer,
    PromptOptimizer,
)
from forgecli.providers.base import ChatMessage, ChatRequest, Role


def _request(*messages: ChatMessage) -> ChatRequest:

    return ChatRequest(model="test-model", messages=list(messages))





def _user(text: str) -> ChatMessage:

    return ChatMessage(role=Role.USER, content=text)





def _system(text: str) -> ChatMessage:

    return ChatMessage(role=Role.SYSTEM, content=text)





def test_intensity_parse_accepts_known_values() -> None:

    assert Intensity.parse("off") is Intensity.OFF

    assert Intensity.parse("LITE") is Intensity.LITE

    assert Intensity.parse("Full") is Intensity.FULL

    assert Intensity.parse("ULTRA") is Intensity.ULTRA





def test_intensity_parse_defaults_to_lite() -> None:

    assert Intensity.parse(None) is Intensity.LITE

    assert Intensity.parse("") is Intensity.LITE

    assert Intensity.parse(Intensity.LITE) is Intensity.LITE





def test_intensity_parse_rejects_unknown() -> None:

    with pytest.raises(ValueError):

        Intensity.parse("ferocious")





def test_ruleset_off_returns_passthrough() -> None:

    optimizer = PonytailRulesetOptimizer(intensity=Intensity.OFF)

    request = _request(_user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    assert result.intensity is Intensity.OFF

    assert result.source == "ruleset"

    assert result.notes == ("ponytail off",)

    assert [m.content for m in result.request.messages] == ["hi"]





def test_ruleset_lite_appends_guidance_when_no_system_message() -> None:

    optimizer = PonytailRulesetOptimizer(intensity=Intensity.LITE)

    request = _request(_user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    assert result.intensity is Intensity.LITE

    assert len(result.request.messages) == 2

    first = result.request.messages[0]

    assert first.role is Role.SYSTEM

    assert "Ponytail (lite)" in first.content

    assert "lazier correct alternative" in first.content





def test_ruleset_full_includes_ladder() -> None:

    optimizer = PonytailRulesetOptimizer(intensity=Intensity.FULL)

    request = _request(_user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    system = result.request.messages[0].content

    assert "Ponytail (full)" in system

    assert "Ponytail ladder" in system

    assert "Speculative need" in system

    assert "ladder enforced" in result.notes





def test_ruleset_ultra_challenges_requirement() -> None:

    optimizer = PonytailRulesetOptimizer(intensity=Intensity.ULTRA)

    request = _request(_user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    system = result.request.messages[0].content

    assert "Ponytail (ultra)" in system

    assert "YAGNI extremist" in system

    assert "yagni extremist mode" in result.notes





def test_ruleset_prepends_to_existing_system_message() -> None:

    optimizer = PonytailRulesetOptimizer(intensity=Intensity.FULL)

    request = _request(_system("You are a Python assistant."), _user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    assert len(result.request.messages) == 2

    system = result.request.messages[0].content

    assert "Ponytail (full)" in system

    assert "You are a Python assistant." in system



    assert system.index("Ponytail (full)") < system.index("You are a Python assistant.")





def test_ruleset_replaces_empty_system_message() -> None:

    optimizer = PonytailRulesetOptimizer(intensity=Intensity.LITE)

    request = _request(_system(""), _user("hi"))

    result = asyncio.run(optimizer.optimize_chat(request))

    system = result.request.messages[0].content

    assert "Ponytail (lite)" in system





def test_ruleset_passthrough_when_no_user_message() -> None:

    optimizer = PonytailRulesetOptimizer(intensity=Intensity.FULL)

    request = _request(_system("hello"))

    result = asyncio.run(optimizer.optimize_chat(request))

    assert result.notes == ("no user message; passthrough",)

    assert [m.content for m in result.request.messages] == ["hello"]





def test_ruleset_does_not_mutate_input_request() -> None:

    optimizer = PonytailRulesetOptimizer(intensity=Intensity.FULL)

    request = _request(_user("hi"))

    snapshot_messages = list(request.messages)

    asyncio.run(optimizer.optimize_chat(request))

    assert list(request.messages) == snapshot_messages





def test_composite_off_short_circuits() -> None:

    composite = CompositeOptimizer(

        intensity=Intensity.OFF,

        ruleset=PonytailRulesetOptimizer(),

    )

    request = _request(_user("hi"))

    result = asyncio.run(composite.optimize_chat(request))

    assert result.intensity is Intensity.OFF

    assert result.source == "passthrough"





def test_composite_uses_external_when_available() -> None:

    class _External(PromptOptimizer):

        name = "ext"



        async def is_available(self) -> bool:

            return True



        async def optimize_chat(self, request):

            return OptimizedRequest(

                request=request,

                notes=("from external",),

                intensity=Intensity.LITE,

                source="external",

            )



    composite = CompositeOptimizer(

        intensity=Intensity.LITE,

        ruleset=PonytailRulesetOptimizer(),

        external=_External(),

    )

    request = _request(_user("hi"))

    result = asyncio.run(composite.optimize_chat(request))

    assert result.source == "external"

    assert result.notes == ("from external",)





def test_composite_falls_back_to_ruleset_when_external_unavailable() -> None:

    class _External(PromptOptimizer):

        name = "ext"



        async def is_available(self) -> bool:

            return False



        async def optimize_chat(self, request):

            raise AssertionError("should not be called")



    composite = CompositeOptimizer(

        intensity=Intensity.FULL,

        ruleset=PonytailRulesetOptimizer(),

        external=_External(),

    )

    request = _request(_user("hi"))

    result = asyncio.run(composite.optimize_chat(request))

    assert result.source == "ruleset"

    assert "Ponytail (full)" in result.request.messages[0].content





def test_composite_no_ruleset_no_external_returns_passthrough() -> None:

    composite = CompositeOptimizer(intensity=Intensity.LITE)

    request = _request(_user("hi"))

    result = asyncio.run(composite.optimize_chat(request))

    assert result.source == "passthrough"

    assert "no ruleset registered" in result.notes

