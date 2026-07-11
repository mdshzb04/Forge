"""Streaming Runtime Middleware."""



from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING

from forgecli.middleware.base import Middleware
from forgecli.runtime_core.response import AIResponse
from forgecli.streaming.events import StreamChunk, StreamEnd, StreamEvent

if TYPE_CHECKING:

    from forgecli.middleware.context import RequestContext, ResponseContext



logger = logging.getLogger("forge.streaming")





class StreamInterceptor:

    """Wraps an async iterator to accumulate text and construct an AIResponse."""



    def __init__(self, original_iterator: AsyncIterator[StreamEvent], response_ctx: ResponseContext, request_id: str) -> None:

        self.original_iterator = original_iterator

        self.response_ctx = response_ctx

        self.request_id = request_id

        self.accumulated_text = ""

        self.finish_reason = "stop"



    async def __aiter__(self) -> AsyncIterator[StreamEvent]:

        try:

            async for event in self.original_iterator:

                if isinstance(event, StreamChunk):

                    self.accumulated_text += event.text

                elif isinstance(event, StreamEnd):

                    self.finish_reason = event.finish_reason

                yield event

        finally:



            logger.debug("Stream completed for request %s. Total length: %d", self.request_id, len(self.accumulated_text))

            if not self.response_ctx.ai_response:

                self.response_ctx.ai_response = AIResponse(

                    response_id=f"resp-{self.request_id}",

                    request_id=self.request_id,

                    content=self.accumulated_text,

                    finish_reason=self.finish_reason,

                    latency_ms=self.response_ctx.timing_ms,

                )

            else:

                self.response_ctx.ai_response.content = self.accumulated_text

                self.response_ctx.ai_response.finish_reason = self.finish_reason





class StreamingMiddleware(Middleware):

    """Pipeline middleware that intercepts streams to accumulate content."""



    @property

    def priority(self) -> int:

        """Priority ordering value (runs late, right above the provider)."""

        return 300



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        """Intercept the request and wrap the output stream if present.

        Args:
            request: The RequestContext object.
            call_next: Next pipeline runner callback.
        """

        response_ctx = await call_next(request)





        if request.ai_request.stream and response_ctx.stream_iterator is not None:

            logger.debug("Intercepting stream for request %s", request.ai_request.request_id)

            interceptor = StreamInterceptor(

                original_iterator=response_ctx.stream_iterator,

                response_ctx=response_ctx,

                request_id=request.ai_request.request_id,

            )



            response_ctx.stream_iterator = interceptor.__aiter__()



        return response_ctx

