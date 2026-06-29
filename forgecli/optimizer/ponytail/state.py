"""Live runtime state for the prompt optimizer.

The optimizer intensity can be flipped from the CLI via
``forge optimizer lite|full|ultra|off``. Because the setting is held
in :class:`AppContext.extras`, every subcommand that resolves the
optimizer sees the latest value. Tests can override it directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from forgecli.optimizer.ponytail import Intensity


@dataclass
class OptimizerState:
    """Mutable intensity for the running CLI process."""

    intensity: Intensity = Intensity.LITE
    backend: str = "ruleset"  # "ruleset" | "cli" | "auto"
    binary: str = "ponytail"

    @classmethod
    def from_extras(cls, extras: dict[str, object]) -> OptimizerState:
        state = cls()
        intensity = extras.get("optimizer.intensity") or extras.get(
            "optimizer_intensity"
        )
        backend = extras.get("optimizer.backend") or extras.get("optimizer_backend")
        binary = extras.get("optimizer.binary") or extras.get("optimizer_binary")
        if isinstance(intensity, str):
            try:
                state.intensity = Intensity.parse(intensity)
            except ValueError:
                state.intensity = Intensity.LITE
        elif isinstance(intensity, Intensity):
            state.intensity = intensity
        if isinstance(backend, str):
            state.backend = backend
        if isinstance(binary, str):
            state.binary = binary
        return state

    def to_extras(self) -> dict[str, str]:
        return {
            "optimizer.intensity": self.intensity.value,
            "optimizer.backend": self.backend,
            "optimizer.binary": self.binary,
        }


__all__ = ["OptimizerState"]
