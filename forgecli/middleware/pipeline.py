"""Middleware execution pipeline for the Forge middleware engine.

Manages registration, ordering, enabling/disabling, and dispatching request/response flows.
"""



from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from collections.abc import Awaitable, Callable

from forgecli.middleware.base import Middleware
from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.middleware.exceptions import PipelineError, ShortCircuitException

logger = logging.getLogger("forge.middleware.pipeline")





class MiddlewarePipeline:

    """Orchestrates sequential dispatch of request context records through interceptors."""



    def __init__(self) -> None:

        """Initialize the MiddlewarePipeline."""

        self._lock = threading.Lock()

        self._middlewares: list[Middleware] = []

        self._disabled_types: set[type[Middleware]] = set()



    def add(self, middleware: Middleware) -> None:

        """Add a middleware instance to the pipeline.

        Args:
            middleware: The middleware instance.
        """

        with self._lock:

            if middleware not in self._middlewares:

                self._middlewares.append(middleware)

                logger.debug("Added middleware '%s' to pipeline.", type(middleware).__name__)



    def insert(self, index: int, middleware: Middleware) -> None:

        """Insert a middleware instance at a specific index in the raw list.

        Note: Execution precedence is determined by priority sorting.

        Args:
            index: List index position.
            middleware: The middleware instance.
        """

        with self._lock:

            if middleware not in self._middlewares:

                self._middlewares.insert(index, middleware)

                logger.debug(

                    "Inserted middleware '%s' at index %d.",

                    type(middleware).__name__,

                    index,

                )



    def remove(self, middleware: Middleware) -> None:

        """Remove a middleware instance.

        Args:
            middleware: The middleware instance.
        """

        with self._lock:

            if middleware in self._middlewares:

                self._middlewares.remove(middleware)

                logger.debug("Removed middleware '%s' from pipeline.", type(middleware).__name__)



    def replace(self, old_middleware: Middleware, new_middleware: Middleware) -> None:

        """Replace an existing middleware instance with a new one.

        Args:
            old_middleware: The middleware instance to remove.
            new_middleware: The middleware instance to register in its place.
        """

        with self._lock:

            if old_middleware in self._middlewares:

                idx = self._middlewares.index(old_middleware)

                self._middlewares[idx] = new_middleware

                logger.debug(

                    "Replaced middleware '%s' with '%s'.",

                    type(old_middleware).__name__,

                    type(new_middleware).__name__,

                )



    def enable(self, middleware_type: type[Middleware]) -> None:

        """Enable all middlewares of a specific class category in the pipeline.

        Args:
            middleware_type: The class type to enable.
        """

        with self._lock:

            self._disabled_types.discard(middleware_type)

            logger.info("Category '%s' enabled.", middleware_type.__name__)



    def disable(self, middleware_type: type[Middleware]) -> None:

        """Disable all middlewares of a specific class category in the pipeline.

        Args:
            middleware_type: The class type to disable.
        """

        with self._lock:

            self._disabled_types.add(middleware_type)

            logger.info("Category '%s' disabled.", middleware_type.__name__)



    def list(self) -> list[Middleware]:

        """List all registered middlewares sorted by current execution precedence.

        Returns:
            List of sorted Middleware instances.
        """

        with self._lock:

            current_list = list(self._middlewares)

            current_list.sort(key=lambda m: m.priority, reverse=True)

            return current_list



    async def execute_async(self, request: RequestContext) -> ResponseContext:

        """Asynchronously dispatch request context through the middleware list.

        Args:
            request: The RequestContext object to process.

        Returns:
            The finalized ResponseContext output.

        Raises:
            PipelineError: If cancellation occurs or execution is corrupted.
        """

        with self._lock:



            active_middlewares = [

                m

                for m in self._middlewares

                if m.enabled and not any(isinstance(m, t) for t in self._disabled_types)

            ]

            active_middlewares.sort(key=lambda m: m.priority, reverse=True)



        async def terminal_delegate(req: RequestContext) -> ResponseContext:



            return ResponseContext(

                ai_response=None,

                timing_ms=0.0,

                usage={},

                provider_metadata={},

                errors=["Endpoint provider not found in pipeline execution chain."],

                streaming_metadata={},

                telemetry={},

            )



        current_delegate: Callable[[RequestContext], Awaitable[ResponseContext]] = terminal_delegate

        for middleware in reversed(active_middlewares):



            def make_call_next(

                mw: Middleware,

                next_del: Callable[[RequestContext], Awaitable[ResponseContext]],

            ) -> Callable[[RequestContext], Awaitable[ResponseContext]]:

                async def call_next(req: RequestContext) -> ResponseContext:

                    if req.cancellation_token and req.cancellation_token.is_cancelled:

                        raise PipelineError("Pipeline execution cancelled.")

                    return await mw(req, next_del)



                return call_next



            current_delegate = make_call_next(middleware, current_delegate)



        try:

            return await current_delegate(request)

        except ShortCircuitException as exc:

            logger.info("Pipeline execution short-circuited: %s", exc)

            return exc.response



    def execute(self, request: RequestContext) -> ResponseContext:

        """Synchronously execute the pipeline.

        Helper wrapper that blocks until the async pipeline execution completes.

        Args:
            request: The RequestContext object to process.

        Returns:
            The completed ResponseContext.
        """

        try:

            loop = asyncio.get_event_loop()

        except RuntimeError:

            loop = asyncio.new_event_loop()

            asyncio.set_event_loop(loop)



        if loop.is_running():



            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:

                future = executor.submit(lambda: asyncio.run(self.execute_async(request)))

                return future.result()

        else:

            return asyncio.run(self.execute_async(request))

