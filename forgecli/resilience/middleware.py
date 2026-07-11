"""Resilience Middleware for the Forge middleware engine."""



from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from forgecli.middleware.base import Middleware
from forgecli.resilience.circuit_breaker import CircuitBreaker
from forgecli.resilience.exceptions import CircuitOpenError, MaxRetriesExceededError
from forgecli.resilience.retry import RetryPolicy

if TYPE_CHECKING:

    from forgecli.middleware.context import RequestContext, ResponseContext



logger = logging.getLogger("forge.resilience")





class ResilienceMiddleware(Middleware):

    """Pipeline middleware that applies circuit breaking and retries."""



    def __init__(

        self,

        service_name: str = "llm_provider",

        circuit_breaker: CircuitBreaker | None = None,

        retry_policy: RetryPolicy | None = None,

    ) -> None:

        """Initialize the ResilienceMiddleware.

        Args:
            service_name: Name of the upstream service.
            circuit_breaker: Custom circuit breaker. Default is used if None.
            retry_policy: Custom retry policy. Default is used if None.
        """

        self.service_name = service_name

        self.circuit_breaker = circuit_breaker or CircuitBreaker(service=service_name)





        self.retry_policy = retry_policy or RetryPolicy(service=service_name, max_attempts=3)



    @property

    def priority(self) -> int:

        """Priority ordering value (runs right before the Provider)."""

        return 250



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        """Intercept the request and execute it via resilience policies.

        Args:
            request: The RequestContext object.
            call_next: Next pipeline runner callback.
        """



        async def _protected_call() -> ResponseContext:

            return await self.circuit_breaker.execute_async(call_next, request)



        try:

            return await self.retry_policy.execute_async(_protected_call)

        except (CircuitOpenError, MaxRetriesExceededError) as e:

            logger.error("Resilience policy blocked execution for request %s: %s", request.ai_request.request_id, e)

            raise

