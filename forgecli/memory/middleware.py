"""History Compression Middleware for the Forge middleware engine."""



from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from forgecli.memory.memory_compression import MemoryCompressionManager
from forgecli.middleware.base import Middleware
from forgecli.providers.base import ChatMessage, Role

if TYPE_CHECKING:

    from forgecli.middleware.context import RequestContext, ResponseContext





class HistoryCompressionMiddleware(Middleware):

    """Pipeline middleware that compresses dialogue history to respect model context windows."""



    def __init__(self, keep_recent_turns: int = 4) -> None:

        """Initialize the HistoryCompressionMiddleware.

        Args:
            keep_recent_turns: The number of recent turns to preserve in full.
        """

        self._manager = MemoryCompressionManager(keep_recent_turns=keep_recent_turns)



    @property

    def priority(self) -> int:

        """Priority ordering value (higher runs earlier)."""

        return 700



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        """Intercept the request and compress its message history if needed.

        Args:
            request: The RequestContext object.
            call_next: Next pipeline runner callback.
        """

        raw_messages = request.ai_request.messages

        if len(raw_messages) > self._manager.keep_recent:



            chat_messages = []

            for msg in raw_messages:

                role_val = msg.get("role", "user")



                if role_val == "system":

                    role = Role.SYSTEM

                elif role_val == "assistant":

                    role = Role.ASSISTANT

                else:

                    role = Role.USER



                chat_messages.append(

                    ChatMessage(role=role, content=msg.get("content", ""))

                )





            compressed_chats = self._manager.compress_history(chat_messages)





            request.ai_request.messages = [

                {"role": m.role.value, "content": m.content} for m in compressed_chats

            ]



        return await call_next(request)

