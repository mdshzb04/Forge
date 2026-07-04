"""Wrapper commands: forge claude | codex | cursor | opencode | commandcode."""

from __future__ import annotations

from pathlib import Path

import typer

from forgecli.runtime.wrappers import launch_wrapper

_WRAPPER_SETTINGS = {
    "allow_extra_args": True,
    "allow_interspersed_args": True,
    "ignore_unknown_options": True,
}


def claude_cmd(
    ctx: typer.Context,
    path: str = typer.Option(".", "--path", "-p", help="Project root."),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass cached Forge context."),
) -> None:
    """Launch Claude Code with Forge prompt + token optimization."""
    launch_wrapper("claude", list(ctx.args), path=Path(path), force_prepare=refresh)


def codex_cmd(
    ctx: typer.Context,
    path: str = typer.Option(".", "--path", "-p", help="Project root."),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass cached Forge context."),
) -> None:
    """Launch Codex CLI with Forge prompt + token optimization."""
    launch_wrapper("codex", list(ctx.args), path=Path(path), force_prepare=refresh)


def cursor_cmd(
    ctx: typer.Context,
    path: str = typer.Option(".", "--path", "-p", help="Project root."),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass cached Forge context."),
) -> None:
    """Launch Cursor CLI with Forge prompt + token optimization."""
    launch_wrapper("cursor", list(ctx.args), path=Path(path), force_prepare=refresh)


def opencode_cmd(
    ctx: typer.Context,
    path: str = typer.Option(".", "--path", "-p", help="Project root."),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass cached Forge context."),
) -> None:
    """Launch OpenCode CLI with Forge prompt + token optimization."""
    launch_wrapper("opencode", list(ctx.args), path=Path(path), force_prepare=refresh)


def commandcode_cmd(
    ctx: typer.Context,
    path: str = typer.Option(".", "--path", "-p", help="Project root."),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass cached Forge context."),
) -> None:
    """Launch CommandCode CLI with Forge prompt + token optimization."""
    launch_wrapper("commandcode", list(ctx.args), path=Path(path), force_prepare=refresh)


__all__ = ["_WRAPPER_SETTINGS", "claude_cmd", "codex_cmd", "commandcode_cmd", "cursor_cmd", "opencode_cmd"]
