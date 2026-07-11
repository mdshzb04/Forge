"""Sample ForgeCLI plugin demonstrating the plugin SDK.

This plugin registers:
- A custom AI provider (SampleProvider)
- A repository analyzer hook
- A context optimizer hook
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from forgecli.sdk.manager import PluginManager


def register_provider(manager: PluginManager) -> None:
    """Register the SampleProvider with the ForgeCLI runtime."""
    manager.register_provider("sample", SampleProvider)


def register_analyzer(manager: PluginManager) -> None:
    """Register a custom repository analyzer."""
    manager.register_repository_analyzer(SampleAnalyzer)


def register_optimizer(manager: PluginManager) -> None:
    """Register a custom context optimizer."""
    manager.register_optimizer("sample", SampleOptimizer)


class SampleProvider:
    """A sample AI provider that returns deterministic test responses."""

    name = "sample"

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health(self):
        from forgecli.providers.health import ProviderHealth, ProviderHealthState
        return ProviderHealth(state=ProviderHealthState.HEALTHY)

    async def send(self, context: Any) -> Any:
        from forgecli.runtime_core.response import AIResponse
        return AIResponse(
            response_id=f"resp-sample-{context.request_context.execution_id}",
            request_id=context.request_context.ai_request.request_id,
            content=f"[SamplePlugin] Processed: {context.request_context.ai_request.prompt[:100]}",
            finish_reason="stop",
            latency_ms=5.0,
        )

    def metadata(self):
        from forgecli.providers.provider_metadata import ProviderMetadata
        return ProviderMetadata(
            name="sample",
            version="1.0.0",
            default_model="sample-v1",
            supported_models=["sample-v1"],
            context_windows={"sample-v1": 8192},
        )

    def supports_streaming(self) -> bool:
        return False

    def supports_tools(self) -> bool:
        return False


class SampleAnalyzer:
    """A sample repository analyzer that logs file counts."""

    def analyze(self, repo_root: str) -> dict[str, Any]:
        from pathlib import Path
        root = Path(repo_root)
        files = list(root.rglob("*.py")) if root.exists() else []
        return {
            "analyzer": "sample",
            "file_count": len(files),
            "language": "python",
        }


class SampleOptimizer:
    """A sample context optimizer that trims verbose comments."""

    def optimize(self, context: str) -> str:
        # Strip lines that are pure comments
        lines = context.split("\n")
        filtered = [
            line for line in lines
            if not line.strip().startswith("# TODO") and not line.strip().startswith("# FIXME")
        ]
        return "\n".join(filtered)
