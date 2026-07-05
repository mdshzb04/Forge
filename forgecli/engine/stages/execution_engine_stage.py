"""Stage 6 - Execution Engine.

Invokes the LLM with the assembled prompt and extracts a unified diff
from the response. Combines :func:`forgecli.build.llm.llm_call` and
:func:`forgecli.build.diff_extract.diff_extraction` into a single stage.
"""

from __future__ import annotations

from pathlib import Path

from forgecli.build import BuildContext
from forgecli.build.diff_extract import diff_extraction
from forgecli.build.llm import llm_call
from forgecli.engine.execution import StageContext, StageResult, StageStatus
from forgecli.providers.base import ChatMessage, ChatRequest, Provider, Role
from forgecli.providers.router import RouteDecision


class ExecutionEngineStage:
    """Send the prompt to the LLM and extract a diff."""

    name = "execution-engine"

    def __init__(self, provider: Provider | None = None) -> None:
        self._provider = provider

    async def __call__(self, context: StageContext) -> StageResult:
        provider = self._provider or context.engine.extras.get("provider")
        if provider is None:
            return StageResult(
                status=StageStatus.FAILED,
                error="no provider available for LLM call",
                notes=("no provider in extras or constructor",),
            )

        decision: RouteDecision | None = context.engine.extras.get("decision")
        build_ctx = BuildContext(
            prompt=context.engine.prompt,
            root=Path(context.engine.cwd),
            decision=decision,
        )
        if context.engine.retrieval is not None:
            build_ctx.retrieval = context.engine.retrieval.context_text
        if context.engine.optimized_request is not None:
            build_ctx.optimized_request = context.engine.optimized_request
            build_ctx.optimized_notes = context.engine.optimized_notes
        # Merge caveman-optimized system prompt into the final request.
        if (
            context.engine.caveman_optimized_request is not None
            and context.engine.optimized_request is not None
        ):
            build_ctx.optimized_request = _merge_caveman_request(
                context.engine.caveman_optimized_request,
                context.engine.optimized_request,
            )
        elif context.engine.caveman_optimized_request is not None:
            build_ctx.optimized_request = context.engine.caveman_optimized_request
        retries = int(context.engine.extras.get("retries", 0))
        build_ctx.extras["provider"] = provider
        build_ctx.extras["retries"] = retries

        build_ctx = await llm_call(build_ctx)
        build_ctx = await diff_extraction(build_ctx)

        context.engine.response = build_ctx.response
        context.engine.diff_text = build_ctx.diff_text

        diff_len = len(build_ctx.diff_text)
        notes: tuple[str, ...] = ()
        if diff_len > 0:
            notes = (f"extracted {diff_len}-char diff",)
        else:
            notes = ("no diff found in LLM response",)

        return StageResult(
            status=StageStatus.SUCCEEDED,
            data={
                "diff_length": diff_len,
                "has_response": build_ctx.response is not None,
            },
            notes=notes,
        )


def _merge_caveman_request(
    caveman_req: ChatRequest,
    ponytail_req: ChatRequest,
) -> ChatRequest:
    """Merge caveman and ponytail system prompts into one request."""
    caveman_sys = [m for m in caveman_req.messages if m.role is Role.SYSTEM]
    ponytail_sys = [m for m in ponytail_req.messages if m.role is Role.SYSTEM]
    other_messages = [m for m in ponytail_req.messages if m.role is not Role.SYSTEM]

    merged_sys_content = "\n\n".join(
        m.content for m in [*caveman_sys, *ponytail_sys] if m.content.strip()
    )
    merged_messages: list[ChatMessage] = [
        ChatMessage(role=Role.SYSTEM, content=merged_sys_content),
        *other_messages,
    ]
    return ponytail_req.model_copy(update={"messages": merged_messages})
