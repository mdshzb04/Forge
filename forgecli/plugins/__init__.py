"""Plugin extension points for ForgeCLI.

A plugin is a Python package that exposes one or more of:

* :class:`Workflow` — a named, executable unit that orchestrates
  the standard pipeline stages (retrieval, optimization, LLM call,
  apply, test, summary) in a custom way. The top-level ``forge``
  command dispatches to a Workflow based on the user's prompt and
  the current :class:`Intent`.
* :class:`Provider` — an AI provider. The router picks from registered
  providers based on the user's model choice.
* :class:`PromptOptimizer` — a prompt-rewriting strategy. Selected by
  the configured intensity.
* :class:`Analyzer` — a code-review analyzer. The review command
  runs every registered analyzer.
* :class:`IntentClassifier` — a plugin that returns a high-level
  :class:`Intent` for a given prompt (e.g. "build", "ask", "plan").
  Used by the top-level ``forge`` command.

Plugins are discovered via the ``forgecli.plugins`` entry-point
group; see :func:`discover_plugins`. A plugin's ``configure``
hook is invoked once at startup with the active
:class:`~forgecli.core.context.AppContext` so it can register
its own commands, providers, or analyzers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from forgecli.core.context import AppContext
from forgecli.providers.base import Provider
from forgecli.review.analyzer import Analyzer


class Intent(str, Enum):
    """A high-level description of what the user wants to do."""

    BUILD = "build"        # generate / modify code
    ASK = "ask"            # answer a question about the project
    PLAN = "plan"          # produce a plan without writing code
    DOCS = "docs"          # produce documentation
    REVIEW = "review"      # run the code review pipeline
    EXPLAIN = "explain"    # explain a single node / file
    COMMIT = "commit"      # generate a commit message
    UNKNOWN = "unknown"


@dataclass
class IntentPrediction:
    """The router's guess at what the user wants."""

    intent: Intent
    confidence: float
    rationale: tuple[str, ...] = ()


@dataclass
class PluginContext:
    """The shared state passed to a :class:`Workflow`."""

    app_context: AppContext
    prompt: str
    intent: Intent
    extras: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------


class Workflow(ABC):
    """A named, executable workflow.

    The top-level ``forge`` command dispatches to the first registered
    Workflow whose :meth:`can_handle` returns True for the active
    :class:`Intent` and prompt.
    """

    name: str = "abstract"
    intents: tuple[Intent, ...] = ()

    @abstractmethod
    async def run(self, context: PluginContext) -> dict[str, Any]:
        """Execute the workflow; return a result payload for the CLI."""

    @classmethod
    def can_handle(cls, intent: Intent, prompt: str) -> bool:
        """Return True if this workflow should run for ``intent``.

        Implemented as a classmethod so the registry can iterate
        over the workflow *classes* (not instances) and call
        ``can_handle`` directly.
        """
        return intent in cls.intents


class IntentClassifier(ABC):
    """A pluggable intent classifier."""

    name: str = "abstract"

    @abstractmethod
    def classify(self, prompt: str, *, history: tuple[str, ...] = ()) -> IntentPrediction:
        """Return the most likely :class:`Intent` for ``prompt``."""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass
class PluginRegistry:
    """In-memory registry of all loaded plugins."""

    providers: dict[str, type[Provider]] = field(default_factory=dict)
    optimizers: dict[str, type] = field(default_factory=dict)
    analyzers: list[type[Analyzer]] = field(default_factory=list)
    classifiers: list[IntentClassifier] = field(default_factory=list)
    workflows: list[Workflow] = field(default_factory=list)
    stages: dict[str, object] = field(default_factory=dict)  # type: ignore[type-arg]
    configure_hooks: list[Callable[[AppContext], None]] = field(default_factory=list)

    def register_provider(self, name: str, provider_cls: type[Provider]) -> None:
        self.providers[name] = provider_cls

    def register_optimizer(self, name: str, optimizer_cls: type) -> None:
        self.optimizers[name] = optimizer_cls

    def register_analyzer(self, analyzer_cls: type[Analyzer]) -> None:
        self.analyzers.append(analyzer_cls)

    def register_classifier(self, classifier: IntentClassifier) -> None:
        self.classifiers.append(classifier)

    def register_workflow(self, workflow: Workflow) -> None:
        self.workflows.append(workflow)

    def register_stage(self, stage) -> None:  # type: ignore[no-untyped-def]
        """Register a :class:`Stage` so the engine can pick it up by name."""
        if not getattr(stage, "name", None):
            raise ValueError("Stage.name must be non-empty")
        if stage.name in self.stages:
            raise ValueError(f"Stage {stage.name!r} already registered")
        self.stages[stage.name] = stage

    def replace_stage(self, stage) -> None:  # type: ignore[no-untyped-def]
        """Replace a registered :class:`Stage` (last-writer-wins)."""
        if not getattr(stage, "name", None):
            raise ValueError("Stage.name must be non-empty")
        self.stages[stage.name] = stage

    def register_configure_hook(
        self, hook: Callable[[AppContext], None]
    ) -> None:
        self.configure_hooks.append(hook)

    def classifiers_sorted(self) -> list[IntentClassifier]:
        return sorted(self.classifiers, key=lambda c: getattr(c, "priority", 100))


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_plugins(
    registry: PluginRegistry,
    group: str = "forgecli.plugins",
) -> list[str]:
    """Discover and load installed plugins via entry points.

    Each entry point must resolve to a callable that takes a
    :class:`PluginRegistry` (and optionally a
    :class:`~forgecli.core.context.AppContext`) and returns nothing.
    """
    import importlib.metadata as importlib_metadata

    loaded: list[str] = []
    try:
        entries = importlib_metadata.entry_points(group=group)
    except Exception:
        return loaded
    for ep in entries:
        try:
            plugin_factory = ep.load()
        except Exception:
            continue
        try:
            plugin_factory(registry)
            loaded.append(ep.name)
        except Exception:
            continue
    return loaded


__all__ = [
    "Intent",
    "IntentClassifier",
    "IntentPrediction",
    "PluginContext",
    "PluginRegistry",
    "Workflow",
    "discover_plugins",
]


# Silence unused-import warnings for symbols only used in some branches.
_ = Awaitable
