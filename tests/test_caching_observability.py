"""Unit tests for Caching Framework and Observability Framework (Phase 4)."""



from __future__ import annotations

import time
from pathlib import Path

import pytest

from forgecli.memory.cache import Cache
from forgecli.memory.caching_middleware import CachingMiddleware
from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.observability.health import HealthMonitor, HealthStatus
from forgecli.observability.metrics import MetricsRegistry
from forgecli.observability.middleware import TelemetryMiddleware
from forgecli.observability.tracing import Tracer
from forgecli.runtime_core.context import RuntimeContext
from forgecli.runtime_core.request import AIRequest, FileContext
from forgecli.runtime_core.response import AIResponse


def make_test_request(

    prompt: str = "hello cache",

    messages: list[dict[str, str]] | None = None,

    files: list[FileContext] | None = None,

    stream: bool = False,

) -> AIRequest:

    return AIRequest(

        request_id="req-123",

        provider_name="openai",

        model_name="gpt-4o",

        session_id="session-123",

        prompt=prompt,

        messages=messages or [],

        attached_files=files or [],

        stream=stream,

    )





def test_cache_framework() -> None:

    cache: Cache[str, str] = Cache(default_ttl=0.1)





    cache.set("k1", "v1")

    assert cache.get("k1") == "v1"

    assert "k1" in cache

    assert len(cache) == 1





    time.sleep(0.15)

    assert cache.get("k1") is None

    assert "k1" not in cache

    assert len(cache) == 0





    cache.set("k2", "v2")

    cache.delete("k2")

    assert cache.get("k2") is None



    cache.set("k3", "v3")

    cache.set("k4", "v4")

    cache.clear()

    assert len(cache) == 0





@pytest.mark.asyncio

async def test_caching_middleware() -> None:

    cache: Cache[str, AIResponse] = Cache(default_ttl=3600.0)

    middleware = CachingMiddleware(cache=cache)

    assert middleware.priority == 850



    ai_req = make_test_request(prompt="write code")

    req_ctx = RequestContext(

        ai_request=ai_req,

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-1",

    )



    call_count = 0



    async def call_next(req: RequestContext) -> ResponseContext:

        nonlocal call_count

        call_count += 1

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-123",

                request_id=req.ai_request.request_id,

                content="function_hello()",

                finish_reason="stop",

                latency_ms=1.0,

            ),

            execution_id=req.execution_id,

        )





    resp1 = await middleware(req_ctx, call_next)

    assert call_count == 1

    assert req_ctx.metadata.get("cache_hit") is False

    assert resp1.ai_response.content == "function_hello()"





    req_ctx2 = RequestContext(

        ai_request=make_test_request(prompt="write code"),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-2",

    )

    resp2 = await middleware(req_ctx2, call_next)

    assert call_count == 1

    assert req_ctx2.metadata.get("cache_hit") is True

    assert resp2.ai_response.content == "function_hello()"





    req_ctx3 = RequestContext(

        ai_request=make_test_request(prompt="write code", stream=True),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-3",

    )

    await middleware(req_ctx3, call_next)

    assert call_count == 2





def test_metrics_registry() -> None:

    metrics = MetricsRegistry()

    metrics.increment("http_requests", tags={"status": "200"})

    metrics.increment("http_requests", tags={"status": "200"}, amount=2)

    assert metrics.get_counter("http_requests", tags={"status": "200"}) == 3



    metrics.record_value("latency", 50.0)

    metrics.record_value("latency", 150.0)

    hist = metrics.get_histogram("latency")

    assert hist is not None

    assert hist.count == 2

    assert hist.sum == 200.0

    assert hist.min == 50.0

    assert hist.max == 150.0



    dump = metrics.dump_metrics()

    assert "http_requests{status=200}" in dump["counters"]

    assert "latency" in dump["histograms"]





def test_tracing_context() -> None:

    metrics = MetricsRegistry()

    tracer = Tracer(metrics)



    with tracer.span("test_op", tags={"env": "prod"}) as span:

        time.sleep(0.01)

        span.tags["user_id"] = "u1"



    assert span.duration_ms > 5.0

    assert span.trace_id is not None



    assert metrics.get_counter("test_op_calls", tags={"env": "prod", "user_id": "u1"}) == 1

    hist = metrics.get_histogram("test_op_latency_ms", tags={"env": "prod", "user_id": "u1"})

    assert hist is not None

    assert hist.count == 1





    with pytest.raises(ValueError):

        with tracer.span("fail_op", tags={"env": "prod"}) as fail_span:

            raise ValueError("boom")



    assert fail_span.error is not None

    assert metrics.get_counter("fail_op_errors", tags={"env": "prod", "error": "ValueError"}) == 1





@pytest.mark.asyncio

async def test_telemetry_middleware() -> None:

    metrics = MetricsRegistry()

    middleware = TelemetryMiddleware(metrics=metrics)

    assert middleware.priority == 1000



    ai_req = make_test_request(prompt="write code")

    req_ctx = RequestContext(

        ai_request=ai_req,

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-abc",

    )



    async def call_next(req: RequestContext) -> ResponseContext:

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-123",

                request_id=req.ai_request.request_id,

                content="done",

                finish_reason="stop",

                latency_ms=1.0,

            ),

            execution_id=req.execution_id,

        )



    await middleware(req_ctx, call_next)



    dump = metrics.dump_metrics()

    keys = list(dump["counters"].keys())



    assert any("pipeline_execution_calls" in k and "status=success" in k for k in keys)





def test_health_monitor() -> None:

    monitor = HealthMonitor()

    monitor.report(HealthStatus(name="database", status="ok", latency_ms=2.0))

    monitor.report(HealthStatus(name="redis", status="degraded", message="slow connection"))



    overall = monitor.get_overall_health()

    assert overall["status"] == "degraded"

    assert "redis" in overall["degraded_components"]



    monitor.report(HealthStatus(name="provider_api", status="down"))

    overall2 = monitor.get_overall_health()

    assert overall2["status"] == "down"

    assert "provider_api" in overall2["down_components"]

