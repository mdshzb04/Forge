"""Caveman token-optimizer integration.

Caveman is a prompt-level optimization engine that reduces LLM output
verbosity. It works by injecting system prompts that instruct the model
to communicate in a concise, token-efficient style — dropping filler words
and pleasantries while keeping all technical terms and code exact.

Two implementations are shipped:

* :class:`CavemanRulesetOptimizer` — a self-contained Python
  implementation of the Caveman ruleset (lite / full / ultra / wenyan).
  Always available, no external dependencies.
* :class:`CavemanCLIOptimizer` — an optional adapter that shells out
  to an external ``caveman`` binary if one is on ``PATH``.

The :class:`CavemanCompositeOptimizer` picks between them at runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum

from forgecli.optimizer.ponytail import OptimizedRequest
from forgecli.providers.base import ChatMessage, ChatRequest


class CavemanIntensity(str, Enum):
    """How aggressively to compress LLM output.

    * ``off``    - no rewriting; pass prompts through unchanged.
    * ``lite``   - be concise; drop filler words and pleasantries.
    * ``full``   - full caveman: fragments, [thing][action][reason] pattern.
    * ``ultra``  - maximum compression; grunt-level communication.
    * ``wenyan`` - Classical Chinese literary style (文言) for max density.
    """

    OFF = "off"
    LITE = "lite"
    FULL = "full"
    ULTRA = "ultra"
    WENYAN = "wenyan"

    @classmethod
    def parse(cls, value: str | CavemanIntensity | None) -> CavemanIntensity:
        """Parse a string into an :class:`CavemanIntensity`, falling back to LITE."""
        if value is None or value == "":
            return cls.LITE
        if isinstance(value, cls):
            return value
        try:
            return cls(value.lower())
        except ValueError as exc:
            raise ValueError(
                f"Unknown caveman intensity {value!r}; expected one of "
                f"{', '.join(i.value for i in cls)}"
            ) from exc


class CavemanPromptOptimizer(ABC):
    """Strategy interface for Caveman prompt optimization.

    Implementations must be deterministic and side-effect free
    (other than logging), so they can be invoked transparently before
    every model call.
    """

    name: str = "abstract-caveman"

    @abstractmethod
    async def optimize_chat(self, request: ChatRequest) -> OptimizedRequest:
        """Return an optimized copy of ``request``."""

    async def is_available(self) -> bool:
        """Return whether this optimizer is available to use."""
        return True


class CavemanCompositeOptimizer(CavemanPromptOptimizer):
    """Pick the right optimizer for the configured :class:`CavemanIntensity`."""

    name = "caveman-composite"

    def __init__(
        self,
        *,
        intensity: CavemanIntensity = CavemanIntensity.LITE,
        ruleset: CavemanPromptOptimizer | None = None,
        external: CavemanPromptOptimizer | None = None,
    ) -> None:
        self._intensity = intensity
        self._ruleset = ruleset
        self._external = external
        self._sync_ruleset_intensity()

    def _sync_ruleset_intensity(self) -> None:
        """Propagate the composite's intensity to the ruleset, if compatible."""
        ruleset = self._ruleset
        if isinstance(ruleset, CavemanRulesetOptimizer):
            ruleset.set_intensity(self._intensity)

    @property
    def intensity(self) -> CavemanIntensity:
        return self._intensity

    def set_intensity(self, intensity: CavemanIntensity | str) -> None:
        self._intensity = CavemanIntensity.parse(intensity)
        if isinstance(self._ruleset, CavemanRulesetOptimizer):
            self._ruleset.set_intensity(self._intensity)

    async def optimize_chat(self, request: ChatRequest) -> OptimizedRequest:
        if self._intensity is CavemanIntensity.OFF:
            return OptimizedRequest(
                request=request,
                notes=("caveman off",),
                intensity=self._intensity,
                source="caveman-passthrough",
            )

        if self._external is not None and await self._external.is_available():
            result = await self._external.optimize_chat(request)
            return OptimizedRequest(
                request=result.request,
                notes=(*result.notes, "caveman external"),
                intensity=self._intensity,
                source="caveman-external",
            )

        if self._ruleset is None:
            return OptimizedRequest(
                request=request,
                notes=("no caveman ruleset registered",),
                intensity=self._intensity,
                source="caveman-passthrough",
            )

        result = await self._ruleset.optimize_chat(request)
        return OptimizedRequest(
            request=result.request,
            notes=result.notes,
            intensity=self._intensity,
            source="caveman-ruleset",
        )


def _ensure_user_message(messages: Sequence[ChatMessage]) -> bool:
    return any(m.role.value == "user" for m in messages)


def _clone_request(request: ChatRequest, messages: Sequence[ChatMessage]) -> ChatRequest:
    """Return a copy of ``request`` with ``messages`` replaced."""
    return request.model_copy(update={"messages": list(messages)})


__all__ = [
    "CavemanCLIOptimizer",
    "CavemanCompositeOptimizer",
    "CavemanIntensity",
    "CavemanPromptOptimizer",
    "CavemanProvider",
    "CavemanRulesetOptimizer",
    "OptimizedRequest",
]

from forgecli.optimizer.caveman.cli import CavemanCLIOptimizer  # noqa: E402
from forgecli.optimizer.caveman.decorator import CavemanProvider  # noqa: E402
from forgecli.optimizer.caveman.ruleset import CavemanRulesetOptimizer  # noqa: E402
