"""PromptForge prompt optimizer middleware adapter."""



from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from forgecli.middleware.base import Middleware
from forgecli.optimizer.promptforge import CompositeOptimizer, Intensity, PromptForgeRulesetOptimizer
from forgecli.providers.base import ChatMessage, ChatRequest, Role

if TYPE_CHECKING:

    from forgecli.middleware.context import RequestContext, ResponseContext





class PromptForgeAdapterMiddleware(Middleware):

    """Pipeline middleware that applies PromptForge prompt ruleset optimizations."""



    def __init__(self, intensity: str = "lite") -> None:

        """Initialize the PromptForgeAdapterMiddleware.

        Args:
            intensity: The optimization intensity (off, lite, full, ultra).
        """

        parsed_intensity = Intensity.parse(intensity)

        ruleset = PromptForgeRulesetOptimizer()

        self._optimizer = CompositeOptimizer(intensity=parsed_intensity, ruleset=ruleset)



    @property

    def priority(self) -> int:

        """Priority ordering value (runs after policy, before model call)."""

        return 600



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        """Intercept and optimize the prompt using PromptForge.

        Args:
            request: The RequestContext object.
            call_next: Next pipeline runner callback.
        """



        messages = []

        for msg in request.ai_request.messages:

            role_val = msg.get("role", "user")

            role = Role.SYSTEM if role_val == "system" else (Role.ASSISTANT if role_val == "assistant" else Role.USER)

            messages.append(ChatMessage(role=role, content=msg.get("content", "")))





        messages.append(ChatMessage(role=Role.USER, content=request.ai_request.prompt))



        chat_req = ChatRequest(

            model=request.ai_request.model_name,

            messages=messages,

            temperature=request.ai_request.temperature,

            stream=request.ai_request.stream,

        )



        optimized = await self._optimizer.optimize_chat(chat_req)





        opt_messages = list(optimized.request.messages)

        if opt_messages:



            last_msg = opt_messages.pop()

            request.ai_request.prompt = last_msg.content

            request.ai_request.messages = [

                {"role": m.role.value, "content": m.content} for m in opt_messages

            ]





        request.metadata["promptforge_optimized"] = True

        request.metadata["promptforge_source"] = optimized.source

        request.metadata["promptforge_notes"] = optimized.notes



        return await call_next(request)

