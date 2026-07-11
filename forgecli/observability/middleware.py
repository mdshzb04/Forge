"""Telemetry Middleware for the Forge middleware engine."""



from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from forgecli.middleware.base import Middleware
from forgecli.observability.metrics import MetricsRegistry
from forgecli.observability.tracing import Tracer

if TYPE_CHECKING:

    from forgecli.middleware.context import RequestContext, ResponseContext



logger = logging.getLogger("forge.observability")





class TelemetryMiddleware(Middleware):

    """Pipeline middleware that traces requests and records telemetry metrics."""



    def __init__(self, metrics: MetricsRegistry | None = None) -> None:

        """Initialize the TelemetryMiddleware.

        Args:
            metrics: Optional shared metrics registry. If None, a new one is created.
        """

        self.metrics = metrics or MetricsRegistry()

        self.tracer = Tracer(self.metrics)



    @property

    def priority(self) -> int:

        """Priority ordering value (runs first to wrap entire pipeline)."""

        return 1000



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        """Intercept the request and measure its execution trace.

        Args:
            request: The RequestContext object.
            call_next: Next pipeline runner callback.
        """

        trace_id = request.tracing_ids.get("trace_id", request.execution_id)



        tags = {

            "model": request.ai_request.model_name,

            "provider": request.ai_request.provider_name,

        }



        logger.debug("Starting trace %s for request %s", trace_id, request.ai_request.request_id)



        with self.tracer.span("pipeline_execution", trace_id=trace_id, tags=tags) as span:

            try:

                response_ctx = await call_next(request)





                span.tags["status"] = "success"

                return response_ctx

            except Exception as e:



                span.tags["status"] = "error"

                span.tags["error_type"] = e.__class__.__name__

                raise

