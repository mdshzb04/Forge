"""Caching middleware for the Forge middleware engine."""



from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from forgecli.memory.cache import Cache
from forgecli.middleware.base import Middleware
from forgecli.middleware.context import ResponseContext
from forgecli.runtime_core.response import AIResponse

if TYPE_CHECKING:

    from forgecli.middleware.context import RequestContext





class CachingMiddleware(Middleware):

    """Pipeline middleware that caches exact-match prompt completions."""



    def __init__(self, cache: Cache[str, AIResponse] | None = None) -> None:

        """Initialize the CachingMiddleware.

        Args:
            cache: The Cache instance to use. Defaults to an in-memory cache with 1h TTL.
        """

        self._cache = cache or Cache(default_ttl=3600.0)



    @property

    def priority(self) -> int:

        """Priority ordering value (runs early, after history compression)."""

        return 850



    def _compute_hash(self, request: RequestContext) -> str:

        """Compute a deterministic hash of the model, prompt, and messages."""

        data: dict[str, Any] = {

            "model": request.ai_request.model_name,

            "prompt": request.ai_request.prompt,

            "messages": request.ai_request.messages,

        }



        if request.ai_request.attached_files:

            files = []

            for f in sorted(request.ai_request.attached_files, key=lambda x: x.filepath):

                files.append({"path": f.filepath, "hash": f.hash_id})

            data["files"] = files



        json_bytes = json.dumps(data, sort_keys=True).encode("utf-8")

        return hashlib.sha256(json_bytes).hexdigest()



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        """Intercept the request and return a cached response if available.

        Args:
            request: The RequestContext object.
            call_next: Next pipeline runner callback.
        """

        if not request.metadata.get("cache_enabled", True):

            return await call_next(request)





        if request.ai_request.stream:

            return await call_next(request)



        cache_key = self._compute_hash(request)

        cached_response = self._cache.get(cache_key)



        if cached_response is not None:

            request.metadata["cache_hit"] = True

            return ResponseContext(

                ai_response=cached_response,

                execution_id=request.execution_id,

                tracing_ids=request.tracing_ids,

            )





        request.metadata["cache_hit"] = False

        response_ctx = await call_next(request)





        if response_ctx.ai_response and response_ctx.ai_response.content:

            self._cache.set(cache_key, response_ctx.ai_response)



        return response_ctx

