"""Tracing framework for Forge observability."""



from __future__ import annotations

import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager

from forgecli.observability.metrics import MetricsRegistry


class TraceSpan:

    """Represents a single timed operation within a trace."""



    def __init__(self, name: str, trace_id: str, tags: dict[str, str] | None = None) -> None:

        self.name = name

        self.trace_id = trace_id

        self.tags = tags or {}

        self.start_time = time.time()

        self.end_time: float | None = None

        self.error: Exception | None = None



    @property

    def duration_ms(self) -> float:

        """Get the duration of the span in milliseconds."""

        end = self.end_time or time.time()

        return (end - self.start_time) * 1000.0





class Tracer:

    """Manages active traces and automatically reports spans to the metrics registry."""



    def __init__(self, metrics: MetricsRegistry) -> None:

        self._metrics = metrics



    @contextmanager

    def span(self, name: str, trace_id: str | None = None, tags: dict[str, str] | None = None) -> Generator[TraceSpan, None, None]:

        """Create a tracing span context manager.

        Args:
            name: The operation name.
            trace_id: An existing trace ID, or generates a new one if None.
            tags: Custom metadata tags.
        """

        active_trace_id = trace_id or str(uuid.uuid4())

        span_obj = TraceSpan(name, active_trace_id, tags)

        try:

            yield span_obj

        except Exception as e:

            span_obj.error = e

            span_obj.tags["error"] = e.__class__.__name__

            self._metrics.increment(f"{name}_errors", tags=span_obj.tags)

            raise

        finally:

            span_obj.end_time = time.time()

            self._metrics.record_value(f"{name}_latency_ms", span_obj.duration_ms, tags=span_obj.tags)

            self._metrics.increment(f"{name}_calls", tags=span_obj.tags)

