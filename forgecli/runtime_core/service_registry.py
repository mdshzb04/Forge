"""Service registry for the Universal AI Runtime.

Tracks managed components, supporting lazy initialization and hot swapping.
"""



from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from forgecli.runtime_core.errors import ConfigurationError
from forgecli.runtime_core.interfaces import Service

logger = logging.getLogger("forge.runtime_core.service_registry")





class ServiceRegistry:

    """Central registry for managed Services.

    Supports lazy initialization (instantiating services on first resolution),
    unregistering services, and hot-swapping active implementations thread-safely.
    """



    def __init__(self) -> None:

        """Initialize the ServiceRegistry."""

        self._lock = threading.Lock()



        self._registry: dict[str, Service | Callable[[], Service]] = {}



        self._instances: dict[str, Service] = {}



    def register(

        self,

        name: str,

        service: Service | Callable[[], Service],

        *,

        lazy: bool = True,

    ) -> None:

        """Register a service with the registry.

        Args:
            name: The lookup key name for the service.
            service: A Service instance or a callable factory returning a Service.
            lazy: If True, delay instantiation until resolved. Otherwise, instantiate immediately.

        Raises:
            ConfigurationError: If the service or factory does not conform to the Service interface.
        """

        with self._lock:

            if name in self._registry:

                raise ConfigurationError(f"Service '{name}' is already registered.")



            self._registry[name] = service



            if not lazy:



                self._resolve_locked(name)



    def unregister(self, name: str) -> None:

        """Remove a service from the registry.

        Args:
            name: The service name key to remove.
        """

        with self._lock:

            self._registry.pop(name, None)

            self._instances.pop(name, None)

            logger.info("Service '%s' unregistered.", name)



    def resolve(self, name: str) -> Service:

        """Resolve a service, instantiating it if registered lazily.

        Args:
            name: The key name of the service.

        Returns:
            The instantiated Service.

        Raises:
            ConfigurationError: If the service is not found or fails validation.
        """

        with self._lock:

            return self._resolve_locked(name)



    def exists(self, name: str) -> bool:

        """Check if a service is registered.

        Args:
            name: The key name.

        Returns:
            True if registered, False otherwise.
        """

        with self._lock:

            return name in self._registry



    def list_services(self) -> list[str]:

        """List names of all registered services.

        Returns:
            List of registered service name strings.
        """

        with self._lock:

            return list(self._registry.keys())



    def replace(self, name: str, new_service: Service | Callable[[], Service]) -> None:

        """Hot-swap a service implementation.

        Args:
            name: The service name key.
            new_service: The new Service instance or factory callback.
        """

        with self._lock:

            if name not in self._registry:

                raise ConfigurationError(f"Cannot replace unregistered service '{name}'.")





            self._registry[name] = new_service

            self._instances.pop(name, None)

            logger.info("Service '%s' implementation hot-swapped.", name)



    def clear(self) -> None:

        """Remove all registered services and clear cache instances."""

        with self._lock:

            self._registry.clear()

            self._instances.clear()

            logger.debug("ServiceRegistry cleared.")



    def _resolve_locked(self, name: str) -> Service:

        """Resolve service worker (caller must hold self._lock)."""

        if name not in self._registry:

            raise ConfigurationError(f"Service '{name}' is not registered.")



        if name in self._instances:

            return self._instances[name]



        target = self._registry[name]





        if isinstance(target, Service):

            self._instances[name] = target

            return target

        elif callable(target):

            try:

                service_instance = target()

            except Exception as exc:

                raise ConfigurationError(

                    f"Factory failed to construct service '{name}': {exc}"

                ) from exc



            if not isinstance(service_instance, Service):

                raise ConfigurationError(

                    f"Resolved object for '{name}' must implement Service interface, got {type(service_instance)}."

                )



            self._instances[name] = service_instance

            return service_instance

        else:

            raise ConfigurationError(

                f"Registered service '{name}' must be a Service instance or a callable, got {type(target)}."

            )

