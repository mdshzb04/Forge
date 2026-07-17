"""Factory for building the live :class:`ResponseForgePromptOptimizer`."""



from __future__ import annotations

from forgecli.config.settings import ForgeSettings
from forgecli.optimizer.responseforge import (
    ResponseForgeCLIOptimizer,
    ResponseForgeCompositeOptimizer,
    ResponseForgeIntensity,
    ResponseForgePromptOptimizer,
    ResponseForgeRulesetOptimizer,
)
from forgecli.optimizer.responseforge.state import ResponseForgeState


def build_responseforge_optimizer(

    state: ResponseForgeState,

    settings: ForgeSettings | None = None,

) -> ResponseForgePromptOptimizer:

    """Build the composite ResponseForge optimizer from runtime state + config.

    The composite always falls back to the in-process ruleset; the
    external CLI adapter is added on top whenever the configured
    backend asks for it and the binary is available.
    """

    ruleset = ResponseForgeRulesetOptimizer(intensity=state.intensity)



    external: ResponseForgePromptOptimizer | None = None

    if state.backend in {"cli", "auto"}:

        binary = state.binary

        if settings is not None and settings.responseforge.binary:

            binary = settings.responseforge.binary

        external = ResponseForgeCLIOptimizer(executable=binary)

    elif state.backend == "ruleset":

        external = None



    if settings is not None and not settings.responseforge.enabled:

        return ResponseForgeCompositeOptimizer(

            intensity=ResponseForgeIntensity.OFF,

            ruleset=ruleset,

            external=external,

        )



    return ResponseForgeCompositeOptimizer(

        intensity=state.intensity,

        ruleset=ruleset,

        external=external,

    )





__all__ = ["build_responseforge_optimizer"]

