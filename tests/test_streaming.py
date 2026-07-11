"""Unit tests for the Streaming Framework (Phase 4)."""



from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.runtime_core.context import RuntimeContext
from forgecli.runtime_core.request import AIRequest
from forgecli.streaming.events import StreamChunk, StreamEnd, StreamEvent, StreamStart
from forgecli.streaming.middleware import StreamingMiddleware


def make_test_request(stream: bool = True) -> AIRequest:

    return AIRequest(

        request_id="req-123",

        provider_name="openai",

        model_name="gpt-4o",

        session_id="session-123",

        prompt="hello stream",

        messages=[],

        stream=stream,

    )





async def dummy_provider_stream() -> AsyncIterator[StreamEvent]:

    """Simulates a provider returning a token stream."""

    yield StreamStart(response_id="resp-req-123")

    yield StreamChunk(text="Hello ")

    yield StreamChunk(text="Stream")

    yield StreamChunk(text="!")

    yield StreamEnd(finish_reason="stop", metrics={"usage": 3})





@pytest.mark.asyncio

async def test_streaming_middleware() -> None:

    middleware = StreamingMiddleware()

    assert middleware.priority == 300



    req_ctx = RequestContext(

        ai_request=make_test_request(stream=True),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-123",

    )



    async def mock_provider_call(req: RequestContext) -> ResponseContext:

        resp = ResponseContext(

            timing_ms=10.0,

            execution_id=req.execution_id,

        )

        resp.stream_iterator = dummy_provider_stream()

        return resp



    resp_ctx = await middleware(req_ctx, mock_provider_call)





    assert resp_ctx.stream_iterator is not None

    assert resp_ctx.ai_response is None





    events = [event async for event in resp_ctx.stream_iterator]



    assert len(events) == 5

    assert isinstance(events[0], StreamStart)

    assert events[1].text == "Hello "

    assert events[2].text == "Stream"

    assert events[3].text == "!"

    assert isinstance(events[4], StreamEnd)





    assert resp_ctx.ai_response is not None

    assert resp_ctx.ai_response.content == "Hello Stream!"

    assert resp_ctx.ai_response.finish_reason == "stop"





@pytest.mark.asyncio

async def test_streaming_middleware_no_stream() -> None:

    middleware = StreamingMiddleware()



    req_ctx = RequestContext(

        ai_request=make_test_request(stream=False),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-123",

    )



    async def mock_provider_call(req: RequestContext) -> ResponseContext:



        from forgecli.runtime_core.response import AIResponse

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-123",

                request_id="req-123",

                content="Non-streaming response",

                finish_reason="stop",

                latency_ms=1.0,

            ),

            execution_id=req.execution_id,

        )



    resp_ctx = await middleware(req_ctx, mock_provider_call)





    assert resp_ctx.stream_iterator is None

    assert resp_ctx.ai_response is not None

    assert resp_ctx.ai_response.content == "Non-streaming response"

