"""Generic hook and event publish/subscribe system for plugins."""



from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("forge.plugins.hook")





@dataclass

class HookEvent:

    """An event dispatched to registered hooks."""



    name: str

    sender: str

    payload: dict[str, Any] = field(default_factory=dict)





class HookManager:

    """Manages asynchronous hook registrations and event dispatching."""



    def __init__(self) -> None:

        self._listeners: dict[str, list[Callable[[HookEvent], Awaitable[None]]]] = {}



    def register(self, event_name: str, callback: Callable[[HookEvent], Awaitable[None]]) -> None:

        """Register a callback for a specific event."""

        if event_name not in self._listeners:

            self._listeners[event_name] = []

        self._listeners[event_name].append(callback)

        logger.debug("Registered hook for event '%s'", event_name)



    def unregister(self, event_name: str, callback: Callable[[HookEvent], Awaitable[None]]) -> None:

        """Unregister a specific callback."""

        if event_name in self._listeners and callback in self._listeners[event_name]:

            self._listeners[event_name].remove(callback)



    async def dispatch(self, event: HookEvent) -> None:

        """Dispatch an event to all registered listeners asynchronously.

        Fails gracefully if a hook throws an exception.
        """

        listeners = self._listeners.get(event.name, [])

        if not listeners:

            return



        tasks = []

        for cb in listeners:

            tasks.append(asyncio.create_task(self._safe_call(cb, event)))



        await asyncio.gather(*tasks)



    async def _safe_call(self, callback: Callable[[HookEvent], Awaitable[None]], event: HookEvent) -> None:

        try:

            await callback(event)

        except Exception as e:

            logger.error("Error executing hook for event '%s': %s", event.name, e)

