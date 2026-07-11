"""Middleware registration registry for the Forge middleware engine.

Allows plugins to extend the pipeline capabilities by registering middleware types dynamically.
"""



from __future__ import annotations

import logging
import threading

from forgecli.middleware.base import Middleware
from forgecli.middleware.exceptions import MiddlewareRegistrationError

logger = logging.getLogger("forge.middleware.registration")



_lock = threading.Lock()



_registered_middlewares: dict[str, type[Middleware]] = {}





def register_middleware_type(name: str, cls: type[Middleware]) -> None:

    """Register a custom middleware class to make it queryable.

    Args:
        name: A unique lookup key for this middleware type.
        cls: A class inheriting from Middleware.

    Raises:
        MiddlewareRegistrationError: If input class is invalid or name is already registered.
    """

    if not issubclass(cls, Middleware):

        raise MiddlewareRegistrationError(

            f"Cannot register '{name}': class must derive from Middleware, got {cls}."

        )



    with _lock:

        if name in _registered_middlewares:

            raise MiddlewareRegistrationError(

                f"Middleware type name '{name}' is already registered to {_registered_middlewares[name]}."

            )

        _registered_middlewares[name] = cls

        logger.info("Registered custom middleware type: %s (%s)", name, cls.__name__)





def unregister_middleware_type(name: str) -> None:

    """Remove a custom middleware type registration.

    Args:
        name: Registration lookup name.
    """

    with _lock:

        _registered_middlewares.pop(name, None)

        logger.debug("Unregistered custom middleware type: %s", name)





def get_registered_middleware_types() -> dict[str, type[Middleware]]:

    """Fetch copies of all registered custom middleware types.

    Returns:
        Dictionary map of registered names to classes.
    """

    with _lock:

        return dict(_registered_middlewares)

