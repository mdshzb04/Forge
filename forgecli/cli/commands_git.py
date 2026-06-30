"""``forgecli git`` subcommand group."""

from __future__ import annotations

from pathlib import Path

import typer

from forgecli.cli.ui import success
from forgecli.core.errors import GitError

app = typer.Typer(
    help="Inspect and operate on the git repository.",
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context) -> None:
    """Inspect and operate on the git repository."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(status)


@app.command("status")
def status() -> None:
    """Show repository status."""
    try:
        from forgecli.git.repo import GitRepo
        repo = GitRepo(Path.cwd())
    except GitError as exc:
        raise typer.Exit(code=1) from exc
    success(f"Branch: {repo.status().get('branch', 'unknown')}")


__all__ = ["app"]
