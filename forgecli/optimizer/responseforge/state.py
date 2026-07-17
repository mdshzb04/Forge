"""Live runtime state for the ResponseForge optimizer.

The intensity can be flipped at runtime. Because the setting is held
in :class:`AppContext.extras`, every subcommand that resolves the
optimizer sees the latest value. Tests can override it directly.
"""



from __future__ import annotations

from dataclasses import dataclass

from forgecli.optimizer.responseforge import ResponseForgeIntensity


@dataclass

class ResponseForgeState:

    """Mutable intensity for the running CLI process."""



    intensity: ResponseForgeIntensity = ResponseForgeIntensity.LITE

    backend: str = "ruleset"

    binary: str = "responseforge"



    @classmethod

    def from_extras(cls, extras: dict[str, object]) -> ResponseForgeState:

        state = cls()

        intensity = extras.get("responseforge.intensity") or extras.get("responseforge_intensity")

        backend = extras.get("responseforge.backend") or extras.get("responseforge_backend")

        binary = extras.get("responseforge.binary") or extras.get("responseforge_binary")

        if isinstance(intensity, str):

            try:

                state.intensity = ResponseForgeIntensity.parse(intensity)

            except ValueError:

                state.intensity = ResponseForgeIntensity.LITE

        elif isinstance(intensity, ResponseForgeIntensity):

            state.intensity = intensity

        if isinstance(backend, str):

            state.backend = backend

        if isinstance(binary, str):

            state.binary = binary

        return state



    def to_extras(self) -> dict[str, str]:

        return {

            "responseforge.intensity": self.intensity.value,

            "responseforge.backend": self.backend,

            "responseforge.binary": self.binary,

        }





__all__ = ["ResponseForgeState"]

