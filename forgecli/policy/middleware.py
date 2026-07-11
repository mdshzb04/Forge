"""Policy Middleware for the Forge middleware engine."""



from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from forgecli.middleware.base import Middleware

if TYPE_CHECKING:

    from forgecli.middleware.context import RequestContext, ResponseContext
    from forgecli.policy.engine import PolicyEngine





class PolicyMiddleware(Middleware):

    """Pipeline middleware that executes security and compliance policies on the request context."""



    def __init__(self, policy_engine: PolicyEngine) -> None:

        """Initialize the PolicyMiddleware.

        Args:
            policy_engine: The PolicyEngine orchestrator.
        """

        self._engine = policy_engine



    @property

    def priority(self) -> int:

        """Priority ordering value (higher runs earlier)."""

        return 900



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        """Intercept and evaluate policies for the request.

        Args:
            request: The RequestContext object.
            call_next: Next pipeline runner callback.
        """

        self._engine.evaluate(request)

        return await call_next(request)

