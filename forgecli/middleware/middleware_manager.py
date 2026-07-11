"""Middleware manager for the Forge middleware engine.

Coordinates configuration, registrations, order validation, lifecycles, and reloading.
"""



from __future__ import annotations

import logging
import threading

from forgecli.middleware.base import Middleware
from forgecli.middleware.exceptions import MiddlewareRegistrationError
from forgecli.middleware.pipeline import MiddlewarePipeline
from forgecli.runtime_core.interfaces import LifecycleAware

logger = logging.getLogger("forge.middleware.manager")





class MiddlewareManager:

    """Manages the lifecycle, precedence rules, and reloading of pipeline middlewares."""



    def __init__(self, pipeline: MiddlewarePipeline | None = None) -> None:

        """Initialize the MiddlewareManager.

        Args:
            pipeline: The target MiddlewarePipeline to coordinate.
        """

        self._lock = threading.Lock()

        self._pipeline = pipeline or MiddlewarePipeline()



    @property

    def pipeline(self) -> MiddlewarePipeline:

        """Get the managed pipeline instance."""

        return self._pipeline



    def register(self, middleware: Middleware) -> None:

        """Register a middleware instance into the pipeline and validate order rules.

        Args:
            middleware: The middleware instance to register.

        Raises:
            MiddlewareRegistrationError: If precedence dependency rules are violated.
        """

        with self._lock:

            self._pipeline.add(middleware)

            try:

                self.validate_dependencies()

            except Exception as exc:

                self._pipeline.remove(middleware)

                raise MiddlewareRegistrationError(f"Failed to register middleware: {exc}") from exc



    def unregister(self, middleware: Middleware) -> None:

        """Unregister a middleware instance from the pipeline.

        Args:
            middleware: The middleware instance to remove.
        """

        with self._lock:

            self._pipeline.remove(middleware)



    def validate_dependencies(self) -> None:

        """Assert that the priority-sorted order of middlewares obeys dependencies.

        Raises:
            MiddlewareRegistrationError: If any run_before or run_after constraint is violated.
        """

        active_list = self._pipeline.list()

        class_to_idx = {type(mw): idx for idx, mw in enumerate(active_list)}



        for idx, mw in enumerate(active_list):

            mw_type = type(mw)





            for after_cls in mw.run_after:

                if after_cls in class_to_idx:

                    after_idx = class_to_idx[after_cls]

                    if after_idx > idx:

                        raise MiddlewareRegistrationError(

                            f"Precedence violation: '{mw_type.__name__}' must execute after "

                            f"'{after_cls.__name__}', but '{after_cls.__name__}' has a lower priority."

                        )





            for before_cls in mw.run_before:

                if before_cls in class_to_idx:

                    before_idx = class_to_idx[before_cls]

                    if before_idx < idx:

                        raise MiddlewareRegistrationError(

                            f"Precedence violation: '{mw_type.__name__}' must execute before "

                            f"'{before_cls.__name__}', but '{before_cls.__name__}' has a higher priority."

                        )



    def hot_reload(self, new_middlewares: list[Middleware]) -> None:

        """Clear existing pipeline elements and reload new middleware configurations.

        Args:
            new_middlewares: List of new middleware instances to install.

        Raises:
            MiddlewareRegistrationError: If the new configuration fails validation.
        """

        with self._lock:

            old_list = list(self._pipeline._middlewares)

            self._pipeline._middlewares.clear()



            try:

                for mw in new_middlewares:

                    self._pipeline.add(mw)

                self.validate_dependencies()

            except Exception as exc:



                self._pipeline._middlewares = old_list

                logger.error("Hot reload failed, rolling back to previous state: %s", exc)

                raise MiddlewareRegistrationError(f"Hot reload aborted: {exc}") from exc



            logger.info("Hot reload completed. Registered %d middlewares.", len(new_middlewares))



    def on_startup(self) -> None:

        """Trigger startup hooks on all LifecycleAware middlewares."""

        with self._lock:

            for mw in self._pipeline.list():

                if isinstance(mw, LifecycleAware):

                    try:

                        mw.on_before_start()

                        mw.on_after_start()

                    except Exception as exc:

                        logger.error("Error executing startup hook on '%s': %s", type(mw).__name__, exc)



    def on_shutdown(self) -> None:

        """Trigger shutdown hooks on all LifecycleAware middlewares."""

        with self._lock:

            for mw in self._pipeline.list():

                if isinstance(mw, LifecycleAware):

                    try:

                        mw.on_before_shutdown()

                        mw.on_after_shutdown()

                    except Exception as exc:

                        logger.error("Error executing shutdown hook on '%s': %s", type(mw).__name__, exc)

