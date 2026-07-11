"""Registry for mapping, storing, and fetching provider driver clients."""



from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from forgecli.providers.exceptions import ProviderNotFoundError, ProviderRegistrationError

if TYPE_CHECKING:

    from forgecli.providers.base import Provider
    from forgecli.providers.health import ProviderHealth
    from forgecli.providers.provider_metadata import ProviderMetadata





class ProviderRegistry:

    """Thread-safe registry containing active provider client drivers."""



    def __init__(self) -> None:

        """Initialize the ProviderRegistry."""

        self._lock = threading.Lock()

        self._providers: dict[str, Provider] = {}



    def register(self, name: str, provider: Provider) -> None:

        """Register a provider instance under a unique name identifier.

        Args:
            name: Case-insensitive unique name identifier (e.g. 'openai').
            provider: The provider instance.

        Raises:
            ProviderRegistrationError: If name is empty or duplicate.
        """

        if not name:

            raise ProviderRegistrationError("Provider name cannot be empty.")



        normalized_name = name.lower()

        with self._lock:

            if normalized_name in self._providers:

                raise ProviderRegistrationError(f"Provider '{normalized_name}' is already registered.")

            self._providers[normalized_name] = provider



    def unregister(self, name: str) -> None:

        """Unregister a provider instance.

        Args:
            name: Unique name identifier.

        Raises:
            ProviderNotFoundError: If the name identifier does not exist.
        """

        normalized_name = name.lower()

        with self._lock:

            if normalized_name not in self._providers:

                raise ProviderNotFoundError(f"Provider '{normalized_name}' is not registered.")

            del self._providers[normalized_name]



    def exists(self, name: str) -> bool:

        """Check if a provider identifier exists in the registry.

        Args:
            name: Unique name identifier.
        """

        return name.lower() in self._providers



    def resolve(self, name: str) -> Provider:

        """Resolve a registered provider instance.

        Args:
            name: Unique name identifier.

        Raises:
            ProviderNotFoundError: If the name identifier does not exist.
        """

        normalized_name = name.lower()

        with self._lock:

            if normalized_name not in self._providers:

                raise ProviderNotFoundError(f"Provider '{normalized_name}' is not registered.")

            return self._providers[normalized_name]



    def list(self) -> list[str]:

        """List names of all registered providers."""

        with self._lock:

            return list(self._providers.keys())



    async def reload(self) -> None:

        """Reload all registered providers by calling shutdown and initialize."""

        with self._lock:

            providers = list(self._providers.values())

        for provider in providers:

            await provider.shutdown()

            await provider.initialize()



    async def health(self) -> dict[str, ProviderHealth]:

        """Collect current health status checks from all registered providers."""

        with self._lock:

            providers = list(self._providers.items())



        health_dict = {}

        for name, provider in providers:

            health_dict[name] = await provider.health()

        return health_dict



    def metadata(self) -> dict[str, ProviderMetadata]:

        """Collect static metadata info from all registered providers."""

        with self._lock:

            providers = list(self._providers.items())



        return {name: provider.metadata() for name, provider in providers}

