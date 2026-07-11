"""Structured event bus for the Execution Engine.

The :class:`EventBus` is a tiny pub/sub dispatcher for the four
event kinds the engine emits:

* :class:`StageEvent` — a stage transitioned to a new state.
* :class:`ProgressEvent` — fractional progress within a stage.
* :class:`TextLogEvent` — a free-form log line (the engine's
  "streaming log" surface).
* :class:`EngineEvent` — the abstract base; every concrete event
  inherits from it.

Subscribers can be sync or async; the engine handles fan-out
sequentially. A single :class:`asyncio.Event` (the cancellation
token) is checked between stages and during long operations so a
caller can abort cleanly.
"""



from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class LogLevel(str, Enum):

    """Severity for :class:`TextLogEvent`."""



    DEBUG = "debug"

    INFO = "info"

    WARN = "warn"

    ERROR = "error"





@dataclass(frozen=True)

class EngineEvent:

    """Abstract base of every event the engine emits."""



    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    run_id: str = ""





@dataclass(frozen=True)

class StageEvent(EngineEvent):

    """A stage transitioned to a new state."""



    stage: str = ""

    status: str = "running"

    attempt: int = 1

    note: str | None = None





@dataclass(frozen=True)

class ProgressEvent(EngineEvent):

    """Fractional progress within a stage (0.0 - 1.0)."""



    stage: str = ""

    progress: float = 0.0

    message: str | None = None





@dataclass(frozen=True)

class TextLogEvent(EngineEvent):

    """A free-form log line emitted by a stage."""



    level: LogLevel = LogLevel.INFO

    source: str = ""

    message: str = ""





EventHandler = Callable[[EngineEvent], "None | Awaitable[None]"]





class EventBus:

    """In-process pub/sub bus for engine events.

    Subscribers are registered per event class. Handlers may be sync
    or async; the engine awaits any coroutines it gets back. A single
    :class:`asyncio.Event` (the cancellation token) is checked between
    stages so the caller can abort cleanly.
    """



    def __init__(self) -> None:

        self._subscribers: dict[type, list[EventHandler]] = {}

        self.cancellation = asyncio.Event()

        self.history: list[EngineEvent] = []











    def subscribe(self, event_cls: type[EngineEvent], handler: EventHandler) -> None:

        self._subscribers.setdefault(event_cls, []).append(handler)



    def unsubscribe(self, event_cls: type[EngineEvent], handler: EventHandler) -> None:

        bucket = self._subscribers.get(event_cls)

        if not bucket:

            return

        with contextlib.suppress(ValueError):

            bucket.remove(handler)











    def cancel(self) -> None:

        """Request cancellation. The engine checks ``cancellation`` between stages."""

        self.cancellation.set()



    def reset_cancellation(self) -> None:

        self.cancellation.clear()



    def is_cancelled(self) -> bool:

        return self.cancellation.is_set()











    def publish(self, event: EngineEvent) -> None:

        """Publish synchronously; async handlers are scheduled."""

        self.history.append(event)

        for handler in list(self._subscribers.get(type(event), ())):

            try:

                result = handler(event)

            except Exception:

                continue

            if asyncio.iscoroutine(result):



                try:

                    loop = asyncio.get_running_loop()

                    task = loop.create_task(result)

                    task.add_done_callback(self._discard_task)

                except RuntimeError:

                    pass



    @staticmethod

    def _discard_task(task: asyncio.Task) -> None:









        return None



    async def publish_and_drain(self, event: EngineEvent) -> None:

        """Publish and await any async handler results."""

        self.history.append(event)

        for handler in list(self._subscribers.get(type(event), ())):

            try:

                result = handler(event)

            except Exception:

                continue

            if asyncio.iscoroutine(result):

                await result











    def drain(self) -> list[EngineEvent]:

        return list(self.history)















class EngineCancelledError(Exception):

    """Raised by the engine when the cancellation token is set."""





__all__ = [

    "EngineCancelledError",

    "EngineEvent",

    "EventBus",

    "EventHandler",

    "LogLevel",

    "ProgressEvent",

    "StageEvent",

    "TextLogEvent",

]

