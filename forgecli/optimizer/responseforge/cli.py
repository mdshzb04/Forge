"""Optional adapter that shells out to an external ``responseforge`` binary.

The external binary is **not** shipped with ForgeCLI. The adapter
is here so the :class:`ResponseForgeCompositeOptimizer` can transparently
pick it when the user has installed a responseforge CLI tool separately.
"""



from __future__ import annotations

import asyncio
import logging
import shutil

from forgecli.optimizer.responseforge import (
    OptimizedRequest,
    ResponseForgeIntensity,
    ResponseForgePromptOptimizer,
)
from forgecli.providers.base import ChatRequest

_log = logging.getLogger("forgecli.optimizer.responseforge.cli")





class ResponseForgeCLIOptimizer(ResponseForgePromptOptimizer):

    """Shell out to an external ``responseforge`` binary for prompt optimization."""



    name = "responseforge.cli"



    def __init__(

        self,

        executable: str = "responseforge",

        timeout_seconds: float = 30.0,

    ) -> None:

        self._executable = executable

        self._timeout = timeout_seconds



    async def is_available(self) -> bool:

        """Return True when the ``responseforge`` binary is on ``PATH``."""

        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(None, lambda: shutil.which(self._executable) is not None)



    async def optimize_chat(self, request: ChatRequest) -> OptimizedRequest:

        """Run the external responseforge binary and return the optimized request.

        Currently a stub that returns the request unchanged \u2014 the
        responseforge CLI protocol hasn't been standardised yet. Implement
        this method once a stable CLI interface exists.
        """

        _log.debug(

            "responseforge CLI adapter called; binary=%s available=%s",

            self._executable,

            await self.is_available(),

        )

        return OptimizedRequest(

            request=request,

            notes=("responseforge CLI stub (passthrough)",),

            intensity=ResponseForgeIntensity.LITE,

            source="responseforge-cli",

        )





__all__ = ["ResponseForgeCLIOptimizer"]

