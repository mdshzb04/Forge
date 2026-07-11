"""Pipeline execution coordinator for the Forge middleware engine.

Provides helper methods to run request loops with execution statistics and measurements.
"""



from __future__ import annotations

import time

from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.middleware.pipeline import MiddlewarePipeline


class PipelineExecutor:

    """Executes a MiddlewarePipeline measuring total elapsed timing and metrics."""



    def __init__(self, pipeline: MiddlewarePipeline) -> None:

        """Initialize with a MiddlewarePipeline instance.

        Args:
            pipeline: The active MiddlewarePipeline.
        """

        self.pipeline = pipeline



    async def execute_async(self, request: RequestContext) -> ResponseContext:

        """Asynchronously execute the pipeline recording time spent.

        Args:
            request: The current request context.

        Returns:
            The processed response context containing timing stats.
        """

        start_time = time.perf_counter()

        try:

            response = await self.pipeline.execute_async(request)

        except Exception as exc:



            elapsed = (time.perf_counter() - start_time) * 1000.0

            response = ResponseContext(

                ai_response=None,

                timing_ms=elapsed,

                errors=[str(exc)],

            )

            raise exc



        elapsed = (time.perf_counter() - start_time) * 1000.0

        response.timing_ms = elapsed

        return response



    def execute(self, request: RequestContext) -> ResponseContext:

        """Synchronously execute the pipeline recording timing.

        Args:
            request: The current request context.

        Returns:
            The processed response context.
        """

        start_time = time.perf_counter()

        try:

            response = self.pipeline.execute(request)

        except Exception as exc:

            elapsed = (time.perf_counter() - start_time) * 1000.0

            response = ResponseContext(

                ai_response=None,

                timing_ms=elapsed,

                errors=[str(exc)],

            )

            raise exc



        elapsed = (time.perf_counter() - start_time) * 1000.0

        response.timing_ms = elapsed

        return response

