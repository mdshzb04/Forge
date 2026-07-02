"""Live runtime state for the Caveman optimizer.

The intensity can be flipped at runtime. Because the setting is held
in :class:`AppContext.extras`, every subcommand that resolves the
optimizer sees the latest value. Tests can override it directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from forgecli.optimizer.caveman import CavemanIntensity


@dataclass
class CavemanState:
    """Mutable intensity for the running CLI process."""

    intensity: CavemanIntensity = CavemanIntensity.LITE
    backend: str = "ruleset"  # "ruleset" | "cli" | "auto"
    binary: str = "caveman"

    @classmethod
    def from_extras(cls, extras: dict[str, object]) -> CavemanState:
        state = cls()
        intensity = extras.get("caveman.intensity") or extras.get(
            "caveman_intensity"
        )
        backend = extras.get("caveman.backend") or extras.get("caveman_backend")
        binary = extras.get("caveman.binary") or extras.get("caveman_binary")
        if isinstance(intensity, str):
            try:
                state.intensity = CavemanIntensity.parse(intensity)
            except ValueError:
                state.intensity = CavemanIntensity.LITE
        elif isinstance(intensity, CavemanIntensity):
            state.intensity = intensity
        if isinstance(backend, str):
            state.backend = backend
        if isinstance(binary, str):
            state.binary = binary
        return state

    def to_extras(self) -> dict[str, str]:
        return {
            "caveman.intensity": self.intensity.value,
            "caveman.backend": self.backend,
            "caveman.binary": self.binary,
        }


__all__ = ["CavemanState"]
