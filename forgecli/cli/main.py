"""Top-level Typer application for Forge."""

from __future__ import annotations

import contextlib
import signal
import warnings
from pathlib import Path

import typer

from forgecli import __app_name__, __version__
from forgecli.cli import commands_diagnostics, commands_graph, commands_wrappers
from forgecli.cli.bootstrap import bootstrap_context
from forgecli.cli.ui import error, get_console
from forgecli.core.errors import ForgeCLIError
from forgecli.runtime.agents import AGENTS

warnings.filterwarnings("ignore")

with contextlib.suppress(AttributeError):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

app = typer.Typer(
    name="forge",
    help="Forge — AI optimization runtime for Claude, Codex, Cursor, Antigravity, and Aider.",
    no_args_is_help=False,
    add_completion=False,
    rich_markup_mode="rich",
)

app.add_typer(commands_graph.app, name="graph")
for _agent_id, _agent in AGENTS.items():
    app.command(
        _agent_id,
        help=f"Launch {_agent.name} with Forge prompt + token optimization.",
        context_settings=commands_wrappers._WRAPPER_SETTINGS,
    )(commands_wrappers.make_agent_cmd(_agent_id))
app.command(
    "status",
    help="Show current repository, optimization, and daemon status.",
)(commands_diagnostics.status_cmd)
app.command(
    "doctor",
    help="Run system checks to verify Forge configuration and dependencies.",
)(commands_diagnostics.doctor_cmd)


@app.command("start", help="Start the long-running Forge Context Runtime daemon.")
def start_cmd(
    port: int = typer.Option(16868, "--port", "-p", help="Port to run the daemon HTTP server on."),
) -> None:
    """Start the long-running Forge Context Runtime daemon."""
    import uvicorn

    from forgecli.cli.daemon import get_watcher_for_path, is_daemon_running
    from forgecli.cli.ui import info, success

    if is_daemon_running():
        info("Forge Runtime daemon is already running on http://127.0.0.1:16868")
        raise typer.Exit(code=0)

    success("Starting Forge Runtime daemon on http://127.0.0.1:16868...")
    get_watcher_for_path(Path.cwd())

    from forgecli.cli.daemon import app as daemon_app

    uvicorn.run(daemon_app, host="127.0.0.1", port=port, log_level="warning")


@app.command("mcp", help="Start the Forge MCP Server over stdio.")
def mcp_cmd() -> None:
    """Start the Forge MCP Server over stdio."""
    from forgecli.cli.daemon import run_mcp_stdio

    run_mcp_stdio()


@app.command("config", help="Configure Forge settings, including optimization profiles.")
def config_cmd(
    ponytail: str = typer.Option(
        None,
        "--ponytail",
        "-p",
        help="Configure Ponytail optimization profile (off | lite | full | ultra).",
    ),
    caveman: str = typer.Option(
        None,
        "--caveman",
        "-c",
        help="Configure Caveman optimization profile (off | lite | full | ultra).",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Configure Output optimization profile (off | lite | full | ultra).",
    ),
) -> None:
    """Configure Forge settings, including optimization profiles."""
    from forgecli.cli.ui import get_console, info, success
    from forgecli.config.loader import ConfigLoader
    from forgecli.config.writer import update_config

    loader = ConfigLoader()
    try:
        settings = loader.load()
    except Exception:
        from forgecli.config.settings import ForgeSettings
        settings = ForgeSettings()

    if ponytail is None and caveman is None and output is None:
        p_val = settings.prompt_optimizer.intensity
        if not settings.prompt_optimizer.enabled or p_val not in {"off", "lite", "full", "ultra"}:
            p_val = "off" if not settings.prompt_optimizer.enabled else "lite"

        c_val = settings.caveman.intensity
        if not settings.caveman.enabled or c_val not in {"off", "lite", "full", "ultra"}:
            c_val = "off" if not settings.caveman.enabled else "lite"

        o_val = settings.output_optimization.intensity
        if not settings.output_optimization.enabled or o_val not in {"off", "lite", "full", "ultra"}:
            o_val = "off" if not settings.output_optimization.enabled else "lite"

        console = get_console()
        console.print()
        console.print("  [bold cyan]Forge Configuration[/bold cyan]")
        console.print(f"  Ponytail Profile : [white]{p_val}[/white]")
        console.print(f"  Caveman Profile  : [white]{c_val}[/white]")
        console.print(f"  Output Profile   : [white]{o_val}[/white]")
        console.print()
        return

    # Normalize and validate options
    if ponytail is not None:
        val = ponytail.lower().strip()
        if val not in {"off", "lite", "full", "ultra"}:
            info(f"Invalid Ponytail mode '{ponytail}'. Falling back to 'lite'.")
            ponytail = "lite"
        else:
            ponytail = val

    if caveman is not None:
        val = caveman.lower().strip()
        if val not in {"off", "lite", "full", "ultra"}:
            info(f"Invalid Caveman mode '{caveman}'. Falling back to 'lite'.")
            caveman = "lite"
        else:
            caveman = val

    if output is not None:
        val = output.lower().strip()
        if val not in {"off", "lite", "full", "ultra"}:
            info(f"Invalid Output mode '{output}'. Falling back to 'lite'.")
            output = "lite"
        else:
            output = val

    path = update_config(ponytail=ponytail, caveman=caveman, output_optimization=output)
    success(f"Config updated in [white]{path}[/white]")


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
    console.print("  [dim]Prompt + token optimization for AI coding CLIs.[/dim]\n")
    console.print(
        "  [bold]Commands[/bold]\n"
        "    [cyan]forge claude[/cyan]       Launch Claude Code with optimized context\n"
        "    [cyan]forge codex[/cyan]        Launch Codex CLI with optimized context\n"
        "    [cyan]forge cursor[/cyan]       Launch Cursor CLI with optimized context\n"
        "    [cyan]forge antigravity[/cyan]  Launch Antigravity CLI with optimized context\n"
        "    [cyan]forge aider[/cyan]        Launch Aider with optimized context\n"
        "    [cyan]forge start[/cyan]        Start the background context optimization daemon\n"
        "    [cyan]forge mcp[/cyan]          Start the stdio Model Context Protocol (MCP) server\n"
        "    [cyan]forge config[/cyan]       Configure Ponytail, Caveman, and Output optimization profiles\n"
        "    [cyan]forge status[/cyan]       Show repository, daemon, and optimization status\n"
        "    [cyan]forge doctor[/cyan]       Verify installation, dependencies, and configuration\n"
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
