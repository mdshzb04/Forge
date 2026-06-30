"""``forge explain`` top-level command."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from forgecli.cli.ui import error, get_console
from forgecli.orchestrator import (
    ExplainWorkflow,
    HeuristicIntentClassifier,
    Orchestrator,
    PluginRegistry,
)

app = typer.Typer(
    help="Explain a node, file, or symbol using the Graphify knowledge graph and LLM.",
    invoke_without_command=True,
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="Node label, id, or filename to explain."),
    path: str = typer.Option(".", "--path", "-p", help="Project root."),
    live: bool = typer.Option(True, "--live/--mock", help="Use the real provider chosen by the router (default: True)."),
) -> None:
    """Explain a node, file, or symbol using the Graphify knowledge graph and LLM."""
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(_run_explain(target, Path(path), live))


async def _run_explain(target: str, path: Path, live: bool) -> None:
    from forgecli.providers.base import Provider
    from forgecli.providers.mock import MockProvider, MockProviderConfig

    provider: Provider = MockProvider(MockProviderConfig())
    if live:
        from forgecli.cli.bootstrap import bootstrap_context
        from forgecli.providers.base import ProviderRegistry
        from forgecli.providers.router_state import load_state

        app_context = bootstrap_context(cwd=str(path))
        state = load_state(app_context.paths.data_dir / "router.json")
        registry: ProviderRegistry = app_context.container.resolve(ProviderRegistry)

        chosen = state.choice or state.provider
        if not chosen:
            from forgecli.config.loader import ConfigLoader
            try:
                settings = ConfigLoader().load()
                chosen = settings.providers.default
            except Exception:
                pass

        if not chosen or chosen == "mock":
            error(
                "No active provider configured.\n"
                "Please configure a provider first:\n"
                "  1. Authenticate using 'forge auth login'\n"
                "  2. Select your active provider using 'forge provider use <provider>'\n"
                "  3. Select your active model using 'forge model use <model>'"
            )
            raise typer.Exit(code=1)

        if not registry.has(chosen):
            error(f"Unknown provider '{chosen}'.")
            raise typer.Exit(code=1)

        provider_cls = registry.get(chosen)
        provider = provider_cls()  # type: ignore[call-arg]

    if isinstance(provider, MockProvider):
        if live:
            error(
                "No active provider configured.\n"
                "Please configure a provider first:\n"
                "  1. Authenticate using 'forge auth login'\n"
                "  2. Select your active provider using 'forge provider use <provider>'\n"
                "  3. Select your active model using 'forge model use <model>'"
            )
            raise typer.Exit(code=1)
        else:
            from forgecli.cli.ui import info
            info("Offline mode: using the mock provider. Pass --live to use the real one.")

    plugin_registry = PluginRegistry()
    plugin_registry.register_classifier(HeuristicIntentClassifier())
    plugin_registry.register_workflow(ExplainWorkflow())
    orchestrator = Orchestrator(plugin_registry, provider=provider)

    try:
        from forgecli.plugins import Intent
        result = await orchestrator.run(target, intent=Intent.EXPLAIN)
        if not result.success:
            raise Exception(result.error or "Orchestrator failed")

        get_console().print()
        get_console().print(result.summary or "(no explanation)")
    except Exception as exc:
        error(f"Failed to get explanation from provider: {exc}")
        raise typer.Exit(code=1) from exc


__all__ = ["app"]
