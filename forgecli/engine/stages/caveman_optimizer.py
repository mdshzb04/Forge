"""Stage 3 — Caveman Optimizer.

Applies the Caveman ruleset to the user prompt to reduce token usage
in LLM responses. Wraps :func:`forgecli.build.caveman_optimize.caveman_optimization`.
"""



from __future__ import annotations

from pathlib import Path

from forgecli.build import BuildContext
from forgecli.build.caveman_optimize import caveman_optimization as _build_caveman_optimize
from forgecli.engine.execution import StageContext, StageResult, StageStatus
from forgecli.optimizer.caveman import CavemanPromptOptimizer


class CavemanOptimizerStage:

    """Optimize the prompt using Caveman rules."""



    name = "caveman-optimizer"



    def __init__(self, optimizer: CavemanPromptOptimizer | None = None) -> None:

        self._optimizer = optimizer



    async def __call__(self, context: StageContext) -> StageResult:

        optimizer = self._optimizer or context.engine.extras.get("caveman_optimizer")

        build_ctx = BuildContext(

            prompt=context.engine.prompt,

            root=Path(context.engine.cwd),

        )

        build_ctx.extras["caveman_optimizer"] = optimizer



        build_ctx = await _build_caveman_optimize(build_ctx)



        context.engine.caveman_optimized_request = build_ctx.caveman_optimized_request

        context.engine.caveman_optimized_notes = build_ctx.caveman_optimized_notes



        return StageResult(

            status=StageStatus.SUCCEEDED,

            data={

                "notes": list(build_ctx.caveman_optimized_notes),

            },

            notes=build_ctx.caveman_optimized_notes or ("no caveman optimization applied",),

        )





__all__ = ["CavemanOptimizerStage"]

