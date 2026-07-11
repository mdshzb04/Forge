"""Transport layer server definitions."""



from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from forgecli.middleware.executor import PipelineExecutor

logger = logging.getLogger("forge.transport")





class TransportServer(ABC):

    """Abstract base class for all protocol transport servers (HTTP, WebSocket, gRPC, etc.)."""



    def __init__(self, engine: PipelineExecutor, host: str = "127.0.0.1", port: int = 8000) -> None:

        self.engine = engine

        self.host = host

        self.port = port

        self.is_running = False



    @abstractmethod

    async def start(self) -> None:

        """Start accepting connections asynchronously."""

        pass



    @abstractmethod

    async def stop(self) -> None:

        """Stop the server and drain connections."""

        pass

