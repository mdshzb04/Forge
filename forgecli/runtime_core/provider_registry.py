"""Provider registry for the Universal AI Runtime.

Maintains LLM driver adapters and queries capability configurations.
"""



from __future__ import annotations

import logging
import threading
from typing import Any

from forgecli.runtime_core.errors import ConfigurationError
from forgecli.runtime_core.interfaces import Provider

logger = logging.getLogger("forge.runtime_core.provider_registry")





class ProviderRegistry:

    """Manages registered Provider driver instances and queries their capability records."""



    def __init__(self) -> None:

        """Initialize the ProviderRegistry."""

        self._lock = threading.Lock()

        self._providers: dict[str, Provider] = {}

        self._default_provider_name: str | None = None



    def register_provider(self, name: str, provider: Provider) -> None:

        """Register a provider driver.

        Args:
            name: The unique key name for the provider.
            provider: An object implementing the Provider interface.

        Raises:
            ConfigurationError: If the provider is invalid or does not implement Provider.
        """

        if not isinstance(provider, Provider):

            raise ConfigurationError(

                f"Registration target for provider '{name}' must implement Provider, got {type(provider)}."

            )

        with self._lock:

            self._providers[name] = provider



            if self._default_provider_name is None:

                self._default_provider_name = name

            logger.info("Provider '%s' registered.", name)



    def remove_provider(self, name: str) -> None:

        """Unregister a provider driver.

        Args:
            name: The key name to remove.
        """

        with self._lock:

            self._providers.pop(name, None)

            if self._default_provider_name == name:



                self._default_provider_name = next(iter(self._providers.keys())) if self._providers else None

            logger.info("Provider '%s' removed.", name)



    def get_provider(self, name: str) -> Provider:

        """Resolve a provider driver by name.

        Args:
            name: The provider key name.

        Returns:
            The resolved Provider.

        Raises:
            ConfigurationError: If the provider name is not registered.
        """

        with self._lock:

            if name not in self._providers:

                raise ConfigurationError(f"Provider '{name}' is not registered.")

            return self._providers[name]



    def list_providers(self) -> list[str]:

        """List names of all registered providers.

        Returns:
            List of registered provider name strings.
        """

        with self._lock:

            return list(self._providers.keys())



    def default_provider(self) -> Provider | None:

        """Retrieve the default provider driver.

        Returns:
            The default Provider instance, or None if none registered.
        """

        with self._lock:

            if self._default_provider_name is None:

                return None

            return self._providers.get(self._default_provider_name)



    def set_default_provider(self, name: str) -> None:

        """Configure the default provider target.

        Args:
            name: The provider name to set as default.

        Raises:
            ConfigurationError: If the provider name is not registered.
        """

        with self._lock:

            if name not in self._providers:

                raise ConfigurationError(f"Cannot set unregistered provider '{name}' as default.")

            self._default_provider_name = name

            logger.info("Default provider updated to '%s'.", name)



    def capabilities(self, name: str) -> dict[str, Any]:

        """Query the capabilities map of a registered provider.

        Args:
            name: The provider name.

        Returns:
            A dictionary of capability mappings.
        """

        provider = self.get_provider(name)

        return provider.capabilities

