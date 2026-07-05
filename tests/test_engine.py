"""Tests for the Execution Engine framework.

These tests cover the orchestration framework itself — the
``Stage`` protocol, ``EventBus``, ``ExecutionEngine`` lifecycle,
retries, cancellation, and plugin hooks. The actual stage
*implementations* (intent, retrieval, etc.) are exercised by the
existing CLI / orchestrator tests; this file only verifies the
framework is wired correctly.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Any, cast

import pytest

from forgecli.engine import (
    EngineContext,
    EngineResult,
    EventBus,
    ExecutionEngine,
    LogLevel,
    PipelineBuilder,
    ProgressEvent,
    Stage,
    StageContext,
    StageEvent,
    StageLog,
    StageRegistry,
    StageResult,
    StageStatus,
    TextLogEvent,
)
from forgecli.engine.plugins import HookManager, PluginHook

# ---------------------------------------------------------------------------
# Stage protocol
# ---------------------------------------------------------------------------


def test_stage_is_callable() -> None:
    async def run(context: StageContext) -> StageResult:
        return StageResult(status=StageStatus.SUCCEEDED, notes=("hi",))

    stage: Stage = run  # type: ignore[assignment]
    stage.name = "echo"
    ctx = StageContext(
        engine=EngineContext(prompt="x", cwd=Path("/tmp")),
        bus=EventBus(),
    )
    result = asyncio.run(stage(ctx))
    assert result.status is StageStatus.SUCCEEDED


def test_stage_protocol_is_runtime_checkable() -> None:
    class _S:
        name = "s"

        async def __call__(self, context: StageContext) -> StageResult:
            return StageResult(status=StageStatus.SUCCEEDED)

    # ``isinstance`` works for Protocol classes that have non-method
    # members (like ``name``). Plain functions don't satisfy the
    # protocol at runtime; only classes do.
    assert isinstance(_S(), Stage)


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------


def test_event_bus_publishes_to_subscribers() -> None:
    bus = EventBus()
    received: list[StageEvent] = []

    def handler(event: Any) -> None:
        received.append(event)

    bus.subscribe(StageEvent, handler)
    bus.publish(StageEvent(stage="x", status="running"))
    bus.publish(StageEvent(stage="x", status="succeeded"))
    assert len(received) == 2
    assert received[0].status == "running"
    assert received[1].status == "succeeded"


def test_event_bus_history() -> None:
    bus = EventBus()
    bus.publish(TextLogEvent(level=LogLevel.INFO, source="x", message="hi"))
    bus.publish(ProgressEvent(stage="x", progress=0.5))
    history = bus.drain()
    assert len(history) == 2
    assert isinstance(history[0], TextLogEvent)
    assert isinstance(history[1], ProgressEvent)


def test_event_bus_unsubscribe() -> None:
    bus = EventBus()
    received: list[int] = []

    def handler(_: Any) -> None:
        received.append(1)

    bus.subscribe(StageEvent, handler)
    bus.publish(StageEvent(stage="x"))
    bus.unsubscribe(StageEvent, handler)
    bus.publish(StageEvent(stage="x"))
    assert len(received) == 1


def test_event_bus_cancellation_token() -> None:
    bus = EventBus()
    assert not bus.is_cancelled()
    bus.cancel()
    assert bus.is_cancelled()
    bus.reset_cancellation()
    assert not bus.is_cancelled()


def test_event_bus_async_subscriber() -> None:
    bus = EventBus()
    received: list[str] = []

    async def handler(event: Any) -> None:
        received.append(event.message)

    bus.subscribe(TextLogEvent, handler)

    async def main() -> None:
        await bus.publish_and_drain(TextLogEvent(source="x", message="hello"))

    asyncio.run(main())
    assert received == ["hello"]


# ---------------------------------------------------------------------------
# StageContext helpers
# ---------------------------------------------------------------------------


def test_stage_context_log_and_progress_publish_events() -> None:
    bus = EventBus()
    ctx = StageContext(
        engine=EngineContext(prompt="x", cwd=Path("/tmp"), extras={"stage_name": "demo"}),
        bus=bus,
    )
    ctx.log("hello", level=LogLevel.INFO)
    ctx.progress(0.42, message="halfway")
    types = [type(e) for e in bus.history]
    assert TextLogEvent in types
    assert ProgressEvent in types
    assert cast(TextLogEvent, bus.history[0]).source == "demo"
    assert cast(ProgressEvent, bus.history[1]).progress == 0.42


# ---------------------------------------------------------------------------
# ExecutionEngine lifecycle
# ---------------------------------------------------------------------------


class _EchoStage:
    name = "echo"

    def __init__(self, name: str = "echo", note: str = "ok") -> None:
        # Allow per-instance names so the registry can hold multiple
        # distinct stages under their canonical names.
        self.name = name
        self.note = note
        self.calls = 0

    async def __call__(self, context: StageContext) -> StageResult:
        self.calls += 1
        context.log(f"running {self.name}", level=LogLevel.INFO)
        return StageResult(status=StageStatus.SUCCEEDED, notes=(self.note,))


class _FlakyStage:
    name = "flaky"

    def __init__(self, fail_count: int) -> None:
        self.fail_count = fail_count
        self.calls = 0

    async def __call__(self, context: StageContext) -> StageResult:
        self.calls += 1
        if self.calls <= self.fail_count:
            raise RuntimeError("transient")
        return StageResult(status=StageStatus.SUCCEEDED, notes=("recovered",))


class _BoomStage:
    name = "boom"

    async def __call__(self, context: StageContext) -> StageResult:
        raise RuntimeError("permanent")


class _CancelStage:
    name = "cancel"

    async def __call__(self, context: StageContext) -> StageResult:
        context.bus.cancel()
        return StageResult(status=StageStatus.SUCCEEDED)


def test_engine_runs_all_stages_in_order() -> None:
    bus = EventBus()
    a, b, c = _EchoStage("a"), _EchoStage("b"), _EchoStage("c")
    engine = ExecutionEngine(stages=[a, b, c], bus=bus)
    result = asyncio.run(engine.run(EngineContext(prompt="p", cwd=Path("/tmp"))))
    assert result.success
    assert len(result.stage_results) == 3
    assert [a.calls, b.calls, c.calls] == [1, 1, 1]


def test_engine_short_circuits_on_failure() -> None:
    bus = EventBus()
    a, boom, c = _EchoStage(), _BoomStage(), _EchoStage()
    engine = ExecutionEngine(stages=[a, boom, c], bus=bus)
    result = asyncio.run(engine.run(EngineContext(prompt="p", cwd=Path("/tmp"))))
    assert not result.success
    assert result.failed_stage == "boom"
    assert a.calls == 1
    assert c.calls == 0  # never reached


def test_engine_retries_then_succeeds() -> None:
    bus = EventBus()
    flaky = _FlakyStage(fail_count=2)
    engine = ExecutionEngine(
        stages=[flaky],
        bus=bus,
        max_attempts_per_stage=3,
        retry_backoff_seconds=0.0,
    )
    result = asyncio.run(engine.run(EngineContext(prompt="p", cwd=Path("/tmp"))))
    assert result.success
    assert flaky.calls == 3
    # Stage events: running, retrying, retrying, succeeded.
    events = [e for e in bus.history if isinstance(e, StageEvent)]
    statuses = [e.status for e in events]
    assert statuses == ["running", "retrying", "retrying", "succeeded"]


def test_engine_gives_up_after_max_attempts() -> None:
    bus = EventBus()
    flaky = _FlakyStage(fail_count=10)
    engine = ExecutionEngine(
        stages=[flaky],
        bus=bus,
        max_attempts_per_stage=3,
        retry_backoff_seconds=0.0,
    )
    result = asyncio.run(engine.run(EngineContext(prompt="p", cwd=Path("/tmp"))))
    assert not result.success
    assert flaky.calls == 3
    assert result.error is not None


def test_engine_emits_cancelled_when_token_set_before_stage() -> None:
    bus = EventBus()
    bus.cancel()
    engine = ExecutionEngine(stages=[_EchoStage("cancel-pre")], bus=bus)
    result = asyncio.run(engine.run(EngineContext(prompt="p", cwd=Path("/tmp"))))
    assert not result.success
    assert result.cancelled is True


def test_engine_emits_cancelled_when_stage_cancels_midway() -> None:
    bus = EventBus()
    a = _EchoStage("cancel-mid-a")
    cancel = _CancelStage()
    c = _EchoStage("cancel-mid-c")
    engine = ExecutionEngine(stages=[a, cancel, c], bus=bus)
    result = asyncio.run(engine.run(EngineContext(prompt="p", cwd=Path("/tmp"))))
    assert not result.success
    assert result.cancelled is True
    assert a.calls == 1
    assert c.calls == 0


def test_engine_records_stage_logs() -> None:
    bus = EventBus()
    a = _EchoStage("log-test", note="done")
    engine = ExecutionEngine(stages=[a], bus=bus)
    context = EngineContext(prompt="p", cwd=Path("/tmp"))
    asyncio.run(engine.run(context))
    assert len(context.log) == 1
    log = context.log[0]
    assert isinstance(log, StageLog)
    assert log.stage == "log-test"
    assert log.status == "succeeded"


def test_engine_from_registry_uses_default_pipeline() -> None:
    registry = StageRegistry()
    for name in ExecutionEngine.DEFAULT_PIPELINE:
        registry.register(_EchoStage(name))
    engine = ExecutionEngine.from_registry(registry)
    assert [s.name for s in engine.stages] == list(ExecutionEngine.DEFAULT_PIPELINE)


def test_engine_from_registry_unknown_stage_raises() -> None:
    registry = StageRegistry()
    with pytest.raises(KeyError):
        ExecutionEngine.from_registry(registry)


def test_engine_rejects_sync_stage() -> None:
    def sync_stage(context: StageContext) -> StageResult:
        return StageResult(status=StageStatus.SUCCEEDED)

    sync_stage.name = "sync-stage"  # type: ignore[attr-defined]
    bus = EventBus()
    engine = ExecutionEngine(stages=[sync_stage], bus=bus)  # type: ignore[list-item]
    result = asyncio.run(engine.run(EngineContext(prompt="p", cwd=Path("/tmp"))))
    assert not result.success
    assert "did not return an awaitable" in (result.error or "")


# ---------------------------------------------------------------------------
# PipelineBuilder
# ---------------------------------------------------------------------------


def test_pipeline_builder_assembles_engine() -> None:
    a, b = _EchoStage("a"), _EchoStage("b")
    engine = (
        PipelineBuilder().stage(a).stage(b).with_max_attempts(5).with_retry_backoff(0.1).build()
    )
    assert engine.stages == [a, b]
    assert engine._max_attempts == 5
    assert engine._retry_backoff == 0.1


# ---------------------------------------------------------------------------
# StageRegistry + plugin replacement
# ---------------------------------------------------------------------------


def test_stage_registry_rejects_duplicate() -> None:
    registry = StageRegistry()
    a = _EchoStage("dup")
    registry.register(a)
    with pytest.raises(ValueError):
        registry.register(a)


def test_stage_registry_replace_succeeds() -> None:
    registry = StageRegistry()
    registry.register(_EchoStage("replace-me", note="v1"))
    registry.replace(_EchoStage("replace-me", note="v2"))
    stage = cast(_EchoStage, registry.get("replace-me"))
    assert stage.note == "v2"


# ---------------------------------------------------------------------------
# HookManager
# ---------------------------------------------------------------------------


def test_hooks_fire_in_registration_order() -> None:
    calls: list[str] = []

    async def make_before(name: str):
        async def hook() -> None:
            calls.append(f"before:{name}")

        return hook

    async def make_after(name: str):
        async def hook() -> None:
            calls.append(f"after:{name}")

        return hook

    async def main() -> None:
        manager = HookManager()
        manager.add_before(PluginHook(name="b1", callback=await make_before("b1")))
        manager.add_before(PluginHook(name="b2", callback=await make_before("b2")))
        manager.add_after(PluginHook(name="a1", callback=await make_after("a1")))
        manager.add_after(PluginHook(name="a2", callback=await make_after("a2")))
        context = EngineContext(prompt="p", cwd=Path("/tmp"))
        await manager.fire_before(context, EventBus())
        # fake result for the after hooks
        result = EngineResult(success=True, context=context, stage_results=[])
        await manager.fire_after(result, EventBus())

    asyncio.run(main())
    assert calls == [
        "before:b1",
        "before:b2",
        "after:a1",
        "after:a2",
    ]


def test_hook_failure_does_not_abort_engine() -> None:
    bus = EventBus()
    context = EngineContext(prompt="p", cwd=Path("/tmp"))
    manager = HookManager()
    manager.add_before(
        PluginHook(name="bad", callback=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    )
    asyncio.run(manager.fire_before(context, bus))
    # The engine bus got a warn-level log line for the failure.
    warns = [e for e in bus.history if isinstance(e, TextLogEvent) and e.level is LogLevel.WARN]
    assert any("before-pipeline hook failed" in e.message for e in warns)


# ---------------------------------------------------------------------------
# EngineContext + structured log payload
# ---------------------------------------------------------------------------


def test_engine_context_to_log_dict_is_serializable() -> None:
    context = EngineContext(prompt="x", cwd=Path("/tmp"))
    context.intent_analysis = None
    context.applied_files = []
    payload = context.to_log_dict()
    import json

    # Must be JSON-serializable.
    json.dumps(payload)
    assert payload["run_id"]


# Silence unused-import warnings for symbols only used in some branches.
_ = contextlib
