"""Unit tests for Phase 3 (Pipeline Dispatcher & Middleware) of the Forge runtime."""



from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from forgecli.middleware.base import Middleware
from forgecli.middleware.builder import PipelineBuilder
from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.middleware.decorators import middleware as middleware_decorator
from forgecli.middleware.exceptions import (
    MiddlewareRegistrationError,
    PipelineError,
    ShortCircuitException,
)
from forgecli.middleware.executor import PipelineExecutor
from forgecli.middleware.middleware_manager import MiddlewareManager
from forgecli.middleware.pipeline import MiddlewarePipeline
from forgecli.middleware.registration import (
    get_registered_middleware_types,
    register_middleware_type,
    unregister_middleware_type,
)
from forgecli.runtime_core.context import CancellationToken, RuntimeContext
from forgecli.runtime_core.request import AIRequest
from forgecli.runtime_core.response import AIResponse


def make_test_request() -> AIRequest:

    """Helper to construct a valid test AIRequest."""

    return AIRequest(

        request_id="req-123",

        provider_name="test-provider",

        model_name="test-model",

        session_id="session-123",

        prompt="test prompt",

    )





class TrackingMiddleware(Middleware):

    """Middleware that appends its name to an execution log list."""



    def __init__(self, name: str, priority_val: int = 100) -> None:

        self._name = name

        self._priority = priority_val



    @property

    def priority(self) -> int:

        return self._priority



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        log = request.metadata.setdefault("exec_log", [])

        log.append(f"{self._name}:before")

        response = await call_next(request)

        log.append(f"{self._name}:after")

        return response





class ShortCircuitingMiddleware(Middleware):

    """Middleware that short-circuits execution and returns a pre-packaged response."""



    async def before_request(self, request: RequestContext) -> RequestContext:

        resp = ResponseContext(

            ai_response=AIResponse(

                response_id="resp-short",

                request_id="req-short",

                content="short-circuited",

                finish_reason="stop",

                latency_ms=5.0,

            ),

            telemetry={"short": True},

        )

        raise ShortCircuitException("Short-circuiting request", resp)





class ErrorMiddleware(Middleware):

    """Middleware that raises a RuntimeError during request processing."""



    async def before_request(self, request: RequestContext) -> RequestContext:

        raise RuntimeError("simulated-error")





class RecoveryMiddleware(Middleware):

    """Middleware that catches exceptions and resolves them into a ResponseContext."""



    async def on_exception(self, request: RequestContext, exception: Exception) -> ResponseContext | None:

        if str(exception) == "simulated-error":

            return ResponseContext(

                ai_response=AIResponse(

                    response_id="resp-recovered",

                    request_id="req-recovered",

                    content="recovered",

                    finish_reason="stop",

                    latency_ms=5.0,

                ),

                errors=[str(exception)],

            )

        return None













def test_middleware_registration_system() -> None:

    """Verify global dynamic middleware type registrations and validations."""



    register_middleware_type("tracker", TrackingMiddleware)

    registered = get_registered_middleware_types()

    assert "tracker" in registered

    assert registered["tracker"] is TrackingMiddleware





    with pytest.raises(MiddlewareRegistrationError):

        register_middleware_type("tracker", TrackingMiddleware)





    class NotMiddleware:

        pass



    with pytest.raises(MiddlewareRegistrationError):

        register_middleware_type("invalid", NotMiddleware)  # type: ignore





    unregister_middleware_type("tracker")

    assert "tracker" not in get_registered_middleware_types()





def test_middleware_decorator() -> None:

    """Verify the @middleware decorator auto-registers classes with priorities."""

    @middleware_decorator(priority=888, name="dec-mw")

    class DecoratedMiddleware(Middleware):

        pass



    registered = get_registered_middleware_types()

    assert "dec-mw" in registered

    assert registered["dec-mw"] is DecoratedMiddleware

    assert DecoratedMiddleware().priority == 888





    unregister_middleware_type("dec-mw")





def test_pipeline_composition_and_priorities() -> None:

    """Verify that the pipeline lists and executes middlewares sorted by priority."""

    pipeline = MiddlewarePipeline()

    m_low = TrackingMiddleware("low", priority_val=10)

    m_high = TrackingMiddleware("high", priority_val=200)

    m_mid = TrackingMiddleware("mid", priority_val=100)





    pipeline.add(m_low)

    pipeline.add(m_mid)

    pipeline.add(m_high)



    sorted_list = pipeline.list()

    assert sorted_list == [m_high, m_mid, m_low]





    m_extra = TrackingMiddleware("extra", priority_val=150)

    pipeline.insert(0, m_extra)

    assert m_extra in pipeline.list()





    pipeline.remove(m_extra)

    assert m_extra not in pipeline.list()



    m_replacement = TrackingMiddleware("replacement", priority_val=100)

    pipeline.replace(m_mid, m_replacement)

    assert m_mid not in pipeline.list()

    assert m_replacement in pipeline.list()





@pytest.mark.asyncio

async def test_pipeline_async_execution() -> None:

    """Verify async request flow executing before/after hooks in correct sequence."""

    pipeline = MiddlewarePipeline()

    pipeline.add(TrackingMiddleware("first", priority_val=200))

    pipeline.add(TrackingMiddleware("second", priority_val=100))



    req_context = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-1",

    )



    response = await pipeline.execute_async(req_context)

    exec_log = req_context.metadata["exec_log"]





    assert exec_log == ["first:before", "second:before", "second:after", "first:after"]

    assert "Endpoint provider not found" in response.errors[0]





def test_pipeline_sync_execution() -> None:

    """Verify synchronous runner blocks and executes successfully."""

    pipeline = MiddlewarePipeline()

    pipeline.add(TrackingMiddleware("sync-mw", priority_val=100))



    req_context = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-2",

    )



    response = pipeline.execute(req_context)

    assert req_context.metadata["exec_log"] == ["sync-mw:before", "sync-mw:after"]

    assert "Endpoint provider not found" in response.errors[0]





@pytest.mark.asyncio

async def test_pipeline_enable_disable() -> None:

    """Verify that categories of middlewares can be enabled/disabled."""

    pipeline = MiddlewarePipeline()

    m_track = TrackingMiddleware("tracker", priority_val=200)

    pipeline.add(m_track)



    req_context = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-3",

    )





    pipeline.disable(TrackingMiddleware)

    await pipeline.execute_async(req_context)

    assert "exec_log" not in req_context.metadata





    pipeline.enable(TrackingMiddleware)

    await pipeline.execute_async(req_context)

    assert req_context.metadata["exec_log"] == ["tracker:before", "tracker:after"]





@pytest.mark.asyncio

async def test_pipeline_short_circuit() -> None:

    """Verify that ShortCircuitException halts propagation and returns early."""

    pipeline = MiddlewarePipeline()

    pipeline.add(TrackingMiddleware("first", priority_val=200))

    pipeline.add(ShortCircuitingMiddleware())



    pipeline.add(TrackingMiddleware("ignored", priority_val=50))



    req_context = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-4",

    )



    response = await pipeline.execute_async(req_context)

    assert response.ai_response is not None

    assert response.ai_response.content == "short-circuited"

    assert response.telemetry.get("short") is True





    exec_log = req_context.metadata["exec_log"]

    assert "ignored:before" not in exec_log





@pytest.mark.asyncio

async def test_pipeline_exception_routing() -> None:

    """Verify that downstream errors are routed to on_exception hook correctly."""

    pipeline = MiddlewarePipeline()

    pipeline.add(RecoveryMiddleware())

    pipeline.add(ErrorMiddleware())



    req_context = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-5",

    )



    response = await pipeline.execute_async(req_context)

    assert response.ai_response is not None

    assert response.ai_response.content == "recovered"

    assert response.errors == ["simulated-error"]





@pytest.mark.asyncio

async def test_pipeline_cancellation() -> None:

    """Verify pipeline raises PipelineError if execution cancellation token is set."""

    pipeline = MiddlewarePipeline()

    pipeline.add(TrackingMiddleware("mw", priority_val=100))



    token = CancellationToken()

    req_context = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        cancellation_token=token,

        execution_id="exec-6",

    )





    token.cancel()

    with pytest.raises(PipelineError):

        await pipeline.execute_async(req_context)





def test_pipeline_fluent_builder() -> None:

    """Verify construction of pipeline chains via PipelineBuilder fluent API."""

    builder = PipelineBuilder()

    pipeline = (

        builder.add(TrackingMiddleware("first", priority_val=200))

        .add(TrackingMiddleware, "second", 100)

        .build()

    )



    middlewares = pipeline.list()

    assert len(middlewares) == 2

    assert middlewares[0]._name == "first"  # type: ignore

    assert middlewares[1]._name == "second"  # type: ignore





def test_middleware_manager_validation_and_lifecycle() -> None:

    """Verify precedence dependency rules and lifecycle notification hooks."""

    class Auth(Middleware):

        def __init__(self, priority_val: int = 100) -> None:

            self._priority = priority_val



        @property

        def priority(self) -> int:

            return self._priority



    class Provider(Middleware):

        def __init__(self, priority_val: int = 100) -> None:

            self._priority = priority_val



        @property

        def priority(self) -> int:

            return self._priority



        @property

        def run_after(self) -> list[type[Middleware]]:

            return [Auth]



    manager = MiddlewareManager()





    auth_inst = Auth(priority_val=200)

    provider_inst = Provider(priority_val=100)



    manager.register(auth_inst)

    manager.register(provider_inst)





    manager.validate_dependencies()





    manager.unregister(auth_inst)

    manager.unregister(provider_inst)



    auth_inst = Auth(priority_val=100)

    provider_inst = Provider(priority_val=200)





    manager.register(provider_inst)



    with pytest.raises(MiddlewareRegistrationError):

        manager.register(auth_inst)





    manager.unregister(provider_inst)





def test_middleware_manager_hot_reload() -> None:

    """Verify hot reloading of new middleware configurations."""

    manager = MiddlewareManager()

    m1 = TrackingMiddleware("m1", priority_val=10)

    manager.register(m1)



    m2 = TrackingMiddleware("m2", priority_val=20)



    manager.hot_reload([m2])



    assert m1 not in manager.pipeline.list()

    assert m2 in manager.pipeline.list()





def test_pipeline_executor() -> None:

    """Verify PipelineExecutor records timing duration."""

    pipeline = MiddlewarePipeline()

    executor = PipelineExecutor(pipeline)



    req_context = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-7",

    )



    response = executor.execute(req_context)

    assert response.timing_ms > 0.0





    async def run_async() -> ResponseContext:

        return await executor.execute_async(req_context)



    async_response = asyncio.run(run_async())

    assert async_response.timing_ms > 0.0











def test_default_placeholders() -> None:

    """Invoke all default placeholder middlewares to ensure they delegate correctly."""

    from forgecli.middleware.defaults import (
        AuthenticationMiddleware,
        CachingMiddleware,
        ContextOptimizerMiddleware,
        ConversationMiddleware,
        DependencyGraphMiddleware,
        ForgeGraphMiddleware,
        HistoryCompressorMiddleware,
        PolicyMiddleware,
        PromptOptimizerMiddleware,
        ProviderMiddleware,
        RepositoryPlannerMiddleware,
        ResponseOptimizerMiddleware,
        SemanticRetrievalMiddleware,
        StreamingMiddleware,
        SymbolLookupMiddleware,
        TelemetryMiddleware,
        TokenPlannerMiddleware,
    )



    placeholders = [

        TelemetryMiddleware,

        AuthenticationMiddleware,

        PolicyMiddleware,

        CachingMiddleware,

        HistoryCompressorMiddleware,

        TokenPlannerMiddleware,

        ContextOptimizerMiddleware,

        ConversationMiddleware,

        PromptOptimizerMiddleware,

        RepositoryPlannerMiddleware,

        DependencyGraphMiddleware,

        SymbolLookupMiddleware,

        ForgeGraphMiddleware,

        SemanticRetrievalMiddleware,

        StreamingMiddleware,

        ProviderMiddleware,

        ResponseOptimizerMiddleware,

    ]



    req_context = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-placeholders",

    )



    async def mock_next(req: RequestContext) -> ResponseContext:

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-test",

                request_id="req-test",

                content="test",

                finish_reason="stop",

                latency_ms=1.0,

            )

        )



    for cls in placeholders:

        mw = cls()

        assert mw.enabled is True

        assert isinstance(mw.priority, int)

        assert mw.run_before == []

        assert mw.run_after == []

        resp = asyncio.run(mw(req_context, mock_next))

        assert resp.ai_response is not None

        assert resp.ai_response.content == "test"





def test_manager_lifecycle_exceptions_and_rollback() -> None:

    """Verify that manager hot reload rolls back on failure and lifecycle hooks handle errors."""

    from forgecli.runtime_core.interfaces import LifecycleAware



    class FaultyLifecycleMiddleware(Middleware, LifecycleAware):

        def on_before_start(self) -> None:

            raise RuntimeError("startup-fail")



        def on_after_start(self) -> None:

            pass



        def on_before_shutdown(self) -> None:

            raise RuntimeError("shutdown-fail")



        def on_after_shutdown(self) -> None:

            pass



    class FaultyLifecycleMiddleware2(Middleware, LifecycleAware):

        def on_before_start(self) -> None:

            pass



        def on_after_start(self) -> None:

            raise RuntimeError("after-start-fail")



        def on_before_shutdown(self) -> None:

            pass



        def on_after_shutdown(self) -> None:

            raise RuntimeError("after-shutdown-fail")



    manager = MiddlewareManager()

    mw1 = FaultyLifecycleMiddleware()

    mw2 = FaultyLifecycleMiddleware2()

    manager.register(mw1)

    manager.register(mw2)





    manager.on_startup()



    manager.on_shutdown()





    class A(Middleware):

        pass



    class B(Middleware):

        @property

        def run_after(self) -> list[type[Middleware]]:

            return [A]



    b_inst = B()

    a_inst = A()

    setattr(b_inst, "_priority", 500)

    setattr(a_inst, "_priority", 100)



    with pytest.raises(MiddlewareRegistrationError):

        manager.hot_reload([b_inst, a_inst])





    class Y(Middleware):

        pass



    class X(Middleware):

        @property

        def run_before(self) -> list[type[Middleware]]:

            return [Y]



    x_inst = X()

    y_inst = Y()

    setattr(x_inst, "_priority", 100)

    setattr(y_inst, "_priority", 500)



    manager2 = MiddlewareManager()

    manager2.register(y_inst)

    with pytest.raises(MiddlewareRegistrationError):

        manager2.register(x_inst)





@pytest.mark.asyncio

async def test_base_hooks_handling() -> None:

    """Test exceptions thrown in before_request, after_request, and default hook routes."""



    class DummyMiddleware(Middleware):

        pass



    dummy = DummyMiddleware()

    assert dummy.run_before == []

    assert dummy.run_after == []



    req = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-disabled",

    )



    async def mock_next(r: RequestContext) -> ResponseContext:

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-dummy",

                request_id="req-dummy",

                content="dummy-out",

                finish_reason="stop",

                latency_ms=1.0,

            )

        )



    res = await dummy(req, mock_next)

    assert res.ai_response is not None

    assert res.ai_response.content == "dummy-out"



    class DisabledMiddleware(Middleware):

        @property

        def enabled(self) -> bool:

            return False



    mw = DisabledMiddleware()

    res_disabled = await mw(req, mock_next)

    assert res_disabled.ai_response is not None



    class SilentErrorMiddleware(Middleware):

        async def before_request(self, request: RequestContext) -> RequestContext:

            raise ValueError("silent")



    mw_silent = SilentErrorMiddleware()

    with pytest.raises(ValueError, match="silent"):

        await mw_silent(req, mock_next)



    class PostErrorRecoveryMiddleware(Middleware):

        async def after_request(self, request: RequestContext, response: ResponseContext) -> ResponseContext:

            raise ValueError("after-error")



        async def on_exception(self, request: RequestContext, exception: Exception) -> ResponseContext | None:

            if str(exception) == "after-error":

                return ResponseContext(errors=["recovered-after"])

            return None



    mw_post = PostErrorRecoveryMiddleware()

    res_post = await mw_post(req, mock_next)

    assert res_post.errors == ["recovered-after"]





    token = CancellationToken()

    req_cancel = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        cancellation_token=token,

        execution_id="exec-cancel-mid",

    )



    class CheckCancelMiddleware(Middleware):

        async def before_request(self, request: RequestContext) -> RequestContext:

            request.cancellation_token.cancel()

            return request



    mw_check = CheckCancelMiddleware()

    pipeline = MiddlewarePipeline()

    pipeline.add(mw_check)

    pipeline.add(dummy)



    with pytest.raises(PipelineError, match="Request cancelled before passing to next middleware"):

        await pipeline.execute_async(req_cancel)





def test_executor_failures() -> None:

    """Verify PipelineExecutor encapsulates pipeline run errors and records timing."""

    pipeline = MiddlewarePipeline()



    class BrokenMiddleware(Middleware):

        async def before_request(self, request: RequestContext) -> RequestContext:

            raise ValueError("crash")



    pipeline.add(BrokenMiddleware())

    executor = PipelineExecutor(pipeline)

    req = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-exec-fail",

    )



    with pytest.raises(ValueError, match="crash"):

        executor.execute(req)



    async def run_async_fail() -> None:

        await executor.execute_async(req)



    with pytest.raises(ValueError, match="crash"):

        asyncio.run(run_async_fail())





@pytest.mark.asyncio

async def test_sync_execution_in_running_loop() -> None:

    """Test synchronous execution when event loop is running (ThreadPoolExecutor branch)."""

    pipeline = MiddlewarePipeline()

    pipeline.add(TrackingMiddleware("sync-thread", priority_val=100))

    req = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test-s", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-sync-loop",

    )

    pipeline.execute(req)

    assert req.metadata["exec_log"] == ["sync-thread:before", "sync-thread:after"]





