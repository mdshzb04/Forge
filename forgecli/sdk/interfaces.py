"""The 10 canonical plugin extension points.

Every ForgeCLI plugin declares one or more of these. Each interface
is a :class:`typing.Protocol` with a single async or sync ``register``
method; the SDK calls the method when the plugin is enabled.

Adding a new plugin category is intentionally hard: the SDK exposes
exactly these ten categories and the engine only looks for them by
name. Plugin authors who want a new category should add a new
:class:`EntryPointKind` to :mod:`forgecli.sdk.manifest`.
"""



from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover - type hints only

    from forgecli.sdk.manager import PluginManager













@runtime_checkable

class PluginConfigurable(Protocol):

    """A plugin that exposes user-configurable values.

    Plugins implementing this protocol may return a dict from
    :meth:`default_config`; the SDK merges that into the persisted
    configuration under ``plugin.<name>``. The dict may contain any
    JSON-serialisable values.
    """



    def default_config(self) -> dict[str, Any]: ...















@runtime_checkable

class PluginHealthCheck(Protocol):

    """A plugin that exposes a synchronous health probe.

    The SDK calls :meth:`health` whenever ``forge plugin doctor``
    is invoked; the returned list of :class:`HealthIssue` items is
    surfaced in the doctor report.
    """



    def health(self) -> list[HealthIssue]: ...















@runtime_checkable

class AIProviderPlugin(Protocol):

    """Register a custom AI provider with the router.

    The plugin's :meth:`register` is called with the
    :class:`~forgecli.plugins.PluginRegistry`; the plugin calls
    :meth:`PluginRegistry.register_provider` to add itself.
    """



    name: str



    def register(self, manager: PluginManager) -> None: ...















@runtime_checkable

class RepositoryAnalyzerPlugin(Protocol):

    """Register a :class:`RepositoryAnalyzer` with the review engine.

    The plugin's :meth:`register` is called with the manager; the
    plugin calls :meth:`PluginManager.register_repository_analyzer`.
    """



    name: str



    def register(self, manager: PluginManager) -> None: ...















@runtime_checkable

class ContextOptimizerPlugin(Protocol):

    """Register a :class:`PromptOptimizer` with the engine."""



    name: str



    def register(self, manager: PluginManager) -> None: ...















@runtime_checkable

class CodeGeneratorPlugin(Protocol):

    """Register a code generator (e.g. a custom executor)."""



    name: str



    def register(self, manager: PluginManager) -> None: ...















@runtime_checkable

class TestRunnerPlugin(Protocol):

    """Register a custom test runner.

    The plugin's :meth:`register` is called with the manager; the
    plugin can use ``manager.register_test_runner(name, callback)``
    to register a callable that the engine will use to run tests
    on a project.
    """



    name: str



    def register(self, manager: PluginManager) -> None: ...















@runtime_checkable

class GitProviderPlugin(Protocol):

    """Register a custom Git provider.

    The plugin's :meth:`register` is called with the manager; the
    plugin can replace or extend ``manager.git_service`` with its
    own implementation.
    """



    name: str



    def register(self, manager: PluginManager) -> None: ...















@runtime_checkable

class DocumentationGeneratorPlugin(Protocol):

    """Register a documentation generator.

    The plugin's :meth:`register` is called with the manager; the
    plugin calls :meth:`PluginManager.register_docs_generator`.
    """



    name: str



    def register(self, manager: PluginManager) -> None: ...















@runtime_checkable

class DeploymentProviderPlugin(Protocol):

    """Register a deployment provider (CI, cloud, package manager)."""



    name: str



    def register(self, manager: PluginManager) -> None: ...















@runtime_checkable

class ObservabilityProviderPlugin(Protocol):

    """Register an observability provider (metrics, tracing, logs)."""



    name: str



    def register(self, manager: PluginManager) -> None: ...















@runtime_checkable

class NotificationProviderPlugin(Protocol):

    """Register a notification sink (Slack, email, webhook)."""



    name: str



    def register(self, manager: PluginManager) -> None: ...















@dataclass(frozen=True)

class HealthIssue:

    """A single result from a plugin's health probe."""



    severity: str

    message: str

    suggestion: str | None = None





@dataclass(frozen=True)

class HealthReport:

    """The aggregated health report for a single plugin."""



    plugin_name: str

    issues: tuple[HealthIssue, ...] = ()

    healthy: bool = True



    def to_dict(self) -> dict[str, object]:

        return {

            "plugin": self.plugin_name,

            "healthy": self.healthy,

            "issues": [

                {

                    "severity": issue.severity,

                    "message": issue.message,

                    "suggestion": issue.suggestion,

                }

                for issue in self.issues

            ],

        }







if False:  # pragma: no cover - type hints only

    from forgecli.sdk.manager import PluginManager





__all__ = [

    "AIProviderPlugin",

    "CodeGeneratorPlugin",

    "ContextOptimizerPlugin",

    "DeploymentProviderPlugin",

    "DocumentationGeneratorPlugin",

    "GitProviderPlugin",

    "HealthIssue",

    "HealthReport",

    "NotificationProviderPlugin",

    "ObservabilityProviderPlugin",

    "PluginConfigurable",

    "PluginHealthCheck",

    "RepositoryAnalyzerPlugin",

    "TestRunnerPlugin",

]

