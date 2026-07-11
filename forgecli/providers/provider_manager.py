"""Manager coordinating provider lifecycles, health checks, and event broadcasts."""



from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from forgecli.providers.health import ProviderHealthState
from forgecli.providers.provider_events import (
    ProviderHealthChanged,
    ProviderRegistered,
    ProviderStarted,
    ProviderStopped,
)

if TYPE_CHECKING:

    from forgecli.providers.base import Provider
    from forgecli.providers.provider_registry import ProviderRegistry
    from forgecli.runtime_core.events import EventBus



logger = logging.getLogger("forge.providers.manager")





class ProviderManager:

    """Manages lifecycles, health heartbeat triggers, and event publishing for all providers."""



    def __init__(self, registry: ProviderRegistry, event_bus: EventBus) -> None:

        """Initialize the ProviderManager.

        Args:
            registry: Provider registry.
            event_bus: System event bus.
        """

        self._registry = registry

        self._event_bus = event_bus

        self._last_known_health: dict[str, ProviderHealthState] = {}



    async def register_provider(self, name: str, provider: Provider) -> None:

        """Register a provider and publish register event.

        Args:
            name: Lowercase provider name.
            provider: Provider instance.
        """

        name_lower = name.lower()

        self._registry.register(name_lower, provider)

        self._last_known_health[name_lower] = ProviderHealthState.UNKNOWN

        self._event_bus.publish(

            ProviderRegistered(provider_name=name_lower, metadata=provider.metadata())

        )



    async def unregister_provider(self, name: str) -> None:

        """Unregister a provider and cleanup.

        Args:
            name: Provider name.
        """

        name_lower = name.lower()

        if self._registry.exists(name_lower):

            provider = self._registry.resolve(name_lower)

            await provider.shutdown()

            self._registry.unregister(name_lower)

            self._last_known_health.pop(name_lower, None)

            self._event_bus.publish(ProviderStopped(provider_name=name_lower))



    async def initialize_all(self) -> None:

        """Initialize all registered providers and emit start events."""

        for name in self._registry.list():

            provider = self._registry.resolve(name)

            await provider.initialize()

            self._event_bus.publish(ProviderStarted(provider_name=name))



    async def shutdown_all(self) -> None:

        """Shutdown all registered providers and emit stop events."""

        for name in self._registry.list():

            provider = self._registry.resolve(name)

            await provider.shutdown()

            self._event_bus.publish(ProviderStopped(provider_name=name))



    async def check_health(self) -> None:

        """Perform a heartbeat check across all providers and publish state changes."""

        for name in self._registry.list():

            provider = self._registry.resolve(name)

            health_info = await provider.health()



            old_state = self._last_known_health.get(name, ProviderHealthState.UNKNOWN)

            new_state = health_info.state



            if old_state != new_state:

                self._last_known_health[name] = new_state

                self._event_bus.publish(

                    ProviderHealthChanged(

                        provider_name=name,

                        old_state=old_state,

                        new_state=new_state,

                        details=health_info.details,

                    )

                )

