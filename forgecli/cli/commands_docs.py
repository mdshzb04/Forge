"""``forge docs`` subcommand: auto-generate project documentation."""

from __future__ import annotations

from pathlib import Path

import typer

from forgecli.cli.bootstrap import bootstrap_context
from forgecli.cli.ui import error, get_console, success
from forgecli.docs.generator import generate_docs

app = typer.Typer(
    help="Auto-generate a project overview from the knowledge graph.",
    invoke_without_command=True,
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def docs_cmd(
    ctx: typer.Context,
    path: str = typer.Option(".", "--path", "-p", help="Project root."),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Override the output file (default: docs/OVERVIEW.md)."
    ),
) -> None:
    """Generate an overview of the current project."""
    if ctx.invoked_subcommand is not None:
        return
    context = bootstrap_context(cwd=path)
    try:
        target = generate_docs(context, output=output)
    except Exception as exc:
        error(f"Failed to generate docs: {exc}")
        raise typer.Exit(code=1) from exc
    success(f"Documentation written to {target}")
    get_console().print(f"  [muted]{target}[/muted]")


__all__ = ["app"]
