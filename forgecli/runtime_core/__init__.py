"""Forge Core Runtime package.

Provides the foundational definitions for requests, responses, configurations,
dependencies, service registries, lifecycles, and event dispatchers.
"""



from __future__ import annotations

from forgecli.runtime_core.config_manager import ConfigurationManager
from forgecli.runtime_core.container import Container, Lifetime
from forgecli.runtime_core.context import CancellationToken, RuntimeContext
from forgecli.runtime_core.errors import (
    ConfigurationError,
    ForgeError,
    PipelineError,
    PluginError,
    PolicyViolationError,
    ProviderError,
    SessionError,
)
from forgecli.runtime_core.events import EventBus, SystemEvent
from forgecli.runtime_core.factory import RuntimeFactory
from forgecli.runtime_core.interfaces import (
    ContextAware,
    EventHandler,
    Factory,
    LifecycleAware,
    Middleware,
    Plugin,
    Provider,
    Service,
)
from forgecli.runtime_core.lifecycle import LifecycleManager
from forgecli.runtime_core.provider_registry import ProviderRegistry
from forgecli.runtime_core.request import AIRequest, FileContext
from forgecli.runtime_core.response import AIResponse, StreamingChunk
from forgecli.runtime_core.service_registry import ServiceRegistry

__all__ = [

    "AIRequest",

    "AIResponse",

    "CancellationToken",

    "ConfigurationError",

    "ConfigurationManager",

    "Container",

    "ContextAware",

    "EventBus",

    "EventHandler",

    "Factory",

    "FileContext",

    "ForgeError",

    "LifecycleAware",

    "LifecycleManager",

    "Lifetime",

    "Middleware",

    "PipelineError",

    "Plugin",

    "PluginError",

    "PolicyViolationError",

    "Provider",

    "ProviderError",

    "ProviderRegistry",

    "RuntimeContext",

    "RuntimeFactory",

    "Service",

    "ServiceRegistry",

    "SessionError",

    "StreamingChunk",

    "SystemEvent",

]

