"""Lifecycle management for the Universal AI Runtime.

Coordinates startup, shutdown, and reload cycles of the runtime services.
"""



from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from forgecli.runtime_core.interfaces import LifecycleAware

logger = logging.getLogger("forge.runtime_core.lifecycle")





class LifecycleManager:

    """Coordinates lifecycle transitions (boot, reload, shutdown) for the runtime.

    Allows services implementing LifecycleAware or individual callback hooks to
    be executed in correct precedence orders.
    """



    def __init__(self) -> None:

        """Initialize the LifecycleManager."""

        self._lock = threading.Lock()

        self._components: list[LifecycleAware] = []

        self._before_start: list[Callable[[], None]] = []

        self._after_start: list[Callable[[], None]] = []

        self._before_shutdown: list[Callable[[], None]] = []

        self._after_shutdown: list[Callable[[], None]] = []

        self._is_running = False



    def register_component(self, component: LifecycleAware) -> None:

        """Register a component to receive lifecycle notifications.

        Args:
            component: The component implementing LifecycleAware.
        """

        with self._lock:

            if component not in self._components:

                self._components.append(component)

                logger.debug("Component '%s' registered for lifecycle notifications.", component)



    def unregister_component(self, component: LifecycleAware) -> None:

        """Unregister a component from lifecycle notifications.

        Args:
            component: The component to remove.
        """

        with self._lock:

            if component in self._components:

                self._components.remove(component)

                logger.debug("Component '%s' unregistered from lifecycle notifications.", component)



    def register_before_start(self, callback: Callable[[], None]) -> None:

        """Register a hook to execute before startup."""

        with self._lock:

            self._before_start.append(callback)



    def register_after_start(self, callback: Callable[[], None]) -> None:

        """Register a hook to execute after startup completes."""

        with self._lock:

            self._after_start.append(callback)



    def register_before_shutdown(self, callback: Callable[[], None]) -> None:

        """Register a hook to execute before teardown starts."""

        with self._lock:

            self._before_shutdown.append(callback)



    def register_after_shutdown(self, callback: Callable[[], None]) -> None:

        """Register a hook to execute after teardown completes."""

        with self._lock:

            self._after_shutdown.append(callback)



    def startup(self) -> None:

        """Transition the system to a running state, executing start hooks."""

        with self._lock:

            if self._is_running:

                logger.warning("System startup called, but system is already running.")

                return



            logger.info("Starting up Forge Universal AI Runtime...")





            for callback in self._before_start:

                self._run_safe(callback, "before_start callback")





            for component in self._components:

                self._run_safe(component.on_before_start, f"{component}.on_before_start")



            self._is_running = True

            logger.info("Core runtime systems transitioned to RUNNING.")





            for component in self._components:

                self._run_safe(component.on_after_start, f"{component}.on_after_start")





            for callback in self._after_start:

                self._run_safe(callback, "after_start callback")



    def shutdown(self) -> None:

        """Transition the system to an offline state, executing shutdown hooks."""

        with self._lock:

            if not self._is_running:

                logger.warning("System shutdown called, but system is not running.")

                return



            logger.info("Initiating teardown of Forge Universal AI Runtime...")





            for callback in self._before_shutdown:

                self._run_safe(callback, "before_shutdown callback")





            for component in self._components:

                self._run_safe(component.on_before_shutdown, f"{component}.on_before_shutdown")



            self._is_running = False

            logger.info("Core runtime systems transitioned to SHUTDOWN.")





            for component in self._components:

                self._run_safe(component.on_after_shutdown, f"{component}.on_after_shutdown")





            for callback in self._after_shutdown:

                self._run_safe(callback, "after_shutdown callback")



    def reload(self) -> None:

        """Reload the runtime, running a full shutdown and startup cycle."""

        logger.info("Reloading Universal AI Runtime context...")

        self.shutdown()

        self.startup()



    @property

    def is_running(self) -> bool:

        """Check if the system is currently running."""

        with self._lock:

            return self._is_running



    def _run_safe(self, func: Callable[[], None], desc: str) -> None:

        """Helper to run a lifecycle callback catching and logging failures."""

        try:

            func()

        except Exception as exc:

            logger.error("Error executing lifecycle hook '%s': %s", desc, exc, exc_info=True)

