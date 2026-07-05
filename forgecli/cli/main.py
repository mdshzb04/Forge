"""Top-level Typer application for Forge."""

from __future__ import annotations

import contextlib
import signal
import warnings
from pathlib import Path
from typing import Any

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
app.command(
    "antigravity",
    help="Launch Antigravity CLI with Forge prompt + token optimization.",
    context_settings=commands_wrappers._WRAPPER_SETTINGS,
)(commands_wrappers.antigravity_cmd)


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


@app.command(
    "stats",
    help="Display the prompt and token optimization statistics from the latest wrapper runs.",
)
def stats_cmd() -> None:
    """Display the prompt and token optimization statistics from the latest wrapper runs."""
    from forgecli.cli.ui import get_console
    from forgecli.utils.stats import get_stats_history

    history = get_stats_history()
    if not history:
        get_console().print("No optimization statistics available yet.")
        return

    console = get_console()
    console.print()

    def format_precision_time(val: Any) -> str:
        try:
            seconds = float(val)
            if seconds < 0.001:
                return "<0.001 s"
            return f"{seconds:.3f} s"
        except (ValueError, TypeError):
            return "N/A"

    for idx, run in enumerate(history):
        run_title = "[bold cyan]Forge Optimization Report"
        if len(history) > 1:
            run_title += f" (Run #{idx + 1}"
            if idx == 0:
                run_title += " - Latest"
            run_title += ")"
        run_title += "[/bold cyan]"

        console.print(run_title)

        status_raw = run.get("status")
        if not status_raw:
            if run.get("cli_used") == "graph":
                status_raw = "Graph Built"
            elif "hit" in str(run.get("cache_status", "")).lower():
                status_raw = "Cache Reused"
            elif run.get("reduction_tokens", 0) > 0:
                status_raw = "Optimized Successfully"
            else:
                status_raw = "No optimization required"

        if status_raw == "Optimized Successfully":
            status_display = "[green]✓ Optimized Successfully[/green]"
        elif status_raw == "Cache Reused":
            status_display = "[green]✓ Cache Reused[/green]"
        elif status_raw == "Graph Built":
            status_display = "[green]✓ Graph Built[/green]"
        else:
            status_display = "[yellow]⚠ No optimization required[/yellow]"

        cli_raw = run.get("cli_used", "N/A")
        cli_display = cli_raw.capitalize() if isinstance(cli_raw, str) else str(cli_raw)

        console.print(f"Status              : {status_display}")
        console.print(f"Repository          : [white]{run.get('repo_name', 'N/A')}[/white]")
        console.print(f"AI CLI              : [white]{cli_display}[/white]")
        console.print()

        # Repository Context section
        console.print("[bold]Repository Context[/bold]")
        console.print("[dim]────────────────────────[/dim]")

        red_abs = run.get("reduction_tokens", 0)
        red_pct = run.get("reduction_pct", 0.0)

        if red_abs <= 0:
            console.print(
                "[yellow]Repository already fits within the optimization budget.[/yellow]"
            )
        else:
            console.print(
                f"Original Context Size      : [white]{run.get('original_tokens', 0):,} tokens (estimated)[/white]"
            )
            console.print(
                f"Optimized Context Size     : [white]{run.get('optimized_tokens', 0):,} tokens (estimated)[/white]"
            )
            console.print(f"Estimated Tokens Saved     : [green]{red_abs:,}[/green]")
            console.print(f"Context Compression        : [green]{red_pct:.1f}%[/green]")
            console.print("Context Budget             : [white]8,000 tokens[/white]")
        console.print()

        # Optimization section
        console.print("[bold]Optimization[/bold]")
        console.print("[dim]────────────────────────[/dim]")

        prompt_opt_raw = run.get("prompt_opt_status", "Disabled")
        prompt_opt_display = "Enabled" if "enable" in str(prompt_opt_raw).lower() else "Disabled"

        token_opt_raw = run.get("token_opt_status", "Disabled")
        token_opt_display = "Enabled" if "enable" in str(token_opt_raw).lower() else "Disabled"

        cache_status_raw = run.get("cache_status", "MISS")
        cache_status_display = "HIT" if "hit" in str(cache_status_raw).lower() else "MISS"

        kg_cache_raw = run.get("kg_cache", "Cache Miss")
        kg_cache_display = "Cache HIT" if "hit" in str(kg_cache_raw).lower() else "Cache MISS"

        console.print(f"Files Scanned             : [white]{run.get('files_scanned', 0)}[/white]")
        console.print(f"Relevant Files            : [white]{run.get('files_count', 0)}[/white]")
        console.print(f"Excluded Files            : [white]{run.get('excluded_files', 0)}[/white]")
        console.print(f"Knowledge Graph           : [white]{kg_cache_display}[/white]")
        console.print(
            f"Preparation Time          : [white]{format_precision_time(run.get('prep_time', 0.0))}[/white]"
        )

        graph_build = run.get("graph_build_time")
        if graph_build is not None:
            console.print(
                f"Graph Build Time          : [white]{format_precision_time(graph_build)}[/white]"
            )

        console.print(f"Prompt Optimization       : [white]{prompt_opt_display}[/white]")
        console.print(f"Token Optimization        : [white]{token_opt_display}[/white]")
        console.print(f"Cache Status              : [white]{cache_status_display}[/white]")
        console.print(f"Timestamp                 : [muted]{run.get('timestamp', 'N/A')}[/muted]")

        if idx < len(history) - 1:
            console.print()
            console.print("[dim]==================================================[/dim]")
            console.print()


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
        "    [cyan]forge opencode[/cyan]     Launch OpenCode CLI with optimized context\n"
        "    [cyan]forge commandcode[/cyan]  Launch CommandCode CLI with optimized context\n"
        "    [cyan]forge antigravity[/cyan]  Launch Antigravity CLI with optimized context\n"
        "    [cyan]forge start[/cyan]        Start the background context optimization daemon\n"
        "    [cyan]forge mcp[/cyan]          Start the stdio Model Context Protocol (MCP) server\n"
        "    [cyan]forge stats[/cyan]        Display optimization statistics\n"
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
