"""Factory for building the live :class:`CavemanPromptOptimizer`."""



from __future__ import annotations

from forgecli.config.settings import ForgeSettings
from forgecli.optimizer.caveman import (
    CavemanCLIOptimizer,
    CavemanCompositeOptimizer,
    CavemanIntensity,
    CavemanPromptOptimizer,
    CavemanRulesetOptimizer,
)
from forgecli.optimizer.caveman.state import CavemanState


def build_caveman_optimizer(

    state: CavemanState,

    settings: ForgeSettings | None = None,

) -> CavemanPromptOptimizer:

    """Build the composite Caveman optimizer from runtime state + config.

    The composite always falls back to the in-process ruleset; the
    external CLI adapter is added on top whenever the configured
    backend asks for it and the binary is available.
    """

    ruleset = CavemanRulesetOptimizer(intensity=state.intensity)



    external: CavemanPromptOptimizer | None = None

    if state.backend in {"cli", "auto"}:

        binary = state.binary

        if settings is not None and settings.caveman.binary:

            binary = settings.caveman.binary

        external = CavemanCLIOptimizer(executable=binary)

    elif state.backend == "ruleset":

        external = None



    if settings is not None and not settings.caveman.enabled:

        return CavemanCompositeOptimizer(

            intensity=CavemanIntensity.OFF,

            ruleset=ruleset,

            external=external,

        )



    return CavemanCompositeOptimizer(

        intensity=state.intensity,

        ruleset=ruleset,

        external=external,

    )





__all__ = ["build_caveman_optimizer"]

