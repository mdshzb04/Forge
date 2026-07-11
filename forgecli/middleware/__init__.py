"""Forge middleware engine package.

Exposes the pipeline composition infrastructure, request contexts, execution tools,
and core placeholder middlewares for the Universal AI Runtime.
"""



from __future__ import annotations

from forgecli.middleware.base import Middleware
from forgecli.middleware.builder import PipelineBuilder
from forgecli.middleware.caveman_adapter import CavemanAdapterMiddleware
from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.middleware.decorators import middleware
from forgecli.middleware.defaults import (
    AuthenticationMiddleware,
    CachingMiddleware,
    ConversationMiddleware,
    DependencyGraphMiddleware,
    GraphifyMiddleware,
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
from forgecli.middleware.graphify_adapter import GraphifyAdapterMiddleware
from forgecli.middleware.middleware_manager import MiddlewareManager
from forgecli.middleware.pipeline import MiddlewarePipeline
from forgecli.middleware.ponytail_adapter import PonytailAdapterMiddleware
from forgecli.middleware.registration import (
    get_registered_middleware_types,
    register_middleware_type,
    unregister_middleware_type,
)
from forgecli.observability.middleware import TelemetryMiddleware

__all__ = [

    "AuthenticationMiddleware",
    "CachingMiddleware",
    "CavemanAdapterMiddleware",
    "ConversationMiddleware",
    "DependencyGraphMiddleware",
    "GraphifyAdapterMiddleware",
    "GraphifyMiddleware",
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
    "PonytailAdapterMiddleware",
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

