"""Abstract base classes and shared data types for AI providers."""



from __future__ import annotations

import os
from abc import ABC
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from forgecli.core.errors import ProviderError
from forgecli.providers.health import ProviderHealth, ProviderHealthState
from forgecli.providers.provider_capabilities import Capability, ProviderCapabilities
from forgecli.providers.provider_metadata import ProviderMetadata
from forgecli.runtime_core.response import AIResponse

if TYPE_CHECKING:

    from forgecli.providers.provider_context import ProviderContext





class Role(str, Enum):

    """A role in a chat conversation."""



    SYSTEM = "system"

    USER = "user"

    ASSISTANT = "assistant"

    TOOL = "tool"





@dataclass(frozen=True)

class ChatMessage:

    """A single message in a chat conversation."""



    role: Role

    content: str

    name: str | None = None

    tool_call_id: str | None = None

    extra: dict[str, Any] = field(default_factory=dict)





class ChatRequest(BaseModel):

    """Provider-agnostic chat completion request."""



    model_config = ConfigDict(extra="allow")



    model: str | None = None

    messages: list[ChatMessage] = Field(default_factory=list)

    temperature: float | None = None

    max_tokens: int | None = None

    top_p: float | None = None

    stop: list[str] | None = None

    tools: list[dict[str, Any]] | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)





class ChatResponse(BaseModel):

    """Provider-agnostic chat completion response."""



    model_config = ConfigDict(extra="allow")



    model: str

    message: ChatMessage

    finish_reason: str | None = None

    prompt_tokens: int = 0

    completion_tokens: int = 0

    total_tokens: int = 0

    raw: dict[str, Any] = Field(default_factory=dict)





@dataclass(frozen=True)

class StreamChunk:

    """A piece of a streamed chat response."""



    delta: str

    finish_reason: str | None = None

    raw: dict[str, Any] = field(default_factory=dict)





class EmbeddingRequest(BaseModel):

    """Provider-agnostic embedding request."""



    model_config = ConfigDict(extra="allow")



    model: str | None = None

    inputs: list[str] = Field(default_factory=list)





class EmbeddingResponse(BaseModel):

    """Provider-agnostic embedding response."""



    model_config = ConfigDict(extra="allow")



    model: str

    vectors: list[list[float]] = Field(default_factory=list)

    prompt_tokens: int = 0

    total_tokens: int = 0





@dataclass(frozen=True)

class ModelInfo:

    """Metadata describing a model exposed by a provider."""



    id: str

    name: str | None = None

    context_window: int | None = None

    supports_tools: bool = False

    supports_vision: bool = False

    extra: dict[str, Any] = field(default_factory=dict)





TConfig = TypeVar("TConfig")





class Provider(ABC, Generic[TConfig]):  # pragma: no cover

    """Base class for AI providers.

    Concrete providers should subclass :class:`Provider` with a concrete
    ``TConfig`` type and implement the abstract methods below.
    """



    name: ClassVar[str] = "abstract"



    def __init__(self, config: TConfig | None = None) -> None:

        self._config = config



    @property

    def config(self) -> TConfig:

        return self._config  # type: ignore[return-value]





    async def chat(self, request: ChatRequest) -> ChatResponse:

        """Send ``request`` and return a :class:`ChatResponse`."""

        raise NotImplementedError



    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:

        """Compute embeddings for ``request.inputs``."""

        raise NotImplementedError



    async def list_models(self) -> list[ModelInfo]:

        """Return the list of models supported by this provider."""

        return []



    def validate(self) -> None:

        """Hook for pre-flight checks (API key, base URL, etc)."""

        return None



    @staticmethod

    def resolve_api_key(env_var: str | None) -> str | None:

        """Return the API key from ``env_var`` or ``None``."""

        if not env_var:

            return None

        return os.environ.get(env_var)





    async def initialize(self) -> None:

        """Initialize connection or configure internal clients."""

        pass



    async def shutdown(self) -> None:

        """Shutdown connection and cleanup client resources."""

        pass



    async def health(self) -> ProviderHealth:

        """Perform a heartbeat check and return current health status."""

        return ProviderHealth(state=ProviderHealthState.HEALTHY)



    async def send(self, context: ProviderContext) -> AIResponse:

        """Send a non-streaming completion request."""

        raise NotImplementedError



    async def stream(self, request_or_context: Any) -> AsyncIterator[Any]:

        """Unified stream method.

        Supports legacy ChatRequest -> StreamChunk streaming and Phase 4 ProviderContext -> AIResponse streaming.
        """

        from forgecli.providers.provider_context import ProviderContext

        if isinstance(request_or_context, ProviderContext):

            resp = await self.send(request_or_context)

            yield resp

        else:

            response = await self.chat(request_or_context)

            yield StreamChunk(

                delta=response.message.content,

                finish_reason=response.finish_reason,

                raw=response.raw,

            )



    async def cancel(self, request_id: str) -> None:

        """Cancel a running request by ID."""

        pass



    def supports_tools(self) -> bool:

        """Whether provider supports tool invocation."""

        return False



    def supports_streaming(self) -> bool:

        """Whether provider supports output token streaming."""

        return False



    def supports_images(self) -> bool:

        """Whether provider supports multimodal image inputs."""

        return False



    def supports_reasoning(self) -> bool:

        """Whether provider supports thinking/reasoning outputs."""

        return False



    def supports_json(self) -> bool:

        """Whether provider supports JSON structural output constraints."""

        return False



    def supports_embeddings(self) -> bool:

        """Whether provider supports vector embeddings generation."""

        return False



    def supports_mcp(self) -> bool:

        """Whether provider supports Model Context Protocol interactions."""

        return False



    def estimate_context_window(self, model: str) -> int:

        """Estimate the context token window limit for a model name."""

        return 4096



    def metadata(self) -> ProviderMetadata:

        """Get static metadata for the provider configuration."""

        return ProviderMetadata(

            name=self.name,

            version="1.0.0",

            default_model="default",

            supported_models=[],

            context_windows={},

        )





class ProviderRegistry:

    """In-memory registry of provider classes keyed by name."""



    def __init__(self) -> None:

        self._providers: dict[str, type[Provider[Any]]] = {}



    def register(self, name: str, provider_cls: type[Provider[Any]]) -> None:

        if not issubclass(provider_cls, Provider):

            raise ProviderError(f"{provider_cls!r} must subclass forgecli.providers.Provider")

        if name in self._providers and self._providers[name] is not provider_cls:

            raise ProviderError(f"Provider {name!r} already registered")

        self._providers[name] = provider_cls



    def unregister(self, name: str) -> None:

        self._providers.pop(name, None)



    def create(self, name: str, config: Any) -> Provider[Any]:

        cls = self._providers.get(name)

        if cls is None:

            raise ProviderError(f"Unknown provider: {name!r}")

        return cls(config)



    def get(self, name: str) -> type[Provider[Any]]:

        cls = self._providers.get(name)

        if cls is None:

            raise ProviderError(f"Unknown provider: {name!r}")

        return cls



    def names(self) -> list[str]:

        return sorted(self._providers)



    def has(self, name: str) -> bool:

        return name in self._providers







default_registry = ProviderRegistry()





def iter_chunked(items: list[str], size: int) -> Iterator[list[str]]:

    """Yield ``items`` in fixed-size chunks; useful for batched embedding calls."""

    if size <= 0:

        raise ValueError("chunk size must be positive")

    for i in range(0, len(items), size):

        yield items[i : i + size]









class BaseProvider(Provider[Any]):

    """A generic base provider that implements abstract methods with placeholder logic."""



    def __init__(self, metadata_info: ProviderMetadata, capabilities_info: ProviderCapabilities) -> None:

        super().__init__()

        self._metadata = metadata_info

        self._capabilities = capabilities_info

        self._health_state = ProviderHealth(state=ProviderHealthState.HEALTHY)

        self._initialized = False



    async def initialize(self) -> None:

        self._initialized = True



    async def shutdown(self) -> None:

        self._initialized = False



    async def health(self) -> ProviderHealth:

        return self._health_state



    async def send(self, context: ProviderContext) -> AIResponse:

        return AIResponse(

            response_id=f"resp-{self._metadata.name}-{context.request_context.execution_id}",

            request_id=context.request_context.ai_request.request_id,

            content=f"Mock response from {self._metadata.name} using {context.model}",

            finish_reason="stop",

            latency_ms=10.0,

        )



    async def stream(self, request_or_context: Any) -> AsyncIterator[Any]:

        from forgecli.providers.provider_context import ProviderContext

        if isinstance(request_or_context, ProviderContext):

            yield AIResponse(

                response_id=f"resp-{self._metadata.name}-{request_or_context.request_context.execution_id}",

                request_id=request_or_context.request_context.ai_request.request_id,

                content=f"Mock stream chunk from {self._metadata.name} using {request_or_context.model}",

                finish_reason="stop",

                latency_ms=10.0,

            )

        else:

            async for chunk in super().stream(request_or_context):

                yield chunk



    async def cancel(self, request_id: str) -> None:

        pass



    def supports_tools(self) -> bool:

        return self._capabilities.supports(Capability.TOOL_CALLING)



    def supports_streaming(self) -> bool:

        return self._capabilities.supports(Capability.STREAMING)



    def supports_images(self) -> bool:

        return self._capabilities.supports(Capability.VISION)



    def supports_reasoning(self) -> bool:

        return self._capabilities.supports(Capability.REASONING)



    def supports_json(self) -> bool:

        return self._capabilities.supports(Capability.JSON_MODE)



    def supports_embeddings(self) -> bool:

        return self._capabilities.supports(Capability.EMBEDDINGS)



    def supports_mcp(self) -> bool:

        return True



    def estimate_context_window(self, model: str) -> int:

        return self._metadata.context_windows.get(model, 4096)



    def metadata(self) -> ProviderMetadata:

        return self._metadata





class OpenAIProvider(BaseProvider):

    """Placeholder driver implementation for OpenAI."""



    def __init__(self) -> None:

        super().__init__(

            ProviderMetadata(

                name="openai",

                version="1.0.0",

                default_model="gpt-4o",

                supported_models=["gpt-4o", "gpt-4o-mini", "o1-preview"],

                context_windows={"gpt-4o": 128000, "gpt-4o-mini": 128000, "o1-preview": 128000},

            ),

            ProviderCapabilities(

                supported_capabilities={

                    Capability.TOOL_CALLING,

                    Capability.VISION,

                    Capability.REASONING,

                    Capability.STREAMING,

                    Capability.JSON_MODE,

                    Capability.EMBEDDINGS,

                    Capability.STRUCTURED_OUTPUTS,

                    Capability.BATCH,

                    Capability.PROMPT_CACHING,

                }

            ),

        )





class AnthropicProvider(BaseProvider):

    """Placeholder driver implementation for Anthropic."""



    def __init__(self) -> None:

        super().__init__(

            ProviderMetadata(

                name="anthropic",

                version="1.0.0",

                default_model="claude-3-5-sonnet",

                supported_models=["claude-3-5-sonnet", "claude-3-haiku", "claude-3-opus"],

                context_windows={"claude-3-5-sonnet": 200000, "claude-3-haiku": 200000, "claude-3-opus": 200000},

            ),

            ProviderCapabilities(

                supported_capabilities={

                    Capability.TOOL_CALLING,

                    Capability.VISION,

                    Capability.STREAMING,

                    Capability.COMPUTER_USE,

                    Capability.PROMPT_CACHING,

                }

            ),

        )





class GeminiProvider(BaseProvider):

    """Placeholder driver implementation for Google Gemini."""



    def __init__(self) -> None:

        super().__init__(

            ProviderMetadata(

                name="gemini",

                version="1.0.0",

                default_model="gemini-1.5-pro",

                supported_models=["gemini-1.5-pro", "gemini-1.5-flash"],

                context_windows={"gemini-1.5-pro": 2000000, "gemini-1.5-flash": 1000000},

            ),

            ProviderCapabilities(

                supported_capabilities={

                    Capability.TOOL_CALLING,

                    Capability.VISION,

                    Capability.STREAMING,

                    Capability.AUDIO,

                    Capability.VIDEO,

                    Capability.LONG_CONTEXT,

                    Capability.CONTEXT_CACHING,

                }

            ),

        )





class OpenRouterProvider(BaseProvider):

    """Placeholder driver implementation for OpenRouter."""



    def __init__(self) -> None:

        super().__init__(

            ProviderMetadata(

                name="openrouter",

                version="1.0.0",

                default_model="openrouter-default",

                supported_models=["openrouter-default"],

                context_windows={"openrouter-default": 8192},

            ),

            ProviderCapabilities(

                supported_capabilities={

                    Capability.TOOL_CALLING,

                    Capability.VISION,

                    Capability.STREAMING,

                }

            ),

        )





class GroqProvider(BaseProvider):

    """Placeholder driver implementation for Groq."""



    def __init__(self) -> None:

        super().__init__(

            ProviderMetadata(

                name="groq",

                version="1.0.0",

                default_model="llama-3.1-70b-versatile",

                supported_models=["llama-3.1-70b-versatile", "mixtral-8x7b-32768"],

                context_windows={"llama-3.1-70b-versatile": 131072, "mixtral-8x7b-32768": 32768},

            ),

            ProviderCapabilities(

                supported_capabilities={

                    Capability.TOOL_CALLING,

                    Capability.STREAMING,

                    Capability.JSON_MODE,

                }

            ),

        )





class DeepSeekProvider(BaseProvider):

    """Placeholder driver implementation for DeepSeek."""



    def __init__(self) -> None:

        super().__init__(

            ProviderMetadata(

                name="deepseek",

                version="1.0.0",

                default_model="deepseek-chat",

                supported_models=["deepseek-chat", "deepseek-coder"],

                context_windows={"deepseek-chat": 64000, "deepseek-coder": 64000},

            ),

            ProviderCapabilities(

                supported_capabilities={

                    Capability.TOOL_CALLING,

                    Capability.STREAMING,

                    Capability.REASONING,

                    Capability.JSON_MODE,

                }

            ),

        )





class GLMProvider(BaseProvider):

    """Placeholder driver implementation for Zhipu GLM."""



    def __init__(self) -> None:

        super().__init__(

            ProviderMetadata(

                name="glm",

                version="1.0.0",

                default_model="glm-4",

                supported_models=["glm-4"],

                context_windows={"glm-4": 128000},

            ),

            ProviderCapabilities(

                supported_capabilities={

                    Capability.TOOL_CALLING,

                    Capability.STREAMING,

                    Capability.VISION,

                }

            ),

        )





class QwenProvider(BaseProvider):

    """Placeholder driver implementation for Alibaba Qwen."""



    def __init__(self) -> None:

        super().__init__(

            ProviderMetadata(

                name="qwen",

                version="1.0.0",

                default_model="qwen-max",

                supported_models=["qwen-max", "qwen-plus"],

                context_windows={"qwen-max": 32000, "qwen-plus": 32000},

            ),

            ProviderCapabilities(

                supported_capabilities={

                    Capability.TOOL_CALLING,

                    Capability.VISION,

                    Capability.STREAMING,

                }

            ),

        )





class KimiProvider(BaseProvider):

    """Placeholder driver implementation for Moonshot Kimi."""



    def __init__(self) -> None:

        super().__init__(

            ProviderMetadata(

                name="kimi",

                version="1.0.0",

                default_model="moonshot-v1-8k",

                supported_models=["moonshot-v1-8k", "moonshot-v1-32k"],

                context_windows={"moonshot-v1-8k": 8192, "moonshot-v1-32k": 32768},

            ),

            ProviderCapabilities(

                supported_capabilities={

                    Capability.TOOL_CALLING,

                    Capability.STREAMING,

                }

            ),

        )





class OllamaProvider(BaseProvider):

    """Placeholder driver implementation for local Ollama."""



    def __init__(self) -> None:

        super().__init__(

            ProviderMetadata(

                name="ollama",

                version="1.0.0",

                default_model="llama3",

                supported_models=["llama3", "mistral"],

                context_windows={"llama3": 8192, "mistral": 8192},

            ),

            ProviderCapabilities(

                supported_capabilities={

                    Capability.TOOL_CALLING,

                    Capability.STREAMING,

                    Capability.EMBEDDINGS,

                }

            ),

        )





class LMStudioProvider(BaseProvider):

    """Placeholder driver implementation for LM Studio."""



    def __init__(self) -> None:

        super().__init__(

            ProviderMetadata(

                name="lmstudio",

                version="1.0.0",

                default_model="lmstudio-default",

                supported_models=["lmstudio-default"],

                context_windows={"lmstudio-default": 8192},

            ),

            ProviderCapabilities(

                supported_capabilities={

                    Capability.STREAMING,

                }

            ),

        )

