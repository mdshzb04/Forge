"""Unit tests for the Resilience Framework (Phase 4)."""



from __future__ import annotations

import time
from pathlib import Path

import pytest

from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.resilience.circuit_breaker import CircuitBreaker, CircuitState
from forgecli.resilience.exceptions import CircuitOpenError, MaxRetriesExceededError
from forgecli.resilience.middleware import ResilienceMiddleware
from forgecli.resilience.retry import RetryPolicy
from forgecli.runtime_core.context import RuntimeContext
from forgecli.runtime_core.request import AIRequest
from forgecli.runtime_core.response import AIResponse


def make_test_request() -> AIRequest:

    return AIRequest(

        request_id="req-123",

        provider_name="openai",

        model_name="gpt-4o",

        session_id="session-123",

        prompt="hello",

        messages=[],

    )





@pytest.mark.asyncio

async def test_retry_policy() -> None:

    policy = RetryPolicy(service="test", max_attempts=3, base_delay=0.01, max_delay=0.1)



    attempts = 0

    async def failing_call() -> str:

        nonlocal attempts

        attempts += 1

        if attempts < 3:

            raise ValueError("fail")

        return "success"



    result = await policy.execute_async(failing_call)

    assert result == "success"

    assert attempts == 3





    attempts2 = 0

    async def always_fail() -> str:

        nonlocal attempts2

        attempts2 += 1

        raise ValueError("fail forever")



    with pytest.raises(MaxRetriesExceededError) as exc:

        await policy.execute_async(always_fail)



    assert exc.value.attempts == 3

    assert "fail forever" in str(exc.value.last_error)





@pytest.mark.asyncio

async def test_circuit_breaker() -> None:

    breaker = CircuitBreaker(service="test", failure_threshold=2, recovery_timeout=0.1)

    assert breaker.state == CircuitState.CLOSED



    async def always_fail() -> str:

        raise ValueError("fail")



    async def always_succeed() -> str:

        return "success"





    with pytest.raises(ValueError):

        await breaker.execute_async(always_fail)

    assert breaker.state == CircuitState.CLOSED





    with pytest.raises(ValueError):

        await breaker.execute_async(always_fail)

    assert breaker.state == CircuitState.OPEN





    with pytest.raises(CircuitOpenError):

        await breaker.execute_async(always_succeed)





    time.sleep(0.15)

    assert breaker.state == CircuitState.HALF_OPEN





    result = await breaker.execute_async(always_succeed)

    assert result == "success"

    assert breaker.state == CircuitState.CLOSED





@pytest.mark.asyncio

async def test_resilience_middleware() -> None:

    breaker = CircuitBreaker(service="test", failure_threshold=2, recovery_timeout=0.1)



    retry = RetryPolicy(service="test", max_attempts=2, base_delay=0.01)



    middleware = ResilienceMiddleware(service_name="test", circuit_breaker=breaker, retry_policy=retry)

    assert middleware.priority == 250



    req_ctx = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-123",

    )



    call_count = 0

    async def flaky_call(req: RequestContext) -> ResponseContext:

        nonlocal call_count

        call_count += 1

        if call_count == 1:

            raise ValueError("flaky fail")

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-123",

                request_id=req.ai_request.request_id,

                content="success",

                finish_reason="stop",

                latency_ms=1.0,

            ),

            execution_id=req.execution_id,

        )



    resp = await middleware(req_ctx, flaky_call)

    assert resp.ai_response.content == "success"

    assert call_count == 2

    assert breaker.state == CircuitState.CLOSED

