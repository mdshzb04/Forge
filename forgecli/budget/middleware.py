"""Budget and Context Window Middlewares."""



from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from forgecli.budget.planner import TokenPlanner
from forgecli.budget.window import ContextWindowManager
from forgecli.middleware.base import Middleware

if TYPE_CHECKING:

    from forgecli.middleware.context import RequestContext, ResponseContext



logger = logging.getLogger("forge.budget")





class TokenPlannerMiddleware(Middleware):

    """Pipeline middleware that allocates token limits."""



    def __init__(self, planner: TokenPlanner | None = None) -> None:

        self.planner = planner or TokenPlanner()



    @property

    def priority(self) -> int:

        """Priority ordering value."""

        return 750



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:



        budget = self.planner.plan_budget(

            model_name=request.ai_request.model_name,

            requested_max_tokens=request.ai_request.max_tokens,

        )

        request.metadata["token_budget"] = budget



        return await call_next(request)





class ContextOptimizerMiddleware(Middleware):

    """Pipeline middleware that trims the request payload to fit within the budget."""



    def __init__(self, window_manager: ContextWindowManager | None = None) -> None:

        self.window_manager = window_manager or ContextWindowManager()



    @property

    def priority(self) -> int:

        """Priority ordering value (must run after TokenPlanner)."""

        return 700



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:



        budget = request.metadata.get("token_budget")

        if budget:

            trimmed_messages = self.window_manager.trim_messages(

                messages=request.ai_request.messages,

                budget=budget,

            )

            request.ai_request.messages = trimmed_messages

        else:

            logger.warning("No token budget found on request; skipping context optimization.")



        return await call_next(request)

