"""Router module for resolving models, aliases, and fallbacks."""



from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from forgecli.providers.exceptions import ProviderExecutionError, ProviderNotFoundError
from forgecli.providers.health import ProviderHealthState

if TYPE_CHECKING:

    from forgecli.providers.base import Provider
    from forgecli.providers.provider_registry import ProviderRegistry



logger = logging.getLogger("forge.providers.router")





class ProviderRouter:

    """Routes execution requests based on configuration, model queries, health, and fallbacks."""



    def __init__(

        self,

        registry: ProviderRegistry,

        default_provider_name: str = "openai",

        default_model_name: str = "gpt-4o",

    ) -> None:

        """Initialize the ProviderRouter.

        Args:
            registry: Provider registry.
            default_provider_name: Default provider name.
            default_model_name: Default model name.
        """

        self._registry = registry

        self._default_provider = default_provider_name.lower()

        self._default_model = default_model_name

        self._aliases: dict[str, tuple[str, str]] = {}

        self._fallbacks: dict[str, list[str]] = {}



    def register_alias(self, alias: str, provider: str, model: str) -> None:

        """Register a model alias mapping.

        Args:
            alias: The alias name (e.g. 'smart-model').
            provider: Target provider name (e.g. 'openai').
            model: Target model name (e.g. 'gpt-4o').
        """

        self._aliases[alias.lower()] = (provider.lower(), model)



    def register_fallback(self, provider: str, fallbacks: list[str]) -> None:

        """Register fallback sequence for a provider.

        Args:
            provider: Name of the primary provider.
            fallbacks: Ordered list of fallback provider names.
        """

        self._fallbacks[provider.lower()] = [f.lower() for f in fallbacks]



    def resolve_provider_and_model(self, model_query: str | None) -> tuple[Provider, str]:

        """Resolve the target Provider instance and concrete model name from a query string.

        Args:
            model_query: An alias, model name, or provider:model structured format.
        """

        if not model_query:

            primary_provider = self._registry.resolve(self._default_provider)

            return primary_provider, self._default_model



        query_lower = model_query.lower()





        if query_lower in self._aliases:

            prov_name, concrete_model = self._aliases[query_lower]

            return self._registry.resolve(prov_name), concrete_model





        if ":" in model_query:

            prov_part, model_part = model_query.split(":", 1)

            prov_part_lower = prov_part.lower()

            if self._registry.exists(prov_part_lower):

                return self._registry.resolve(prov_part_lower), model_part





        for name in self._registry.list():

            provider = self._registry.resolve(name)

            meta = provider.metadata()

            for m in meta.supported_models:

                if m.lower() == query_lower:

                    return provider, m





        primary_provider = self._registry.resolve(self._default_provider)

        return primary_provider, model_query



    async def get_healthy_provider(self, provider_name: str) -> Provider:

        """Get the specified provider, or select a healthy fallback if unavailable.

        Args:
            provider_name: The name of the desired provider.
        """

        prov_name_lower = provider_name.lower()

        if not self._registry.exists(prov_name_lower):

            raise ProviderNotFoundError(f"Provider '{provider_name}' not found.")





        provider = self._registry.resolve(prov_name_lower)

        health_status = await provider.health()

        if health_status.state in (ProviderHealthState.HEALTHY, ProviderHealthState.DEGRADED):

            return provider





        logger.warning(

            "Primary provider '%s' is unhealthy (%s). Attempting fallbacks...",

            provider_name,

            health_status.state,

        )

        fallbacks_list = self._fallbacks.get(prov_name_lower, [])

        for fb_name in fallbacks_list:

            if self._registry.exists(fb_name):

                fb_provider = self._registry.resolve(fb_name)

                fb_health = await fb_provider.health()

                if fb_health.state in (ProviderHealthState.HEALTHY, ProviderHealthState.DEGRADED):

                    logger.info("Routing request to fallback provider '%s'.", fb_name)

                    return fb_provider





        raise ProviderExecutionError(

            f"Primary provider '{provider_name}' and all fallbacks are unhealthy/unavailable."

        )



    async def route_request(self, model_query: str | None) -> tuple[Provider, str]:

        """Resolve a healthy provider and model name combination for a request.

        Args:
            model_query: The model string.
        """

        target_provider, resolved_model = self.resolve_provider_and_model(model_query)

        provider_name = target_provider.metadata().name



        selected_provider = await self.get_healthy_provider(provider_name)



        if selected_provider != target_provider:

            resolved_model = selected_provider.metadata().default_model



        return selected_provider, resolved_model

