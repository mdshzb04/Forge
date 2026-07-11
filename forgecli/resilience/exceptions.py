"""Resilience exceptions for Forge."""



from __future__ import annotations

from forgecli.runtime_core.errors import ForgeError


class ResilienceError(ForgeError):

    """Base exception for resilience failures."""





class CircuitOpenError(ResilienceError):

    """Exception raised when a circuit breaker is open and preventing calls."""



    def __init__(self, service: str, message: str = "Circuit is OPEN.") -> None:

        super().__init__(f"Circuit for '{service}' is open: {message}")

        self.service = service





class MaxRetriesExceededError(ResilienceError):

    """Exception raised when all retry attempts have failed."""



    def __init__(self, service: str, attempts: int, last_error: Exception) -> None:

        super().__init__(f"Max retries ({attempts}) exceeded for '{service}'. Last error: {last_error}")

        self.service = service

        self.attempts = attempts

        self.last_error = last_error

