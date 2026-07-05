"""Optional adapter that shells out to an external ``caveman`` binary.

The external binary is **not** shipped with ForgeCLI. The adapter
is here so the :class:`CavemanCompositeOptimizer` can transparently
pick it when the user has installed a caveman CLI tool separately.
"""

from __future__ import annotations

import asyncio
import logging
import shutil

from forgecli.optimizer.caveman import (
    CavemanIntensity,
    CavemanPromptOptimizer,
    OptimizedRequest,
)
from forgecli.providers.base import ChatRequest

_log = logging.getLogger("forgecli.optimizer.caveman.cli")


class CavemanCLIOptimizer(CavemanPromptOptimizer):
    """Shell out to an external ``caveman`` binary for prompt optimization."""

    name = "caveman.cli"

    def __init__(
        self,
        executable: str = "caveman",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._executable = executable
        self._timeout = timeout_seconds

    async def is_available(self) -> bool:
        """Return True when the ``caveman`` binary is on ``PATH``."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: shutil.which(self._executable) is not None)

    async def optimize_chat(self, request: ChatRequest) -> OptimizedRequest:
        """Run the external caveman binary and return the optimized request.

        Currently a stub that returns the request unchanged \u2014 the
        caveman CLI protocol hasn't been standardised yet. Implement
        this method once a stable CLI interface exists.
        """
        _log.debug(
            "caveman CLI adapter called; binary=%s available=%s",
            self._executable,
            await self.is_available(),
        )
        return OptimizedRequest(
            request=request,
            notes=("caveman CLI stub (passthrough)",),
            intensity=CavemanIntensity.LITE,
            source="caveman-cli",
        )


__all__ = ["CavemanCLIOptimizer"]
