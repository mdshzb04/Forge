"""Top-level Typer application for Forge."""

from __future__ import annotations

import contextlib
import signal
import warnings
from pathlib import Path

import typer

from forgecli import __app_name__, __version__
from forgecli.cli import commands_graph, commands_wrappers
from forgecli.cli.bootstrap import bootstrap_context
from forgecli.cli.ui import error, get_console
from forgecli.core.errors import ForgeCLIError

warnings.filterwarnings("ignore")

with contextlib.suppress(AttributeError):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

app = typer.Typer(
    name="forge",
    help="Forge — AI optimization runtime for Claude Code, Codex, Cursor, OpenCode, and CommandCode CLI.",
    no_args_is_help=False,
    add_completion=False,
    rich_markup_mode="rich",
)

app.add_typer(commands_graph.app, name="graph")
app.command(
    "claude",
    help="Launch Claude Code with Forge prompt + token optimization.",
    context_settings=commands_wrappers._WRAPPER_SETTINGS,
)(commands_wrappers.claude_cmd)
app.command(
    "codex",
    help="Launch Codex CLI with Forge prompt + token optimization.",
    context_settings=commands_wrappers._WRAPPER_SETTINGS,
)(commands_wrappers.codex_cmd)
app.command(
    "cursor",
    help="Launch Cursor CLI with Forge prompt + token optimization.",
    context_settings=commands_wrappers._WRAPPER_SETTINGS,
)(commands_wrappers.cursor_cmd)
app.command(
    "opencode",
    help="Launch OpenCode CLI with Forge prompt + token optimization.",
    context_settings=commands_wrappers._WRAPPER_SETTINGS,
)(commands_wrappers.opencode_cmd)
app.command(
    "commandcode",
    help="Launch CommandCode CLI with Forge prompt + token optimization.",
    context_settings=commands_wrappers._WRAPPER_SETTINGS,
)(commands_wrappers.commandcode_cmd)


def _version_callback(value: bool) -> None:
    if value:
        get_console().print(f"{__app_name__} [muted]v{__version__}[/muted]")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to a forgecli.toml file.",
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging."),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """Forge global entry point."""
    bootstrap_context(config_path=config, extras={"verbose": verbose})
    if ctx.invoked_subcommand is not None:
        return

    console = get_console()
    console.print()
    console.print(
        f"  [bold cyan]Forge[/bold cyan] [dim]v{__version__}[/dim] • "
        "[bold white]AI Optimization Runtime[/bold white]"
    )
    console.print(
        "  [dim]Prompt + token optimization for AI coding CLIs.[/dim]\n"
    )
    console.print(
        "  [bold]Commands[/bold]\n"
        "    [cyan]forge claude[/cyan]       Launch Claude Code with optimized context\n"
        "    [cyan]forge codex[/cyan]        Launch Codex CLI with optimized context\n"
        "    [cyan]forge cursor[/cyan]       Launch Cursor CLI with optimized context\n"
        "    [cyan]forge opencode[/cyan]     Launch OpenCode CLI with optimized context\n"
        "    [cyan]forge commandcode[/cyan]  Launch CommandCode CLI with optimized context\n"
        "    [cyan]forge graph build[/cyan]  Build a full knowledge graph (optional)\n"
        "    [cyan]forge --help[/cyan]       Show all options\n"
    )


def _run() -> None:
    """Run the Typer app and translate ForgeCLIError to clean exit codes."""
    try:
        app()
    except ForgeCLIError as exc:
        error(str(exc))
        raise SystemExit(2) from exc


if __name__ == "__main__":
    _run()


__all__ = ["app", "main"]
