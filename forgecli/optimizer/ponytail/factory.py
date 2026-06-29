"""Factory for building the live :class:`PromptOptimizer`."""

from __future__ import annotations

from forgecli.config.settings import ForgeSettings
from forgecli.optimizer.ponytail import (
    CompositeOptimizer,
    Intensity,
    PonytailCLIOptimizer,
    PonytailRulesetOptimizer,
    PromptOptimizer,
)
from forgecli.optimizer.ponytail.state import OptimizerState


def build_optimizer(
    state: OptimizerState,
    settings: ForgeSettings | None = None,
) -> PromptOptimizer:
    """Build the composite optimizer from the runtime state + config.

    The composite always falls back to the in-process ruleset; the
    external CLI adapter is added on top whenever the configured
    backend asks for it and the binary is available.
    """
    ruleset = PonytailRulesetOptimizer(intensity=state.intensity)

    external: PromptOptimizer | None = None
    if state.backend in {"cli", "auto"}:
        binary = state.binary
        if settings is not None and settings.prompt_optimizer.binary:
            binary = settings.prompt_optimizer.binary
        external = PonytailCLIOptimizer(executable=binary)
    elif state.backend == "ruleset":
        external = None

    if settings is not None and not settings.prompt_optimizer.enabled:
        return CompositeOptimizer(
            intensity=Intensity.OFF,
            ruleset=ruleset,
            external=external,
        )

    return CompositeOptimizer(
        intensity=state.intensity,
        ruleset=ruleset,
        external=external,
    )


__all__ = ["build_optimizer"]
