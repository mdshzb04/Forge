"""Forge middleware engine package.

Exposes the pipeline composition infrastructure, request contexts, execution tools,
and core placeholder middlewares for the Universal AI Runtime.
"""



from __future__ import annotations

from forgecli.middleware.base import Middleware
from forgecli.middleware.builder import PipelineBuilder
from forgecli.middleware.responseforge_adapter import ResponseForgeAdapterMiddleware
from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.middleware.decorators import middleware
from forgecli.middleware.defaults import (
    AuthenticationMiddleware,
    CachingMiddleware,
    ConversationMiddleware,
    DependencyGraphMiddleware,
    ForgeGraphMiddleware,
    HistoryCompressorMiddleware,
    PolicyMiddleware,
    PromptOptimizerMiddleware,
    ProviderMiddleware,
    RepositoryPlannerMiddleware,
    ResponseOptimizerMiddleware,
    SemanticRetrievalMiddleware,
    SymbolLookupMiddleware,
)
from forgecli.middleware.exceptions import (
    MiddlewareError,
    MiddlewareRegistrationError,
    PipelineError,
    ShortCircuitException,
)
from forgecli.middleware.executor import PipelineExecutor
from forgecli.middleware.forgegraph_adapter import ForgeGraphAdapterMiddleware
from forgecli.middleware.middleware_manager import MiddlewareManager
from forgecli.middleware.pipeline import MiddlewarePipeline
from forgecli.middleware.promptforge_adapter import PromptForgeAdapterMiddleware
from forgecli.middleware.registration import (
    get_registered_middleware_types,
    register_middleware_type,
    unregister_middleware_type,
)
from forgecli.observability.middleware import TelemetryMiddleware

__all__ = [

    "AuthenticationMiddleware",
    "CachingMiddleware",
    "ResponseForgeAdapterMiddleware",
    "ConversationMiddleware",
    "DependencyGraphMiddleware",
    "ForgeGraphAdapterMiddleware",
    "ForgeGraphMiddleware",
    "HistoryCompressorMiddleware",
    "Middleware",
    "MiddlewareError",
    "MiddlewareManager",
    "MiddlewarePipeline",
    "MiddlewareRegistrationError",
    "PipelineBuilder",
    "PipelineError",
    "PipelineExecutor",
    "PolicyMiddleware",
    "PromptForgeAdapterMiddleware",
    "PromptOptimizerMiddleware",
    "ProviderMiddleware",
    "RepositoryPlannerMiddleware",
    "RequestContext",
    "ResponseContext",
    "ResponseOptimizerMiddleware",
    "SemanticRetrievalMiddleware",
    "ShortCircuitException",
    "SymbolLookupMiddleware",
    "TelemetryMiddleware",
    "get_registered_middleware_types",
    "middleware",
    "register_middleware_type",
    "unregister_middleware_type",

]

