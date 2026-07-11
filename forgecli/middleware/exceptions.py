"""Exception definitions for the Forge middleware engine.

Standardizes error categories during pipeline routing, validation, and short-circuiting.
"""



from __future__ import annotations

from typing import Any

from forgecli.runtime_core.errors import ForgeError


class MiddlewareError(ForgeError):

    """Base exception for all middleware management and execution failures."""



    pass





class PipelineError(MiddlewareError):

    """Raised when pipeline flow execution halts unexpectedly or is malformed."""



    pass





class MiddlewareRegistrationError(MiddlewareError):

    """Raised when a middleware is incorrectly registered or contains dependency conflicts."""



    pass





class ShortCircuitException(MiddlewareError):  # noqa: N818

    """Signaled by middleware to break execution and return a response immediately."""



    def __init__(self, message: str, response: Any, context: dict[str, Any] | None = None) -> None:

        """Initialize the ShortCircuitException with a completed response payload.

        Args:
            message: Description of the short-circuit event.
            response: The ResponseContext payload to return immediately.
            context: Contextual diagnostic data.
        """

        super().__init__(message, context)

        self.response = response

