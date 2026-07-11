"""HTTP Server for Transport Layer."""



from __future__ import annotations

import asyncio
import contextlib
import logging

from forgecli.middleware.executor import PipelineExecutor
from forgecli.transport.server import TransportServer

logger = logging.getLogger("forge.transport.http")





class HttpServer(TransportServer):

    """An HTTP server wrapping the Forge pipeline engine.

    In a full deployment, this integrates with FastAPI/Uvicorn or an ASGI server.
    """



    def __init__(self, engine: PipelineExecutor, host: str = "127.0.0.1", port: int = 8000) -> None:

        super().__init__(engine, host, port)

        self._server_task: asyncio.Task[None] | None = None



    async def start(self) -> None:

        """Start the HTTP listener."""

        if self.is_running:

            return



        self.is_running = True

        logger.info("Starting Forge HTTP Server on %s:%d...", self.host, self.port)





        async def _mock_serve() -> None:

            try:

                while self.is_running:

                    await asyncio.sleep(1.0)

            except asyncio.CancelledError:

                pass



        self._server_task = asyncio.create_task(_mock_serve())



    async def stop(self) -> None:

        """Stop the HTTP listener."""

        if not self.is_running:

            return



        logger.info("Stopping Forge HTTP Server...")

        self.is_running = False



        if self._server_task:

            self._server_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):

                await self._server_task


            self._server_task = None

