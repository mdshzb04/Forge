"""Health check abstractions for the Forge observability framework."""



from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass

class HealthStatus:

    """Represents the health of a specific subsystem."""



    name: str

    status: str

    message: str | None = None

    latency_ms: float | None = None

    last_checked: float = field(default_factory=time.time)

    metadata: dict[str, Any] = field(default_factory=dict)





class HealthMonitor:

    """Aggregates health checks across the system."""



    def __init__(self) -> None:

        self._checks: dict[str, HealthStatus] = {}



    def report(self, status: HealthStatus) -> None:

        """Report a subsystem status."""

        self._checks[status.name] = status



    def get_overall_health(self) -> dict[str, Any]:

        """Aggregate and evaluate the system's total health."""

        total_status = "ok"

        down_components = []

        degraded_components = []



        for name, stat in self._checks.items():

            if stat.status == "down":

                total_status = "down"

                down_components.append(name)

            elif stat.status == "degraded" and total_status == "ok":

                total_status = "degraded"

                degraded_components.append(name)



        return {

            "status": total_status,

            "timestamp": time.time(),

            "down_components": down_components,

            "degraded_components": degraded_components,

            "details": {k: {"status": v.status, "message": v.message, "latency_ms": v.latency_ms} for k, v in self._checks.items()},

        }

