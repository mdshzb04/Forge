"""Stage 3 — ResponseForge token optimization.

Wraps the user prompt with the configured :class:`ResponseForgePromptOptimizer`
(default: :class:`ResponseForgeRulesetOptimizer`). The optimized request is
stored in ``responseforge_optimized_request`` and later merged with the
PromptForge-optimized request before the LLM call.
"""



from __future__ import annotations



from forgecli.build import BuildContext

from forgecli.optimizer.responseforge import ResponseForgePromptOptimizer

from forgecli.providers.base import ChatMessage, ChatRequest, Role





async def responseforge_optimization(context: BuildContext) -> BuildContext:

    """Run the configured :class:`ResponseForgePromptOptimizer` and stash the result."""

    optimizer: ResponseForgePromptOptimizer | None = context.extras.get("responseforge_optimizer")

    if optimizer is None:

                                                                            

                                           

        context.responseforge_optimized_request = ChatRequest(

            messages=[ChatMessage(role=Role.USER, content=context.prompt)],

        )

        context.responseforge_optimized_notes = ()

        return context



    request = ChatRequest(

        messages=[ChatMessage(role=Role.USER, content=context.prompt)],

    )

    optimized = await optimizer.optimize_chat(request)

    context.responseforge_optimized_request = optimized.request

    context.responseforge_optimized_notes = optimized.notes

    return context





__all__ = ["responseforge_optimization"]

