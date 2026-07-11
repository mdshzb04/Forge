"""Unit tests for Model Registry and Capability Negotiation (Phase 1)."""



from __future__ import annotations

from pathlib import Path

import pytest

from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.negotiator.middleware import CapabilityNegotiationMiddleware
from forgecli.negotiator.negotiator import CapabilityNegotiator
from forgecli.providers.provider_capabilities import Capability
from forgecli.registry.model_registry import ModelProfile, ModelRegistry
from forgecli.runtime_core.context import RuntimeContext
from forgecli.runtime_core.errors import ConfigurationError
from forgecli.runtime_core.request import AIRequest
from forgecli.runtime_core.response import AIResponse


def make_test_request(model_name: str = "gpt-4o", stream: bool = True) -> AIRequest:

    return AIRequest(

        request_id="req-123",

        provider_name="openai",

        model_name=model_name,

        session_id="session-123",

        prompt="test prompt",

        stream=stream,

    )





def test_model_registry_crud() -> None:

    registry = ModelRegistry()





    assert "gpt-4o" in registry.list_models()

    assert "claude-3-5-sonnet" in registry.list_models()





    custom = ModelProfile(

        name="custom-model",

        context_window=32000,

        max_output_tokens=2048,

        capabilities={Capability.STREAMING, Capability.VISION},

    )

    registry.register_profile(custom)

    assert "custom-model" in registry.list_models()

    assert registry.resolve_model("custom-model") == custom





    registry.register_alias("custom-alias", "custom-model")

    assert registry.resolve_model("custom-alias") == custom





    assert registry.resolve_model("gpt-4") is not None





    registry.unregister_profile("custom-model")

    assert "custom-model" not in registry.list_models()

    assert registry.resolve_model("custom-alias") is None





def test_negotiator_compatible() -> None:

    registry = ModelRegistry()

    negotiator = CapabilityNegotiator(registry)





    res = negotiator.negotiate(

        model_name="gpt-4o",

        required_capabilities={Capability.VISION},

        optional_capabilities={Capability.STREAMING},

    )

    assert res.is_compatible is True

    assert Capability.VISION in res.supported

    assert Capability.STREAMING in res.supported

    assert res.adjusted_features.get("streaming") is True





def test_negotiator_incompatible_fallback() -> None:

    registry = ModelRegistry()

    negotiator = CapabilityNegotiator(registry)





    res = negotiator.negotiate(

        model_name="llama-3.1-70b-versatile",

        required_capabilities={Capability.VISION},

    )

    assert res.is_compatible is False

    assert Capability.VISION in res.unsupported





    alt = negotiator.find_compatible_model({Capability.VISION}, preferred_family="gpt")

    assert alt == "gpt-4o"





    alt_none = negotiator.find_compatible_model({Capability.AUDIO}, preferred_family="gpt")

    assert alt_none is None





def test_negotiator_unresolved_model() -> None:

    registry = ModelRegistry()

    negotiator = CapabilityNegotiator(registry)

    with pytest.raises(ConfigurationError):

        negotiator.negotiate("non-existent", {Capability.STREAMING})





@pytest.mark.asyncio

async def test_negotiation_middleware_success() -> None:

    registry = ModelRegistry()

    negotiator = CapabilityNegotiator(registry)

    middleware = CapabilityNegotiationMiddleware(negotiator)



    assert middleware.priority == 750



    ai_req = make_test_request(model_name="gpt-4o", stream=True)

    runtime_ctx = RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r"))

    req_ctx = RequestContext(

        ai_request=ai_req,

        runtime_context=runtime_ctx,

        execution_id="exec-123",

        metadata={

            "required_capabilities": ["vision", Capability.JSON_MODE, "invalid-cap-req"],

            "optional_capabilities": ["streaming", Capability.REASONING, "invalid-cap-opt"],

        },

    )



    async def call_next(req: RequestContext) -> ResponseContext:

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-123",

                request_id=req.ai_request.request_id,

                content="success",

                finish_reason="stop",

                latency_ms=10.0,

            ),

            execution_id=req.execution_id,

        )



    resp = await middleware(req_ctx, call_next)

    assert resp.ai_response.content == "success"

    assert req_ctx.ai_request.stream is True

    assert "negotiation_result" in req_ctx.metadata

    assert req_ctx.metadata["negotiation_result"].is_compatible is True





@pytest.mark.asyncio

async def test_negotiation_middleware_fallback() -> None:

    registry = ModelRegistry()

    negotiator = CapabilityNegotiator(registry)

    middleware = CapabilityNegotiationMiddleware(negotiator)





    ai_req = make_test_request(model_name="llama-3.1-70b-versatile", stream=True)

    runtime_ctx = RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r"))

    req_ctx = RequestContext(

        ai_request=ai_req,

        runtime_context=runtime_ctx,

        execution_id="exec-123",

        metadata={"required_capabilities": [Capability.VISION]},

    )



    async def call_next(req: RequestContext) -> ResponseContext:

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-123",

                request_id=req.ai_request.request_id,

                content="success",

                finish_reason="stop",

                latency_ms=10.0,

            ),

            execution_id=req.execution_id,

        )



    await middleware(req_ctx, call_next)

    assert req_ctx.ai_request.model_name == "gpt-4o"

    assert "negotiation_result" in req_ctx.metadata





@pytest.mark.asyncio

async def test_negotiation_middleware_unsupported_error() -> None:

    registry = ModelRegistry()

    negotiator = CapabilityNegotiator(registry)

    middleware = CapabilityNegotiationMiddleware(negotiator)







    registry.unregister_profile("gemini-1.5-pro")



    ai_req = make_test_request(model_name="gpt-4o", stream=True)

    runtime_ctx = RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r"))

    req_ctx = RequestContext(

        ai_request=ai_req,

        runtime_context=runtime_ctx,

        execution_id="exec-123",

        metadata={"required_capabilities": [Capability.AUDIO]},

    )



    async def call_next(req: RequestContext) -> ResponseContext:

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-123",

                request_id=req.ai_request.request_id,

                content="success",

                finish_reason="stop",

                latency_ms=10.0,

            ),

            execution_id=req.execution_id,

        )



    with pytest.raises(ConfigurationError) as exc:

        await middleware(req_ctx, call_next)

    assert "does not support required capabilities" in str(exc.value)

