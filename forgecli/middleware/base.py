"""Base middleware interface for the Forge middleware engine.

Defines lifecycle hooks and call structures for all pipeline layers.
"""



from __future__ import annotations

from abc import ABC
from collections.abc import Awaitable, Callable

from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.middleware.exceptions import PipelineError


class Middleware(ABC):  # noqa: B024

    """Abstract base class for all request pipeline middleware interceptors."""



    @property

    def priority(self) -> int:

        """Execution priority of the middleware.

        Higher numbers execute earlier in the incoming pipeline (and later in the response path).
        """

        return 100



    @property

    def enabled(self) -> bool:

        """Whether this middleware is currently enabled for execution."""

        return True



    @property

    def run_after(self) -> list[type[Middleware]]:

        """List of middleware classes that must execute before this middleware (higher priority)."""

        return []



    @property

    def run_before(self) -> list[type[Middleware]]:

        """List of middleware classes that must execute after this middleware (lower priority)."""

        return []



    async def before_request(self, request: RequestContext) -> RequestContext:

        """Invoked on incoming requests traveling down the pipeline.

        Args:
            request: The current request context.

        Returns:
            The processed (or unmodified) request context.
        """

        return request



    async def after_request(self, request: RequestContext, response: ResponseContext) -> ResponseContext:

        """Invoked on outgoing responses traveling up the pipeline.

        Args:
            request: The request context associated with the response.
            response: The response context generated downstream.

        Returns:
            The processed (or unmodified) response context.
        """

        return response



    async def on_exception(self, request: RequestContext, exception: Exception) -> ResponseContext | None:

        """Invoked if an exception is raised by a downstream middleware or provider.

        If a ResponseContext is returned, the exception is swallowed and the returned context
        is sent back up the pipeline. If None is returned, the exception continues to propagate.

        Args:
            request: The current request context.
            exception: The error encountered.

        Returns:
            A resolved response context to recover, or None to let the error propagate.
        """

        return None



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        """Intercepts and controls execution flow of the request.

        Can be overridden by subclasses for complex routing/interceptor needs.

        Args:
            request: The incoming request context.
            call_next: Next execution link in the pipeline.

        Returns:
            The output response context.
        """

        if not self.enabled:

            return await call_next(request)





        try:

            request = await self.before_request(request)

        except Exception as exc:

            resp = await self.on_exception(request, exc)

            if resp is not None:

                return resp

            raise





        if request.cancellation_token and request.cancellation_token.is_cancelled:

            raise PipelineError("Request cancelled before passing to next middleware.")





        try:

            response = await call_next(request)

        except Exception as exc:

            resp = await self.on_exception(request, exc)

            if resp is not None:

                return resp

            raise





        try:

            response = await self.after_request(request, response)

        except Exception as exc:

            resp = await self.on_exception(request, exc)

            if resp is not None:

                return resp

            raise



        return response

