"""Unit tests for Phase 4 (Provider Runtime) of the Forge runtime."""



from __future__ import annotations

from pathlib import Path

import pytest

from forgecli.middleware.context import RequestContext
from forgecli.providers.base import (
    AnthropicProvider,
    GeminiProvider,
    LMStudioProvider,
    OllamaProvider,
    OpenAIProvider,
    Provider,
)
from forgecli.providers.exceptions import (
    ProviderExecutionError,
    ProviderNotFoundError,
    ProviderRegistrationError,
)
from forgecli.providers.health import ProviderHealth, ProviderHealthState
from forgecli.providers.provider_capabilities import Capability, ProviderCapabilities
from forgecli.providers.provider_context import ProviderContext
from forgecli.providers.provider_events import (
    ProviderEvent,
    ProviderHealthChanged,
    ProviderRegistered,
    ProviderStarted,
    ProviderStopped,
)
from forgecli.providers.provider_factory import ProviderFactory
from forgecli.providers.provider_manager import ProviderManager
from forgecli.providers.provider_metadata import ProviderMetadata
from forgecli.providers.provider_registry import ProviderRegistry
from forgecli.providers.provider_router import ProviderRouter
from forgecli.runtime_core.container import Container
from forgecli.runtime_core.context import CancellationToken, RuntimeContext
from forgecli.runtime_core.events import EventBus
from forgecli.runtime_core.request import AIRequest


def make_test_request() -> AIRequest:

    """Helper to construct a valid test AIRequest."""

    return AIRequest(

        request_id="req-p4",

        provider_name="openai",

        model_name="gpt-4o",

        session_id="session-p4",

        prompt="test prompt",

    )





def make_request_context() -> RequestContext:

    """Helper to construct a valid RequestContext."""

    return RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(

            session_id="session-p4",

            workspace=Path("workspace-p4"),

            repository_root=Path("repo-p4"),

        ),

        execution_id="exec-p4",

    )





def test_capabilities_and_metadata() -> None:

    """Verify capabilities system and metadata models compile and function correctly."""

    caps = ProviderCapabilities()

    assert caps.supports(Capability.VISION) is False



    caps.add(Capability.VISION)

    assert caps.supports(Capability.VISION) is True



    caps.remove(Capability.VISION)

    assert caps.supports(Capability.VISION) is False



    meta = ProviderMetadata(

        name="test-meta",

        version="2.0.0",

        default_model="m-1",

        supported_models=["m-1", "m-2"],

        context_windows={"m-1": 1000, "m-2": 2000},

    )

    assert meta.name == "test-meta"

    assert meta.context_windows["m-2"] == 2000





def test_health_monitoring_states() -> None:

    """Verify provider health structure holds fields correctly."""

    health = ProviderHealth(

        state=ProviderHealthState.DEGRADED,

        details="high latency rates",

    )

    assert health.state == ProviderHealthState.DEGRADED

    assert health.details == "high latency rates"

    assert health.last_checked is not None





@pytest.mark.asyncio

async def test_provider_registry_lifecycle() -> None:

    """Verify dynamic provider registration, unregistration, retrieval, and listings."""

    registry = ProviderRegistry()

    assert len(registry.list()) == 0



    prov = OpenAIProvider()

    registry.register("openai", prov)

    assert registry.exists("openai") is True

    assert registry.exists("OpenAI") is True

    assert registry.resolve("openai") is prov





    with pytest.raises(ProviderRegistrationError):

        registry.register("openai", OpenAIProvider())





    with pytest.raises(ProviderRegistrationError):

        registry.register("", OpenAIProvider())





    assert registry.list() == ["openai"]





    meta_dict = registry.metadata()

    assert "openai" in meta_dict

    assert meta_dict["openai"].default_model == "gpt-4o"





    await registry.reload()





    health_dict = await registry.health()

    assert "openai" in health_dict

    assert health_dict["openai"].state == ProviderHealthState.HEALTHY





    registry.unregister("openai")

    assert registry.exists("openai") is False





    with pytest.raises(ProviderNotFoundError):

        registry.resolve("openai")



    with pytest.raises(ProviderNotFoundError):

        registry.unregister("openai")





def test_provider_factory_resolution() -> None:

    """Verify factory integrates with DI container to resolve driver instances."""

    container = Container()

    factory = ProviderFactory(container)





    openai_driver = factory.create_by_name("openai")

    assert isinstance(openai_driver, OpenAIProvider)





    openai_driver_2 = factory.create_by_name("openai")

    assert openai_driver_2 is openai_driver





    anthropic_driver = factory.create(AnthropicProvider)

    assert isinstance(anthropic_driver, AnthropicProvider)





    with pytest.raises(ProviderNotFoundError):

        factory.create_by_name("unknown-provider")





def test_provider_context_packing() -> None:

    """Verify ProviderContext structures packing parameters correctly."""

    prov = OpenAIProvider()

    req_ctx = make_request_context()

    cancel_token = CancellationToken()



    ctx = ProviderContext(

        provider=prov,

        model="gpt-4o",

        workspace=Path("test-workspace"),

        request_context=req_ctx,

        cancellation_token=cancel_token,

        configuration={"key": "val"},

    )



    assert ctx.model == "gpt-4o"

    assert ctx.workspace == Path("test-workspace")

    assert ctx.request_context is req_ctx

    assert ctx.cancellation_token is cancel_token

    assert ctx.configuration == {"key": "val"}





@pytest.mark.asyncio

async def test_provider_router_resolution_and_fallbacks() -> None:

    """Verify route queries, model alias lookups, prefix mappings, and fallback resolution."""

    registry = ProviderRegistry()

    openai = OpenAIProvider()

    anthropic = AnthropicProvider()

    gemini = GeminiProvider()



    registry.register("openai", openai)

    registry.register("anthropic", anthropic)

    registry.register("gemini", gemini)



    router = ProviderRouter(

        registry=registry,

        default_provider_name="openai",

        default_model_name="gpt-4o",

    )





    router.register_alias("smart-model", "anthropic", "claude-3-5-sonnet")





    p, m = router.resolve_provider_and_model(None)

    assert p is openai

    assert m == "gpt-4o"





    p, m = router.resolve_provider_and_model("smart-model")

    assert p is anthropic

    assert m == "claude-3-5-sonnet"





    p, m = router.resolve_provider_and_model("gemini:gemini-1.5-pro")

    assert p is gemini

    assert m == "gemini-1.5-pro"





    p, m = router.resolve_provider_and_model("claude-3-haiku")

    assert p is anthropic

    assert m == "claude-3-haiku"





    p, m = router.resolve_provider_and_model("random-model-query")

    assert p is openai

    assert m == "random-model-query"





    router.register_fallback("openai", ["anthropic", "gemini"])





    routed_p, routed_m = await router.route_request("gpt-4o")

    assert routed_p is openai

    assert routed_m == "gpt-4o"





    setattr(openai, "_health_state", ProviderHealth(state=ProviderHealthState.UNAVAILABLE))





    routed_p, routed_m = await router.route_request("gpt-4o")

    assert routed_p is anthropic



    assert routed_m == "claude-3-5-sonnet"





    setattr(anthropic, "_health_state", ProviderHealth(state=ProviderHealthState.UNAVAILABLE))





    routed_p, routed_m = await router.route_request("gpt-4o")

    assert routed_p is gemini

    assert routed_m == "gemini-1.5-pro"





    setattr(gemini, "_health_state", ProviderHealth(state=ProviderHealthState.UNAVAILABLE))





    with pytest.raises(ProviderExecutionError):

        await router.route_request("gpt-4o")





    setattr(openai, "_health_state", ProviderHealth(state=ProviderHealthState.HEALTHY))

    setattr(anthropic, "_health_state", ProviderHealth(state=ProviderHealthState.HEALTHY))

    setattr(gemini, "_health_state", ProviderHealth(state=ProviderHealthState.HEALTHY))





@pytest.mark.asyncio

async def test_provider_manager_lifecycles_and_events() -> None:

    """Verify manager boot sequence, dynamic status triggers, and event loop listeners."""

    registry = ProviderRegistry()

    event_bus = EventBus()

    manager = ProviderManager(registry, event_bus)



    events_received: list[ProviderEvent] = []



    def on_event(event: ProviderEvent) -> None:

        events_received.append(event)





    event_bus.subscribe(ProviderRegistered, on_event)

    event_bus.subscribe(ProviderStarted, on_event)

    event_bus.subscribe(ProviderStopped, on_event)

    event_bus.subscribe(ProviderHealthChanged, on_event)





    prov = OpenAIProvider()

    await manager.register_provider("openai", prov)

    assert len(events_received) == 1

    assert isinstance(events_received[0], ProviderRegistered)

    assert events_received[0].provider_name == "openai"





    await manager.initialize_all()

    assert len(events_received) == 2

    assert isinstance(events_received[1], ProviderStarted)





    await manager.check_health()

    assert len(events_received) == 3

    assert isinstance(events_received[2], ProviderHealthChanged)

    assert events_received[2].old_state == ProviderHealthState.UNKNOWN

    assert events_received[2].new_state == ProviderHealthState.HEALTHY





    setattr(prov, "_health_state", ProviderHealth(state=ProviderHealthState.DEGRADED, details="warning"))

    await manager.check_health()

    assert len(events_received) == 4

    assert isinstance(events_received[3], ProviderHealthChanged)

    assert events_received[3].old_state == ProviderHealthState.HEALTHY

    assert events_received[3].new_state == ProviderHealthState.DEGRADED





    await manager.unregister_provider("openai")

    assert len(events_received) == 5

    assert isinstance(events_received[4], ProviderStopped)





    setattr(prov, "_health_state", ProviderHealth(state=ProviderHealthState.HEALTHY))

    event_bus.shutdown()





@pytest.mark.asyncio

async def test_placeholder_execution() -> None:

    """Verify default placeholder send and stream payloads compile and execute."""

    openai = OpenAIProvider()

    await openai.initialize()



    req_ctx = make_request_context()

    ctx = ProviderContext(

        provider=openai,

        model="gpt-4o",

        workspace=Path("workspace-p4"),

        request_context=req_ctx,

    )





    resp = await openai.send(ctx)

    assert resp.response_id.startswith("resp-openai-")

    assert resp.content == "Mock response from openai using gpt-4o"

    assert resp.finish_reason == "stop"

    assert resp.latency_ms == 10.0





    stream_response = []

    async for chunk in openai.stream(ctx):

        stream_response.append(chunk)



    assert len(stream_response) == 1

    assert stream_response[0].content == "Mock stream chunk from openai using gpt-4o"





    await openai.cancel(resp.request_id)





    assert openai.supports_tools() is True

    assert openai.supports_streaming() is True

    assert openai.supports_images() is True

    assert openai.supports_reasoning() is True

    assert openai.supports_json() is True

    assert openai.supports_embeddings() is True

    assert openai.supports_mcp() is True





    assert openai.estimate_context_window("gpt-4o") == 128000

    assert openai.estimate_context_window("unknown-model") == 4096





    ollama = OllamaProvider()

    assert ollama.supports_tools() is True

    assert ollama.supports_images() is False

    assert ollama.supports_embeddings() is True



    lmstudio = LMStudioProvider()

    assert lmstudio.supports_tools() is False

    assert lmstudio.supports_streaming() is True



    await openai.shutdown()





@pytest.mark.asyncio

async def test_uncovered_paths_and_all_placeholders() -> None:

    """Verify all remaining placeholder constructors and error recovery execution paths."""

    from forgecli.providers.base import (
        AnthropicProvider,
        DeepSeekProvider,
        GeminiProvider,
        GLMProvider,
        GroqProvider,
        KimiProvider,
        LMStudioProvider,
        OllamaProvider,
        OpenAIProvider,
        OpenRouterProvider,
        QwenProvider,
    )



    placeholders = [

        OpenAIProvider(),

        AnthropicProvider(),

        GeminiProvider(),

        OpenRouterProvider(),

        GroqProvider(),

        DeepSeekProvider(),

        GLMProvider(),

        QwenProvider(),

        KimiProvider(),

        OllamaProvider(),

        LMStudioProvider(),

    ]



    for provider in placeholders:

        assert provider.metadata().name is not None

        assert provider.metadata().version is not None

        assert provider.metadata().default_model is not None

        assert isinstance(provider.estimate_context_window("default"), int)

        assert provider.supports_streaming() is not None

        assert provider.supports_reasoning() is not None

        assert provider.supports_images() is not None

        assert provider.supports_json() is not None





    container = Container()



    container.register(OpenAIProvider, OpenAIProvider)

    factory = ProviderFactory(container)

    assert isinstance(factory.create_by_name("openai"), OpenAIProvider)





    with pytest.raises(ProviderNotFoundError):

        factory.create(Provider)





    class BrokenClass:

        def __init__(self) -> None:

            raise ValueError("Intentional error")

    with pytest.raises(ProviderNotFoundError):

        factory.create(BrokenClass)





    registry = ProviderRegistry()

    router = ProviderRouter(registry)

    with pytest.raises(ProviderNotFoundError):

        await router.get_healthy_provider("nonexistent-prov")





    event_bus = EventBus()

    manager = ProviderManager(registry, event_bus)

    prov = OpenAIProvider()

    await manager.register_provider("openai", prov)

    await manager.initialize_all()

    await manager.shutdown_all()

    event_bus.shutdown()



