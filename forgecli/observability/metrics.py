"""Metrics tracking and aggregation for the Forge Observability framework."""



from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass

class MetricValue:

    """Represents a metric state."""



    count: int = 0

    sum: float = 0.0

    min: float | None = None

    max: float | None = None

    last_updated: float = field(default_factory=time.time)





class MetricsRegistry:

    """In-memory thread-safe metrics registry.

    Provides basic counters and histograms/gauges for tracking telemetry
    across the Forge execution pipeline.
    """



    def __init__(self) -> None:

        self._lock = threading.Lock()

        self._counters: dict[str, int] = defaultdict(int)

        self._histograms: dict[str, MetricValue] = defaultdict(MetricValue)



    def increment(self, name: str, tags: dict[str, str] | None = None, amount: int = 1) -> None:

        """Increment a counter metric."""

        tag_suffix = self._format_tags(tags)

        key = f"{name}{tag_suffix}"

        with self._lock:

            self._counters[key] += amount



    def record_value(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:

        """Record a value (e.g. latency) for a histogram/summary metric."""

        tag_suffix = self._format_tags(tags)

        key = f"{name}{tag_suffix}"

        with self._lock:

            metric = self._histograms[key]

            metric.count += 1

            metric.sum += value

            if metric.min is None or value < metric.min:

                metric.min = value

            if metric.max is None or value > metric.max:

                metric.max = value

            metric.last_updated = time.time()



    def get_counter(self, name: str, tags: dict[str, str] | None = None) -> int:

        """Retrieve a counter value."""

        key = f"{name}{self._format_tags(tags)}"

        with self._lock:

            return self._counters.get(key, 0)



    def get_histogram(self, name: str, tags: dict[str, str] | None = None) -> MetricValue | None:

        """Retrieve a histogram state."""

        key = f"{name}{self._format_tags(tags)}"

        with self._lock:

            val = self._histograms.get(key)

            if not val:

                return None



            return MetricValue(

                count=val.count,

                sum=val.sum,

                min=val.min,

                max=val.max,

                last_updated=val.last_updated,

            )



    def dump_metrics(self) -> dict[str, Any]:

        """Dump all metrics as a dictionary for exporting/reporting."""

        with self._lock:

            histograms_dump = {}

            for k, v in self._histograms.items():

                avg = v.sum / v.count if v.count > 0 else 0.0

                histograms_dump[k] = {

                    "count": v.count,

                    "sum": v.sum,

                    "avg": avg,

                    "min": v.min,

                    "max": v.max,

                }

            return {

                "counters": dict(self._counters),

                "histograms": histograms_dump,

            }



    def _format_tags(self, tags: dict[str, str] | None) -> str:

        if not tags:

            return ""



        tag_strs = [f"{k}={v}" for k, v in sorted(tags.items())]

        return "{" + ",".join(tag_strs) + "}"

