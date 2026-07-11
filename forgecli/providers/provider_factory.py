"""Factory to resolve provider instances from the dependency injection container."""



from __future__ import annotations

from typing import TYPE_CHECKING

from forgecli.providers.base import (
    AnthropicProvider,
    DeepSeekProvider,
    GeminiProvider,
    GLMProvider,
    GroqProvider,
    KimiProvider,
    LMStudioProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenRouterProvider,
    QwenProvider,
)
from forgecli.providers.exceptions import ProviderNotFoundError
from forgecli.runtime_core.container import Lifetime

if TYPE_CHECKING:

    from forgecli.providers.base import Provider
    from forgecli.runtime_core.container import Container





class ProviderFactory:

    """Factory to construct provider instances using the DI container."""



    def __init__(self, container: Container) -> None:

        """Initialize the ProviderFactory.

        Args:
            container: The DI Container instance.
        """

        self._container = container

        self._register_default_providers()



    def _register_default_providers(self) -> None:

        """Register all default placeholder providers in the container namespace."""

        providers_mapping = {

            "openai": OpenAIProvider,

            "anthropic": AnthropicProvider,

            "gemini": GeminiProvider,

            "openrouter": OpenRouterProvider,

            "groq": GroqProvider,

            "deepseek": DeepSeekProvider,

            "glm": GLMProvider,

            "qwen": QwenProvider,

            "kimi": KimiProvider,

            "ollama": OllamaProvider,

            "lmstudio": LMStudioProvider,

        }



        for cls in providers_mapping.values():

            try:



                self._container.register(cls, cls, lifetime=Lifetime.SINGLETON)

            except Exception:  # pragma: no cover



                pass



    def create(self, provider_type: type[Provider]) -> Provider:

        """Create or resolve an instance of the provider class from the DI container.

        Args:
            provider_type: The class type of the provider to construct.
        """

        from forgecli.providers.base import Provider

        if provider_type is Provider:

            raise ProviderNotFoundError("Cannot instantiate the base Provider class directly.")

        try:

            return self._container.resolve(provider_type)

        except Exception as exc:

            raise ProviderNotFoundError(

                f"Failed to instantiate provider class '{provider_type.__name__}' through container: {exc}"

            ) from exc



    def create_by_name(self, name: str) -> Provider:

        """Create or resolve an instance of a provider by its name identifier.

        Args:
            name: The lowercase name identifier (e.g. 'openai').
        """

        providers_mapping = {

            "openai": OpenAIProvider,

            "anthropic": AnthropicProvider,

            "gemini": GeminiProvider,

            "openrouter": OpenRouterProvider,

            "groq": GroqProvider,

            "deepseek": DeepSeekProvider,

            "glm": GLMProvider,

            "qwen": QwenProvider,

            "kimi": KimiProvider,

            "ollama": OllamaProvider,

            "lmstudio": LMStudioProvider,

        }

        normalized_name = name.lower()

        if normalized_name not in providers_mapping:

            raise ProviderNotFoundError(f"Unknown provider name identifier '{name}'.")



        return self.create(providers_mapping[normalized_name])

