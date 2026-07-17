"""Stage 3 — ResponseForge Optimizer.

Applies the ResponseForge ruleset to the user prompt to reduce token usage
in LLM responses. Wraps :func:`forgecli.build.responseforge_optimize.responseforge_optimization`.
"""



from __future__ import annotations

from pathlib import Path

from forgecli.build import BuildContext
from forgecli.build.responseforge_optimize import (
    responseforge_optimization as _build_responseforge_optimize,
)
from forgecli.engine.execution import StageContext, StageResult, StageStatus
from forgecli.optimizer.responseforge import ResponseForgePromptOptimizer


class ResponseForgeOptimizerStage:

    """Optimize the prompt using ResponseForge rules."""



    name = "responseforge-optimizer"



    def __init__(self, optimizer: ResponseForgePromptOptimizer | None = None) -> None:

        self._optimizer = optimizer



    async def __call__(self, context: StageContext) -> StageResult:

        optimizer = self._optimizer or context.engine.extras.get("responseforge_optimizer")

        build_ctx = BuildContext(

            prompt=context.engine.prompt,

            root=Path(context.engine.cwd),

        )

        build_ctx.extras["responseforge_optimizer"] = optimizer



        build_ctx = await _build_responseforge_optimize(build_ctx)



        context.engine.responseforge_optimized_request = build_ctx.responseforge_optimized_request

        context.engine.responseforge_optimized_notes = build_ctx.responseforge_optimized_notes



        return StageResult(

            status=StageStatus.SUCCEEDED,

            data={

                "notes": list(build_ctx.responseforge_optimized_notes),

            },

            notes=build_ctx.responseforge_optimized_notes or ("no responseforge optimization applied",),

        )





__all__ = ["ResponseForgeOptimizerStage"]

