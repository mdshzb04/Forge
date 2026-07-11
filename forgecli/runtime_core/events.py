"""Event bus for the Universal AI Runtime.

Provides typed publish/subscribe channels with priority routing and thread executors.
"""



from __future__ import annotations

import concurrent.futures
import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("forge.runtime_core.events")





class EventBus:

    """Central event broker for component coordination.

    Allows handlers to subscribe to typed events with priority. Runs asynchronous
    notifications inside an internal thread pool executor.
    """



    def __init__(self, max_workers: int = 4) -> None:

        """Initialize the EventBus.

        Args:
            max_workers: The worker count for the background thread pool.
        """

        self._lock = threading.Lock()



        self._listeners: dict[type[Any], list[tuple[int, Callable[[Any], None]]]] = {}

        self._executor = concurrent.futures.ThreadPoolExecutor(

            max_workers=max_workers,

            thread_name_prefix="forge_event_bus",

        )



    def subscribe(self, event_type: type[Any], handler: Callable[[Any], None], priority: int = 100) -> None:

        """Subscribe to a specific event type.

        Args:
            event_type: The class type of the event.
            handler: The subscriber callback.
            priority: Higher numbers denote higher priority execution.
        """

        if not callable(handler):

            raise TypeError("Event handler must be a callable.")



        with self._lock:

            if event_type not in self._listeners:

                self._listeners[event_type] = []





            for _, existing in self._listeners[event_type]:

                if existing == handler:

                    return



            self._listeners[event_type].append((priority, handler))



            self._listeners[event_type].sort(key=lambda item: item[0], reverse=True)

            logger.debug("Subscribed %s to %s with priority %d", handler, event_type.__name__, priority)



    def unsubscribe(self, event_type: type[Any], handler: Callable[[Any], None]) -> None:

        """Remove a subscriber from an event channel.

        Args:
            event_type: The class type.
            handler: The subscriber callback.
        """

        with self._lock:

            if event_type not in self._listeners:

                return



            original_list = self._listeners[event_type]

            self._listeners[event_type] = [item for item in original_list if item[1] != handler]

            logger.debug("Unsubscribed %s from %s", handler, event_type.__name__)



    def publish(self, event: Any) -> None:

        """Publish an event synchronously to all registered listeners.

        Args:
            event: The event payload instance.
        """

        event_type = type(event)

        handlers_to_run: list[Callable[[Any], None]] = []



        with self._lock:



            if event_type in self._listeners:

                handlers_to_run.extend([h for _, h in self._listeners[event_type]])





        for handler in handlers_to_run:

            try:

                handler(event)

            except Exception as exc:

                logger.error(

                    "Error executing event handler %s for event %s: %s",

                    handler,

                    event_type.__name__,

                    exc,

                    exc_info=True,

                )



    def emit_async(self, event: Any) -> concurrent.futures.Future[None]:

        """Publish an event asynchronously in the background thread executor.

        Args:
            event: The event payload.

        Returns:
            A Future representing the background execution task.
        """



        return self._executor.submit(self.publish, event)



    def shutdown(self, wait: bool = True) -> None:

        """Clean up thread executor assets.

        Args:
            wait: Whether to block until all active tasks complete.
        """

        with self._lock:

            self._executor.shutdown(wait=wait)

            logger.debug("EventBus background executor shut down.")

class SystemEvent:

    """Base class for system-wide lifecycle events."""



    pass

