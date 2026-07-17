"""ResponseForge token-optimizer integration.

ResponseForge is a prompt-level optimization engine that reduces LLM output
verbosity. It works by injecting system prompts that instruct the model
to communicate in a concise, token-efficient style — dropping filler words
and pleasantries while keeping all technical terms and code exact.

Two implementations are shipped:

* :class:`ResponseForgeRulesetOptimizer` — a self-contained Python
  implementation of the ResponseForge ruleset (lite / full / ultra / wenyan).
  Always available, no external dependencies.
* :class:`ResponseForgeCLIOptimizer` — an optional adapter that shells out
  to an external ``responseforge`` binary if one is on ``PATH``.

The :class:`ResponseForgeCompositeOptimizer` picks between them at runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum

from forgecli.optimizer.promptforge import OptimizedRequest
from forgecli.providers.base import ChatMessage, ChatRequest


class ResponseForgeIntensity(str, Enum):
    """How aggressively to compress LLM output.

    * ``off``    - no rewriting; pass prompts through unchanged.
    * ``lite``   - be concise; drop filler words and pleasantries.
    * ``full``   - full responseforge: fragments, [thing][action][reason] pattern.
    * ``ultra``  - maximum compression; grunt-level communication.
    * ``wenyan`` - Classical Chinese literary style (文言) for max density.
    """

    OFF = "off"
    LITE = "lite"
    FULL = "full"
    ULTRA = "ultra"
    WENYAN = "wenyan"

    @classmethod
    def parse(cls, value: str | ResponseForgeIntensity | None) -> ResponseForgeIntensity:
        """Parse a string into an :class:`ResponseForgeIntensity`, falling back to LITE."""
        if value is None or value == "":
            return cls.LITE
        if isinstance(value, cls):
            return value
        try:
            return cls(value.lower())
        except ValueError as exc:
            raise ValueError(
                f"Unknown responseforge intensity {value!r}; expected one of "
                f"{', '.join(i.value for i in cls)}"
            ) from exc


class ResponseForgePromptOptimizer(ABC):
    """Strategy interface for ResponseForge prompt optimization.

    Implementations must be deterministic and side-effect free
    (other than logging), so they can be invoked transparently before
    every model call.
    """

    name: str = "abstract-responseforge"

    @abstractmethod
    async def optimize_chat(self, request: ChatRequest) -> OptimizedRequest:
        """Return an optimized copy of ``request``."""

    async def is_available(self) -> bool:
        """Return whether this optimizer is available to use."""
        return True


class ResponseForgeCompositeOptimizer(ResponseForgePromptOptimizer):
    """Pick the right optimizer for the configured :class:`ResponseForgeIntensity`."""

    name = "responseforge-composite"

    def __init__(
        self,
        *,
        intensity: ResponseForgeIntensity = ResponseForgeIntensity.LITE,
        ruleset: ResponseForgePromptOptimizer | None = None,
        external: ResponseForgePromptOptimizer | None = None,
    ) -> None:
        self._intensity = intensity
        self._ruleset = ruleset
        self._external = external
        self._sync_ruleset_intensity()

    def _sync_ruleset_intensity(self) -> None:
        """Propagate the composite's intensity to the ruleset, if compatible."""
        ruleset = self._ruleset
        if isinstance(ruleset, ResponseForgeRulesetOptimizer):
            ruleset.set_intensity(self._intensity)

    @property
    def intensity(self) -> ResponseForgeIntensity:
        return self._intensity

    def set_intensity(self, intensity: ResponseForgeIntensity | str) -> None:
        self._intensity = ResponseForgeIntensity.parse(intensity)
        if isinstance(self._ruleset, ResponseForgeRulesetOptimizer):
            self._ruleset.set_intensity(self._intensity)

    async def optimize_chat(self, request: ChatRequest) -> OptimizedRequest:
        if self._intensity is ResponseForgeIntensity.OFF:
            return OptimizedRequest(
                request=request,
                notes=("responseforge off",),
                intensity=self._intensity,
                source="responseforge-passthrough",
            )

        if self._external is not None and await self._external.is_available():
            result = await self._external.optimize_chat(request)
            return OptimizedRequest(
                request=result.request,
                notes=(*result.notes, "responseforge external"),
                intensity=self._intensity,
                source="responseforge-external",
            )

        if self._ruleset is None:
            return OptimizedRequest(
                request=request,
                notes=("no responseforge ruleset registered",),
                intensity=self._intensity,
                source="responseforge-passthrough",
            )

        result = await self._ruleset.optimize_chat(request)
        return OptimizedRequest(
            request=result.request,
            notes=result.notes,
            intensity=self._intensity,
            source="responseforge-ruleset",
        )


def _ensure_user_message(messages: Sequence[ChatMessage]) -> bool:
    return any(m.role.value == "user" for m in messages)


def _clone_request(request: ChatRequest, messages: Sequence[ChatMessage]) -> ChatRequest:
    """Return a copy of ``request`` with ``messages`` replaced."""
    return request.model_copy(update={"messages": list(messages)})


__all__ = [
    "ResponseForgeCLIOptimizer",
    "ResponseForgeCompositeOptimizer",
    "ResponseForgeIntensity",
    "ResponseForgePromptOptimizer",
    "ResponseForgeProvider",
    "ResponseForgeRulesetOptimizer",
    "OptimizedRequest",
]

from forgecli.optimizer.responseforge.cli import ResponseForgeCLIOptimizer  # noqa: E402
from forgecli.optimizer.responseforge.decorator import ResponseForgeProvider  # noqa: E402
from forgecli.optimizer.responseforge.ruleset import ResponseForgeRulesetOptimizer  # noqa: E402
