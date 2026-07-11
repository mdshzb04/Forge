"""Daemon server manager."""



from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

from forgecli.transport.server import TransportServer

logger = logging.getLogger("forge.transport.daemon")





class ForgeDaemon:

    """Manages the lifecycle of a Forge transport server as a daemon process."""



    def __init__(self, server: TransportServer) -> None:

        self.server = server

        self._stop_event = asyncio.Event()



    def _setup_signal_handlers(self) -> None:

        """Attach OS signal handlers for graceful shutdown."""

        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):

            with contextlib.suppress(NotImplementedError):

                loop.add_signal_handler(sig, self._handle_signal, sig)




    def _handle_signal(self, sig: int) -> None:

        """Handle incoming stop signals."""

        logger.info("Received exit signal %s...", sig)

        self._stop_event.set()



    async def serve(self) -> None:

        """Start the server and block until interrupted."""

        self._setup_signal_handlers()



        try:

            await self.server.start()

            logger.info("Forge Daemon is running. Press Ctrl+C to stop.")

            await self._stop_event.wait()

        finally:

            logger.info("Shutting down Forge Daemon...")

            await self.server.stop()

