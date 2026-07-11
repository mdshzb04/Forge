"""Circuit breaker state machine."""



from __future__ import annotations

import threading
import time
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

from forgecli.resilience.exceptions import CircuitOpenError

T = TypeVar("T")





class CircuitState(str, Enum):

    CLOSED = "closed"

    OPEN = "open"

    HALF_OPEN = "half_open"





class CircuitBreaker:

    """State machine that tracks failures and opens the circuit to prevent cascading failures."""



    def __init__(

        self,

        service: str,

        failure_threshold: int = 5,

        recovery_timeout: float = 30.0,

    ) -> None:

        """Initialize the CircuitBreaker.

        Args:
            service: Name of the protected service.
            failure_threshold: Number of consecutive failures before opening.
            recovery_timeout: Time in seconds before transitioning from OPEN to HALF-OPEN.
        """

        self.service = service

        self.failure_threshold = failure_threshold

        self.recovery_timeout = recovery_timeout



        self._lock = threading.Lock()

        self._state = CircuitState.CLOSED

        self._failures = 0

        self._last_failure_time: float | None = None



    @property

    def state(self) -> CircuitState:

        """Get the current state, handling automatic transitions from OPEN to HALF_OPEN."""

        with self._lock:

            if self._state == CircuitState.OPEN:

                if self._last_failure_time and (time.time() - self._last_failure_time) > self.recovery_timeout:

                    self._state = CircuitState.HALF_OPEN

            return self._state



    def record_success(self) -> None:

        """Record a successful operation, closing the circuit if it was half-open."""

        with self._lock:

            self._failures = 0

            self._state = CircuitState.CLOSED



    def record_failure(self) -> None:

        """Record a failed operation, potentially opening the circuit."""

        with self._lock:

            self._failures += 1

            self._last_failure_time = time.time()

            if self._failures >= self.failure_threshold or self._state == CircuitState.HALF_OPEN:

                self._state = CircuitState.OPEN



    def check(self) -> None:

        """Check if execution is allowed. Raises CircuitOpenError if not."""

        if self.state == CircuitState.OPEN:

            raise CircuitOpenError(self.service)



    async def execute_async(self, func: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:

        """Execute an asynchronous function protected by the circuit breaker."""

        self.check()

        try:

            result = await func(*args, **kwargs)

            self.record_success()

            return result

        except Exception:

            self.record_failure()

            raise

