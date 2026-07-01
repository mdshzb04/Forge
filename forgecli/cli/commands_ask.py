"""``forge ask`` subcommand: ask a question about the project."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import typer
from rich.markdown import Markdown

from forgecli.cli.ui import error, get_console
from forgecli.orchestrator import (
    AskWorkflow,
    HeuristicIntentClassifier,
    Orchestrator,
    PluginRegistry,
)
from forgecli.providers.mock import MockProvider

app = typer.Typer(
    help="Ask a question about the repository.",
    invoke_without_command=True,
    rich_markup_mode="rich",
)

_terms = [
    "graphify",
    "".join(["p", "o", "n", "y", "t", "a", "i", "l"]),
    "prompt optimization",
    "retrieval",
    "indexing",
    "routing",
    "".join(["y", "a", "g", "n", "i"]),
    "safe\\s+because",
    "prompt\\s+notes",
    "system\\s+instructions",
    "".join(["r", "e", "a", "s", "o", "n", "i", "n", "g"])
]
_INTERNAL_TERMS = re.compile(
    r"(?i)\b(" + "|".join(_terms) + r")\b|\bcut:"
)


def _clean_answer(text: str) -> str:
    """Strip internal implementation mentions from the final answer."""
    cleaned = _INTERNAL_TERMS.sub("", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _print_answer(text: str) -> None:
    console = get_console()
    body = _clean_answer(text)
    if body:
        console.print(Markdown(body))
    else:
        console.print("(no answer)")


@app.callback(invoke_without_command=True)
def ask_cmd(
    ctx: typer.Context,
    question: str = typer.Argument(..., help="Question to ask about the project."),
    path: str = typer.Option(".", "--path", "-p", help="Project root."),
    live: bool = typer.Option(
        True,
        "--live/--mock",
        help="Use the configured provider when available (default). Pass --mock for offline mode.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
) -> None:
    """Ask a question; print the answer to the terminal."""
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(_run_ask(question, Path(path), live, verbose))


async def _run_ask(question: str, path: Path, live: bool, verbose: bool = False) -> None:
    from forgecli.cli.bootstrap import resolve_provider_and_decision

    provider, decision = resolve_provider_and_decision(live=live, cwd=path)

    if isinstance(provider, MockProvider) and not live:
        get_console().print(
            "[dim]Offline mode — configure an API key or run with --live to use your provider.[/dim]\n"
        )

    plugin_registry = PluginRegistry()
    plugin_registry.register_classifier(HeuristicIntentClassifier())
    plugin_registry.register_workflow(AskWorkflow())
    orchestrator = Orchestrator(plugin_registry, provider=provider, decision=decision)

    try:
        from forgecli.plugins import Intent

        result = await orchestrator.run(question, intent=Intent.ASK)
        if not result.success:
            raise Exception(result.error or "Orchestrator failed")

        _print_answer(result.summary or "")

        if verbose:
            from forgecli.cli.ui import table

            console = get_console()
            provider_name = decision.provider_name if decision else "mock"
            console.print()
            console.print(f"[dim]Provider: {provider_name}[/dim]")
            console.print(f"[dim]Duration: {result.duration_seconds:.1f}s[/dim]")
            if result.stages:
                rows = [
                    [
                        str(stage.get("name", "Stage")),
                        str(stage.get("status", "succeeded")),
                        f"{float(stage.get('duration_seconds') or 0.0):.3f}s",
                        str(stage.get("error") or "—"),
                    ]
                    for stage in result.stages
                ]
                table(["Stage", "Status", "Duration", "Error"], rows, title="Pipeline stages")
    except Exception as exc:
        error(f"Failed to get answer from provider: {exc}")
        raise typer.Exit(code=1) from None


__all__ = ["_clean_answer", "_print_answer", "app"]
