"""Stage 3 — Caveman token optimization.

Wraps the user prompt with the configured :class:`CavemanPromptOptimizer`
(default: :class:`CavemanRulesetOptimizer`). The optimized request is
stored in ``caveman_optimized_request`` and later merged with the
Ponytail-optimized request before the LLM call.
"""



from __future__ import annotations



from forgecli.build import BuildContext

from forgecli.optimizer.caveman import CavemanPromptOptimizer

from forgecli.providers.base import ChatMessage, ChatRequest, Role





async def caveman_optimization(context: BuildContext) -> BuildContext:

    """Run the configured :class:`CavemanPromptOptimizer` and stash the result."""

    optimizer: CavemanPromptOptimizer | None = context.extras.get("caveman_optimizer")

    if optimizer is None:

                                                                            

                                           

        context.caveman_optimized_request = ChatRequest(

            messages=[ChatMessage(role=Role.USER, content=context.prompt)],

        )

        context.caveman_optimized_notes = ()

        return context



    request = ChatRequest(

        messages=[ChatMessage(role=Role.USER, content=context.prompt)],

    )

    optimized = await optimizer.optimize_chat(request)

    context.caveman_optimized_request = optimized.request

    context.caveman_optimized_notes = optimized.notes

    return context





__all__ = ["caveman_optimization"]

