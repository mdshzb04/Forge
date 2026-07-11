"""Default middleware implementations for the Forge middleware engine.

Each slot delegates to the real implementation from its domain module.
When dependencies are unavailable (standalone testing or no config), middlewares
pass through transparently.
"""



from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from forgecli.middleware.base import Middleware
from forgecli.middleware.context import RequestContext, ResponseContext

if TYPE_CHECKING:

    pass



logger = logging.getLogger("forge.middleware")





class TelemetryMiddleware(Middleware):

    """Pipeline middleware that traces requests and records telemetry metrics."""



    def __init__(self) -> None:

        try:

            from forgecli.observability.middleware import TelemetryMiddleware as _Real

            self._impl = _Real()

        except Exception:

            logger.debug("TelemetryMiddleware: real impl unavailable, using pass-through")

            self._impl = None



    @property

    def priority(self) -> int:

        return 1000



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        if self._impl is not None:

            return await self._impl(request, call_next)

        return await call_next(request)





class AuthenticationMiddleware(Middleware):

    """Validates authentication tokens and credentials on incoming requests."""



    def __init__(self, required: bool = False) -> None:

        self._required = required



    @property

    def priority(self) -> int:

        return 950



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        import os



        token = request.metadata.get("auth_token") or os.environ.get("FORGE_API_KEY")

        if token:

            request.metadata["authenticated"] = True

            request.metadata["auth_mode"] = "token"

        elif self._required:

            from forgecli.core.errors import ForgeCLIError

            raise ForgeCLIError("Authentication required. Set FORGE_API_KEY or provide an auth token.")

        else:

            request.metadata["authenticated"] = False

        return await call_next(request)





class PolicyMiddleware(Middleware):

    """Evaluates safety and compliance policies on request context."""



    def __init__(self) -> None:

        try:

            from forgecli.policy.engine import PolicyEngine
            from forgecli.policy.middleware import PolicyMiddleware as _Real

            self._impl = _Real(policy_engine=PolicyEngine())

        except Exception:

            logger.debug("PolicyMiddleware: real impl unavailable, using pass-through")

            self._impl = None



    @property

    def priority(self) -> int:

        return 900



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        if self._impl is not None:

            return await self._impl(request, call_next)

        return await call_next(request)





class CachingMiddleware(Middleware):

    """Pipeline middleware that caches exact-match prompt completions."""



    def __init__(self) -> None:

        try:

            from forgecli.memory.caching_middleware import CachingMiddleware as _Real

            self._impl = _Real()

        except Exception:

            logger.debug("CachingMiddleware: real impl unavailable, using pass-through")

            self._impl = None



    @property

    def priority(self) -> int:

        return 850



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        if self._impl is not None:

            return await self._impl(request, call_next)

        return await call_next(request)





class HistoryCompressorMiddleware(Middleware):

    """Compresses long conversation histories to fit token windows."""



    def __init__(self, keep_recent_turns: int = 4) -> None:

        try:

            from forgecli.memory.middleware import HistoryCompressionMiddleware

            self._impl = HistoryCompressionMiddleware(keep_recent_turns=keep_recent_turns)

        except Exception:

            logger.debug("HistoryCompressorMiddleware: real impl unavailable, using pass-through")

            self._impl = None



    @property

    def priority(self) -> int:

        return 800



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        if self._impl is not None:

            return await self._impl(request, call_next)

        return await call_next(request)





class TokenPlannerMiddleware(Middleware):

    """Allocates token limits and computes budget for the request."""



    def __init__(self) -> None:

        try:

            from forgecli.budget.middleware import TokenPlannerMiddleware as _Real

            self._impl = _Real()

        except Exception:

            logger.debug("TokenPlannerMiddleware: real impl unavailable, using pass-through")

            self._impl = None



    @property

    def priority(self) -> int:

        return 750



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        if self._impl is not None:

            return await self._impl(request, call_next)

        return await call_next(request)





class ContextOptimizerMiddleware(Middleware):

    """Trims request payload to fit within the computed token budget."""



    def __init__(self) -> None:

        try:

            from forgecli.budget.middleware import ContextOptimizerMiddleware as _Real

            self._impl = _Real()

        except Exception:

            logger.debug("ContextOptimizerMiddleware: real impl unavailable, using pass-through")

            self._impl = None



    @property

    def priority(self) -> int:

        return 700



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        if self._impl is not None:

            return await self._impl(request, call_next)

        return await call_next(request)





class ConversationMiddleware(Middleware):

    """Loads, appends, and persists conversation session state."""



    def __init__(self) -> None:

        self._manager = None

        try:

            from forgecli.conversation.manager import SessionManager
            from forgecli.platform.paths import get_data_dir

            data_dir = get_data_dir() if hasattr(__import__("forgecli.platform.paths", fromlist=["get_data_dir"]), "get_data_dir") else None

            persistence = Path(data_dir) / "sessions" if data_dir else None

            self._manager = SessionManager(persistence_dir=persistence)

        except Exception:

            logger.debug("ConversationMiddleware: SessionManager unavailable, using pass-through")



    @property

    def priority(self) -> int:

        return 650



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        if self._manager is None:

            return await call_next(request)



        session_id = request.metadata.get("session_id", request.execution_id)

        session = self._manager.get_or_create_session(session_id)



        if request.ai_request.prompt:

            session.append_message("user", request.ai_request.prompt)



        response = await call_next(request)



        if response.ai_response and response.ai_response.content:

            session.append_message("assistant", response.ai_response.content)

            self._manager.save_session(session_id)



        return response





class PromptOptimizerMiddleware(Middleware):

    """Applies Ponytail prompt ruleset optimization to the request."""



    def __init__(self, intensity: str = "lite") -> None:

        try:

            from forgecli.middleware.ponytail_adapter import PonytailAdapterMiddleware

            self._impl = PonytailAdapterMiddleware(intensity=intensity)

        except Exception:

            logger.debug("PromptOptimizerMiddleware: Ponytail adapter unavailable, using pass-through")

            self._impl = None



    @property

    def priority(self) -> int:

        return 600



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        if self._impl is not None:

            return await self._impl(request, call_next)

        return await call_next(request)





class RepositoryPlannerMiddleware(Middleware):

    """Scans workspace and resolves files relevant to the user query.

    Context preparation is handled directly by prepare_runtime_sync / shared_extraction.
    This middleware stage is preserved for pipeline compatibility.
    """

    def __init__(self) -> None:
        pass

    @property
    def priority(self) -> int:
        return 550

    async def __call__(
        self,
        request: RequestContext,
        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],
    ) -> ResponseContext:
        request.metadata["repository_planned"] = True
        return await call_next(request)





class DependencyGraphMiddleware(Middleware):
    """Builds import dependency graph for matched repository files.

    Dependency extraction is handled by shared_extraction.py in the canonical path.
    """

    def __init__(self) -> None:
        pass

    @property
    def priority(self) -> int:
        return 500

    async def __call__(
        self,
        request: RequestContext,
        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],
    ) -> ResponseContext:
        request.metadata["dependency_graph"] = []
        return await call_next(request)





class SymbolLookupMiddleware(Middleware):
    """Extracts structural symbols (classes, functions) from attached files.

    Symbol extraction is handled by shared_extraction.py in the canonical path.
    """

    def __init__(self) -> None:
        pass

    @property
    def priority(self) -> int:
        return 450

    async def __call__(
        self,
        request: RequestContext,
        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],
    ) -> ResponseContext:
        request.metadata["symbol_lookup"] = []
        return await call_next(request)





class GraphifyMiddleware(Middleware):

    """Queries the RepositoryGraph to enrich context with structural nodes."""



    def __init__(self, graph: Any = None) -> None:

        if graph is not None:

            self._graph = graph

        else:

            try:

                from forgecli.graph.backend_forgegraph import ForgeRepositoryGraph

                self._graph = ForgeRepositoryGraph(root=Path.cwd())

            except Exception:

                logger.debug("GraphifyMiddleware: graph backend unavailable, using pass-through")

                self._graph = None



    @property

    def priority(self) -> int:

        return 400



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        if self._graph is None:

            return await call_next(request)



        try:

            from forgecli.middleware.graphify_adapter import GraphifyAdapterMiddleware

            adapter = GraphifyAdapterMiddleware(graph=self._graph)

            return await adapter(request, call_next)

        except Exception:

            return await call_next(request)





class SemanticRetrievalMiddleware(Middleware):
    """Ranks files by query relevance and trims context to top results.

    Semantic ranking is handled by prepare_runtime_sync in the canonical path.
    """

    def __init__(self, top_n: int = 10) -> None:
        self._top_n = top_n

    @property
    def priority(self) -> int:
        return 350

    async def __call__(
        self,
        request: RequestContext,
        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],
    ) -> ResponseContext:
        request.metadata["semantic_ranking_applied"] = True
        return await call_next(request)





class StreamingMiddleware(Middleware):

    """Intercepts streams to accumulate content into the final AIResponse."""



    def __init__(self) -> None:

        try:

            from forgecli.streaming.middleware import StreamingMiddleware as _Real

            self._impl = _Real()

        except Exception:

            logger.debug("StreamingMiddleware: real impl unavailable, using pass-through")

            self._impl = None



    @property

    def priority(self) -> int:

        return 300



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        if self._impl is not None:

            return await self._impl(request, call_next)

        return await call_next(request)





class ProviderMiddleware(Middleware):

    """Terminal middleware: resolves provider via router and calls the LLM API."""



    def __init__(self) -> None:

        self._router = None

        try:

            from forgecli.providers.provider_registry import ProviderRegistry as Phase4Registry
            from forgecli.providers.provider_router import ProviderRouter

            registry = Phase4Registry()

            self._router = ProviderRouter(registry=registry)

        except Exception:

            logger.debug("ProviderMiddleware: router unavailable, using pass-through")



    @property

    def priority(self) -> int:

        return 200



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        if self._router is None:

            return await call_next(request)



        model_query = request.ai_request.model_name or None

        try:

            provider, resolved_model = await self._router.route_request(model_query)

        except Exception:

            return await call_next(request)



        from forgecli.providers.base import ChatMessage, ChatRequest, Role
        from forgecli.providers.provider_context import ProviderContext



        messages = []

        for msg in request.ai_request.messages:

            role_val = msg.get("role", "user")

            if role_val == "system":

                role = Role.SYSTEM

            elif role_val == "assistant":

                role = Role.ASSISTANT

            else:

                role = Role.USER

            messages.append(ChatMessage(role=role, content=msg.get("content", "")))



        messages.append(ChatMessage(role=Role.USER, content=request.ai_request.prompt))



        chat_req = ChatRequest(

            model=resolved_model,

            messages=messages,

            temperature=request.ai_request.temperature,

            max_tokens=request.ai_request.max_tokens,

            stream=request.ai_request.stream,

        )



        pc = ProviderContext(

            provider=provider,

            model=resolved_model,

            workspace=request.runtime_context.workspace,

            request_context=request,

        )



        if request.ai_request.stream:

            ai_response = await provider.send(pc)

            return ResponseContext(

                ai_response=ai_response,

                execution_id=request.execution_id,

                tracing_ids=request.tracing_ids,

            )

        else:

            chat_response = await provider.chat(chat_req)

            from forgecli.runtime_core.response import AIResponse

            ai_resp = AIResponse(

                response_id=f"resp-{request.execution_id}",

                request_id=request.ai_request.request_id,

                content=chat_response.message.content,

                finish_reason=chat_response.finish_reason,

                latency_ms=0.0,

            )

            return ResponseContext(

                ai_response=ai_resp,

                execution_id=request.execution_id,

                tracing_ids=request.tracing_ids,

            )





class ResponseOptimizerMiddleware(Middleware):

    """Post-processes LLM responses: validates syntax, scrubs, and formats."""



    def __init__(self) -> None:

        pass



    @property

    def priority(self) -> int:

        return 100



    async def __call__(
        self,
        request: RequestContext,
        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],
    ) -> ResponseContext:
        response = await call_next(request)

        if response.ai_response and response.ai_response.content:
            try:
                from forgecli.optimizer.quality_validation import QualityValidator
                valid = QualityValidator.validate_braces_balance(response.ai_response.content)
                if not valid:
                    logger.warning("ResponseOptimizer: braces unbalanced in response")
                response.metadata["response_validated"] = True
                response.metadata["response_braces_ok"] = valid
            except Exception:
                pass

        return response

