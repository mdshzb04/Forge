"""Default stage wiring for the Execution Engine.

Provides :func:`default_registry` which populates a
:class:`~forgecli.engine.execution.StageRegistry` with all eight
DEFAULT_PIPELINE stages. Callers can then build an engine with::

    registry = default_registry()
    engine = ExecutionEngine.from_registry(registry)
    result = await engine.run(context)

Individual stages can be overridden via
:meth:`StageRegistry.replace` before building the engine.
"""



from __future__ import annotations

from typing import Any

from forgecli.engine.execution import Stage, StageRegistry
from forgecli.engine.stages import (
    ContextOptimizerStage,
    ExecutionEngineStage,
    GitEngineStage,
    IntentAnalyzerStage,
    ModelRouterStage,
    PlanningEngineStage,
    RepositoryAnalyzerStage,
    ResponseForgeOptimizerStage,
    ValidationEngineStage,
)


def default_registry(

    *,

    provider: Any = None,

    optimizer: Any = None,

    responseforge_optimizer: Any = None,

    graph: Any = None,

    classifier: Any = None,

    router: Any = None,

    test_command: str | None = None,

    plugin_registry: Any = None,

    **stage_kwargs: Any,

) -> StageRegistry:

    """Create a :class:`StageRegistry` with all nine default pipeline stages.

    Keyword arguments are forwarded to stage constructors:

    * ``provider`` → :class:`ExecutionEngineStage`
    * ``optimizer`` → :class:`ContextOptimizerStage`
    * ``responseforge_optimizer`` → :class:`ResponseForgeOptimizerStage`
    * ``graph`` → :class:`RepositoryAnalyzerStage`
    * ``classifier`` → :class:`IntentAnalyzerStage`
    * ``router`` → :class:`ModelRouterStage`
    * ``test_command`` → :class:`ValidationEngineStage`
    * ``plugin_registry`` → a :class:`~forgecli.plugins.PluginRegistry` whose
      stages are bulk-loaded into the registry after default stages.
      The plugin registry is also linked so future
      :meth:`~forgecli.plugins.PluginRegistry.register_stage` /
      :meth:`~forgecli.plugins.PluginRegistry.replace_stage` calls
      are mirrored into this registry.

    Remaining kwargs are passed to stages that accept them by name
    (e.g. ``auto_commit`` for :class:`GitEngineStage`).
    """

    registry = StageRegistry()



    stages: list[Stage] = [

        IntentAnalyzerStage(classifier=classifier),

        RepositoryAnalyzerStage(graph=graph),

        ResponseForgeOptimizerStage(optimizer=responseforge_optimizer),

        ContextOptimizerStage(optimizer=optimizer),

        PlanningEngineStage(**{k: v for k, v in stage_kwargs.items() if k in ("enabled",)}),

        ModelRouterStage(router=router),

        ExecutionEngineStage(provider=provider),

        ValidationEngineStage(test_command=test_command),

        GitEngineStage(),

    ]



    for stage in stages:

        registry.register(stage)



    if plugin_registry is not None:

        plugin_registry.link_engine_registry(registry)



    return registry





__all__ = ["default_registry"]

