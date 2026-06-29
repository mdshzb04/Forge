"""The Stage interface, StageContext, and ExecutionEngine.

A :class:`Stage` is the unit of orchestration. Every stage is a
small async callable that takes a :class:`StageContext` and returns
a :class:`StageResult`. Stages are *independently replaceable* — a
plugin can drop in a custom stage that supersedes the default one
under the same name.

The :class:`ExecutionEngine` runs the registered stages in order,
emits structured events, supports retries, cancellation, and a
small lifecycle:

* StageStart -> stage.run() -> StageEnd
* On exception: schedule a retry up to ``max_attempts``; on
  exhaustion mark the run failed.
* On cancellation: raise :class:`EngineCancelled` immediately.

The engine does *no* business logic. Stages encapsulate the work.
"""

from __future__ import annotations

import asyncio
import inspect
import time
import traceback
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from forgecli.engine.context import EngineContext, StageLog
from forgecli.engine.events import (
    EventBus,
    LogLevel,
    ProgressEvent,
    StageEvent,
    TextLogEvent,
)


class StageStatus(str, Enum):
    """Per-stage lifecycle status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class StageResult:
    """Structured output of a :class:`Stage`.

    Every stage returns one of these. The ``data`` dict is a free-form
    bag of structured output (typed per stage); ``notes`` are
    human-readable summary lines; ``error`` is set on failure.
    """

    status: StageStatus
    data: dict[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    error: str | None = None


@dataclass
class StageContext:
    """Per-stage runtime context.

    The engine hands each stage a :class:`StageContext` that bundles
    the shared :class:`EngineContext` with the active
    :class:`EventBus`, the current attempt number, and a helper
    for emitting progress / log events.
    """

    engine: EngineContext
    bus: EventBus
    attempt: int = 1
    max_attempts: int = 1

    def log(self, message: str, *, level: LogLevel = LogLevel.INFO, source: str = "") -> None:
        self.bus.publish(
            TextLogEvent(
                level=level,
                source=source or self.engine.extras.get("stage_name", ""),
                message=message,
                run_id=self.engine.run_id,
            )
        )

    def progress(self, value: float, *, message: str | None = None) -> None:
        self.bus.publish(
            ProgressEvent(
                stage=self.engine.extras.get("stage_name", ""),
                progress=max(0.0, min(1.0, value)),
                message=message,
                run_id=self.engine.run_id,
            )
        )

    def cancelled(self) -> bool:
        return self.bus.is_cancelled()


@runtime_checkable
class Stage(Protocol):
    """The protocol every engine stage must implement.

    A Stage is *just* an async callable that takes a
    :class:`StageContext` and returns a :class:`StageResult`. The
    name (``name``) is what shows up in events and logs. Stages
    are normally registered by name so plugins can replace them
    individually.
    """

    name: str

    async def __call__(self, context: StageContext) -> StageResult: ...


# ---------------------------------------------------------------------------
# Convenience base class
# ---------------------------------------------------------------------------


class BaseStage(ABC):
    """A small ABC for stages that prefer the class form.

    The engine accepts both :class:`Stage` callables and
    :class:`BaseStage` instances. Subclasses must set ``name`` and
    implement :meth:`run`.
    """

    name: str = "abstract"

    @abstractmethod
    async def run(self, context: StageContext) -> StageResult:
        """Execute the stage and return a :class:`StageResult`."""

    async def __call__(self, context: StageContext) -> StageResult:
        return await self.run(context)


# ---------------------------------------------------------------------------
# Default stage implementations (no business logic — only contracts)
# ---------------------------------------------------------------------------


class _NoOpStage(BaseStage):
    """A pass-through stage that does nothing. Useful for tests."""

    name = "noop"

    async def run(self, context: StageContext) -> StageResult:
        return StageResult(status=StageStatus.SUCCEEDED, notes=("no-op",))


# ---------------------------------------------------------------------------
# Result of a run
# ---------------------------------------------------------------------------


@dataclass
class EngineResult:
    """The result of a complete engine run."""

    success: bool
    context: EngineContext
    stage_results: list[StageResult]
    failed_stage: str | None = None
    cancelled: bool = False
    error: str | None = None


# ---------------------------------------------------------------------------
# Pipeline builder
# ---------------------------------------------------------------------------


@dataclass
class PipelineBuilder:
    """Fluent builder for an :class:`ExecutionEngine` instance."""

    bus: EventBus = field(default_factory=EventBus)  # type: ignore[assignment]
    stages: list[Stage] = field(default_factory=list)
    max_attempts_per_stage: int = 1
    retry_backoff_seconds: float = 0.5

    def stage(self, stage: Stage) -> PipelineBuilder:
        self.stages.append(stage)
        return self

    def stages_from(
        self, names: Iterable[str], registry: StageRegistry
    ) -> PipelineBuilder:
        for name in names:
            stage = registry.get(name)
            self.stages.append(stage)
        return self

    def with_max_attempts(self, attempts: int) -> PipelineBuilder:
        self.max_attempts_per_stage = max(1, attempts)
        return self

    def with_retry_backoff(self, seconds: float) -> PipelineBuilder:
        self.retry_backoff_seconds = max(0.0, seconds)
        return self

    def build(self) -> ExecutionEngine:
        return ExecutionEngine(
            stages=self.stages,
            bus=self.bus,
            max_attempts_per_stage=self.max_attempts_per_stage,
            retry_backoff_seconds=self.retry_backoff_seconds,
        )


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------


class StageRegistry:
    """A name -> Stage mapping.

    Plugins and core ship stages to this registry; the engine looks
    them up by name when assembling a pipeline. A registry can be
    populated directly, by entry-point plugin, or by calling
    :meth:`register`.
    """

    def __init__(self) -> None:
        self._stages: dict[str, Stage] = {}

    def register(self, stage: Stage) -> None:
        if not stage.name:
            raise ValueError("Stage.name must be non-empty")
        if stage.name in self._stages:
            raise ValueError(f"Stage {stage.name!r} already registered")
        self._stages[stage.name] = stage

    def replace(self, stage: Stage) -> None:
        if not stage.name:
            raise ValueError("Stage.name must be non-empty")
        self._stages[stage.name] = stage

    def get(self, name: str) -> Stage:
        if name not in self._stages:
            raise KeyError(f"No stage registered under {name!r}")
        return self._stages[name]

    def has(self, name: str) -> bool:
        return name in self._stages

    def names(self) -> list[str]:
        return list(self._stages)


# ---------------------------------------------------------------------------
# ExecutionEngine
# ---------------------------------------------------------------------------


class ExecutionEngine:
    """The async orchestration runtime.

    The engine does no business logic. It runs the registered
    stages in order, emitting structured events, retrying failed
    stages up to ``max_attempts_per_stage`` with a backoff, and
    honouring a cancellation token between stages.
    """

    DEFAULT_PIPELINE: tuple[str, ...] = (
        "intent-analyzer",
        "repository-analyzer",
        "context-optimizer",
        "planning-engine",
        "model-router",
        "execution-engine",
        "validation-engine",
        "git-engine",
    )

    def __init__(
        self,
        stages: Iterable[Stage] | None = None,
        *,
        bus: EventBus | None = None,
        max_attempts_per_stage: int = 1,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self.bus: EventBus = bus or EventBus()
        self._stages: list[Stage] = list(stages or [])
        self._max_attempts = max(1, max_attempts_per_stage)
        self._retry_backoff = max(0.0, retry_backoff_seconds)

    @classmethod
    def from_registry(
        cls,
        registry: StageRegistry,
        *,
        names: Iterable[str] | None = None,
        bus: EventBus | None = None,
        max_attempts_per_stage: int = 1,
        retry_backoff_seconds: float = 0.5,
    ) -> ExecutionEngine:
        names = tuple(names or cls.DEFAULT_PIPELINE)
        stages = [registry.get(name) for name in names]
        return cls(
            stages=stages,
            bus=bus,
            max_attempts_per_stage=max_attempts_per_stage,
            retry_backoff_seconds=retry_backoff_seconds,
        )

    @property
    def stages(self) -> list[Stage]:
        return list(self._stages)

    async def run(self, context: EngineContext) -> EngineResult:
        """Run every stage in order; return a structured :class:`EngineResult`."""
        if not self.bus.is_cancelled():
            self.bus.reset_cancellation()
        results: list[StageResult] = []

        for stage in self._stages:
            if self.bus.is_cancelled():
                self.bus.publish(
                    TextLogEvent(
                        level=LogLevel.WARN,
                        source=stage.name,
                        message="engine cancelled before stage",
                        run_id=context.run_id,
                    )
                )
                return EngineResult(
                    success=False,
                    context=context,
                    stage_results=results,
                    cancelled=True,
                )

            stage_result = await self._run_stage(stage, context)
            results.append(stage_result)
            if stage_result.status is StageStatus.FAILED:
                return EngineResult(
                    success=False,
                    context=context,
                    stage_results=results,
                    failed_stage=stage.name,
                    error=stage_result.error,
                )
        return EngineResult(
            success=True,
            context=context,
            stage_results=results,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _run_stage(
        self, stage: Stage, context: EngineContext
    ) -> StageResult:
        stage_context = StageContext(
            engine=context,
            bus=self.bus,
            attempt=1,
            max_attempts=self._max_attempts,
        )
        # Make the active stage name visible to the stage via extras
        # so log()/progress() can label themselves.
        context.extras["stage_name"] = stage.name

        log = StageLog(stage=stage.name, status="running", started_at=time.time())
        context.log.append(log)

        self.bus.publish(
            StageEvent(
                stage=stage.name,
                status="running",
                attempt=1,
                run_id=context.run_id,
            )
        )

        last_exc: BaseException | None = None
        for attempt in range(1, self._max_attempts + 1):
            stage_context.attempt = attempt
            try:
                result = await self._invoke(stage, stage_context)
            except asyncio.CancelledError:
                log = replace(
                    log,
                    status="failed",
                    error="cancelled",
                    finished_at=time.time(),
                )
                context.log[-1] = log
                self.bus.publish(
                    StageEvent(
                        stage=stage.name,
                        status="failed",
                        attempt=attempt,
                        note="cancelled",
                        run_id=context.run_id,
                    )
                )
                return StageResult(
                    status=StageStatus.FAILED,
                    notes=("cancelled",),
                    error="cancelled",
                )
            except Exception as exc:
                last_exc = exc
                self.bus.publish(
                    TextLogEvent(
                        level=LogLevel.ERROR,
                        source=stage.name,
                        message=f"stage failed: {exc}",
                        run_id=context.run_id,
                    )
                )
                if attempt >= self._max_attempts:
                    break
                self.bus.publish(
                    StageEvent(
                        stage=stage.name,
                        status="retrying",
                        attempt=attempt + 1,
                        note=str(exc),
                        run_id=context.run_id,
                    )
                )
                if self._retry_backoff > 0:
                    await asyncio.sleep(self._retry_backoff * attempt)
                continue
            else:
                log = replace(
                    log,
                    status="skipped" if result.status is StageStatus.SKIPPED else "succeeded",
                    finished_at=time.time(),
                    notes=result.notes,
                )
                context.log[-1] = log
                self.bus.publish(
                    StageEvent(
                        stage=stage.name,
                        status=log.status,
                        attempt=attempt,
                        run_id=context.run_id,
                    )
                )
                return result

        # All retries exhausted.
        log = replace(
            log,
            status="failed",
            finished_at=time.time(),
            error=repr(last_exc) if last_exc else "unknown error",
        )
        context.log[-1] = log
        self.bus.publish(
            StageEvent(
                stage=stage.name,
                status="failed",
                attempt=self._max_attempts,
                note=log.error,
                run_id=context.run_id,
            )
        )
        return StageResult(
            status=StageStatus.FAILED,
            notes=("retries exhausted",),
            error=log.error,
        )

    async def _invoke(
        self, stage: Stage, stage_context: StageContext
    ) -> StageResult:
        """Run a single stage invocation.

        Handles both async callables and sync callables. Surfaces
        unexpected exceptions to the event bus before propagating.
        """
        try:
            result = stage(stage_context)
            if inspect.isawaitable(result):
                return await result
            if asyncio.iscoroutine(result):
                return await result
            # Stage returned synchronously: that's a programmer error
            # (every engine stage is async). Surface it cleanly.
            raise TypeError(
                f"Stage {stage.name!r} did not return an awaitable; "
                "engine stages must be async."
            )
        except Exception:
            self.bus.publish(
                TextLogEvent(
                    level=LogLevel.ERROR,
                    source=stage.name,
                    message=traceback.format_exc(),
                    run_id=stage_context.engine.run_id,
                )
            )
            raise


__all__ = [
    "BaseStage",
    "EngineResult",
    "ExecutionEngine",
    "PipelineBuilder",
    "Stage",
    "StageContext",
    "StageRegistry",
    "StageResult",
    "StageStatus",
]
