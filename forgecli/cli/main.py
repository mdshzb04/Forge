"""Top-level Typer application for Forge."""



from __future__ import annotations

import contextlib
import signal
import warnings
from pathlib import Path

import typer

from forgecli import __app_name__, __version__
from forgecli.cli import commands_auth, commands_diagnostics, commands_graph, commands_wrappers
from forgecli.cli.bootstrap import bootstrap_context
from forgecli.cli.commands_commit import commit_cmd
from forgecli.cli.commands_inspect import inspect_cmd
from forgecli.cli.ui import error, get_console
from forgecli.core.errors import ForgeCLIError
from forgecli.runtime.agents import AGENTS

warnings.filterwarnings("ignore")



with contextlib.suppress(AttributeError):

    signal.signal(signal.SIGPIPE, signal.SIG_DFL)



app = typer.Typer(

    name="forge",

    help="Forge — pre-launch context preparation for Claude, Codex, Cursor, and Antigravity.",

    no_args_is_help=False,

    add_completion=False,

    rich_markup_mode="rich",

)



app.add_typer(commands_graph.app, name="graph")
app.add_typer(commands_auth.app, name="auth")

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

app.command(

    "inspect",

    help="Display the active pipeline, provider, ForgeGraph status, and optimization stages.",

)(inspect_cmd)

app.command(

    "stats",

    help="Show Forge usage statistics, cache metrics, and pipeline performance.",

)(commands_diagnostics.stats_cmd)

app.command(

    "profile",

    help="View or set optimization profiles (PromptForge, ResponseForge).",

)(commands_diagnostics.profile_cmd)

app.command(
    "explain",
    help="Explain Forge concepts, pipeline stages, or diagnostics.",
)(commands_diagnostics.explain_cmd)

app.command(
    "commit",
    help="Generate a Conventional Commit message from staged changes and commit them.",
)(commit_cmd)





@app.command("start", help="Start the long-running Forge Context Runtime daemon.")

def start_cmd(

    port: int = typer.Option(16868, "--port", "-p", help="Port to run the daemon HTTP server on."),

) -> None:

    """Start the long-running Forge Context Runtime daemon."""

    import uvicorn

    from forgecli.cli.daemon import get_watcher_for_path
    from forgecli.cli.daemon_utils import check_daemon_health
    from forgecli.cli.ui import info, success



    if check_daemon_health():

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
    promptforge: str = typer.Option(
        None,
        "--promptforge",
        "-p",
        help="Configure PromptForge optimization profile (off | lite | full | ultra).",
    ),
    responseforge: str = typer.Option(
        None,
        "--responseforge",
        "-c",
        help="Configure ResponseForge optimization profile (off | lite | full | ultra).",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Configure Output optimization profile (off | lite | full | ultra).",
    ),
    loop_pattern: str = typer.Option(
        None,
        "--loop-pattern",
        help="Set the loop-engineering pattern string used in prompts.",
    ),
    claude_usd_limit: float = typer.Option(
        None,
        "--claude-usd-limit",
        help="Set a USD usage cap for Claude Code.",
    ),
    cursor_usd_limit: float = typer.Option(
        None,
        "--cursor-usd-limit",
        help="Set a USD usage cap for Cursor.",
    ),
    codex_usd_limit: float = typer.Option(
        None,
        "--codex-usd-limit",
        help="Set a USD usage cap for Codex.",
    ),
    antigravity_usd_limit: float = typer.Option(
        None,
        "--antigravity-usd-limit",
        help="Set a USD usage cap for Antigravity.",
    ),
    loop_enabled: bool | None = typer.Option(
        None,
        "--loop-enabled/--no-loop-enabled",
        help="Enable or disable loop-engineering prompts and caps.",
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

    if (
        promptforge is None
        and responseforge is None
        and output is None
        and loop_pattern is None
        and claude_usd_limit is None
        and cursor_usd_limit is None
        and codex_usd_limit is None
        and antigravity_usd_limit is None
        and loop_enabled is None
    ):
        p_val = settings.prompt_optimizer.intensity
        if not settings.prompt_optimizer.enabled or p_val not in {"off", "lite", "full", "ultra"}:
            p_val = "off" if not settings.prompt_optimizer.enabled else "lite"

        c_val = settings.responseforge.intensity
        if not settings.responseforge.enabled or c_val not in {"off", "lite", "full", "ultra"}:
            c_val = "off" if not settings.responseforge.enabled else "lite"

        o_val = settings.output_optimization.intensity
        if not settings.output_optimization.enabled or o_val not in {"off", "lite", "full", "ultra"}:
            o_val = "off" if not settings.output_optimization.enabled else "lite"

        loop = settings.loop_engineering
        console = get_console()
        console.print()
        console.print("  [bold cyan]Forge Configuration[/bold cyan]")
        console.print(f"  PromptForge Profile : [white]{p_val}[/white]")
        console.print(f"  ResponseForge Profile  : [white]{c_val}[/white]")
        console.print(f"  Output Profile   : [white]{o_val}[/white]")
        console.print(f"  Loop Pattern     : [white]{loop.pattern}[/white]")
        console.print(f"  Claude USD Limit : [white]{loop.claude_usd_limit}[/white]")
        console.print(f"  Cursor USD Limit : [white]{loop.cursor_usd_limit}[/white]")
        console.print(f"  Codex USD Limit  : [white]{loop.codex_usd_limit}[/white]")
        console.print(f"  Antigravity USD  : [white]{loop.antigravity_usd_limit}[/white]")
        console.print()
        return

    if promptforge is not None:
        val = promptforge.lower().strip()
        if val not in {"off", "lite", "full", "ultra"}:
            info(f"Invalid PromptForge mode '{promptforge}'. Falling back to 'lite'.")
            promptforge = "lite"
        else:
            promptforge = val

    if responseforge is not None:
        val = responseforge.lower().strip()
        if val not in {"off", "lite", "full", "ultra"}:
            info(f"Invalid ResponseForge mode '{responseforge}'. Falling back to 'lite'.")
            responseforge = "lite"
        else:
            responseforge = val

    if output is not None:
        val = output.lower().strip()
        if val not in {"off", "lite", "full", "ultra"}:
            info(f"Invalid Output mode '{output}'. Falling back to 'lite'.")
            output = "lite"
        else:
            output = val

    path = update_config(
        promptforge=promptforge,
        responseforge=responseforge,
        output_optimization=output,
        loop_engineering_pattern=loop_pattern,
        claude_usd_limit=claude_usd_limit,
        cursor_usd_limit=cursor_usd_limit,
        codex_usd_limit=codex_usd_limit,
        antigravity_usd_limit=antigravity_usd_limit,
        loop_engineering_enabled=loop_enabled,
    )

    success(f"Config updated in [white]{path}[/white]")


@app.command("loop", help="Scaffold and run the Forge-native loop engineering workflow.")
def loop_cmd(
    path: Path = typer.Option(".", "--path", "-p", help="Project root."),
    refresh: bool = typer.Option(False, "--refresh", help="Refresh the prepared Forge context."),
    tool: str = typer.Option(
        "claude",
        "--tool",
        help="Preferred loop tool: claude | cursor | codex | antigravity.",
    ),
    task: str = typer.Option(
        "",
        "--task",
        help="Optional short task label to store in the loop state.",
    ),
) -> None:
    """Scaffold loop files, write the budget config, and print the workflow state."""
    from datetime import datetime, timezone

    from forgecli.cli.ui import get_console, success
    from forgecli.loop import build_loop_context, ensure_loop_scaffold, record_loop_run, summarize_loop_files

    context = build_loop_context(path.resolve(), force_prepare=refresh)
    files = ensure_loop_scaffold(context["prepared"].root)

    now = datetime.now(timezone.utc)
    record_loop_run(
        context["prepared"].root,
        tool=tool,
        task_status="scaffolded" if not task else f"task:{task}",
        iteration=1,
        started_at=now,
        finished_at=now,
    )

    success(f"Loop scaffolded in {files['root']}")
    console = get_console()
    console.print()
    console.print("  [bold cyan]Forge Loop[/bold cyan]")
    for key, value in summarize_loop_files(context["prepared"].root).items():
        console.print(f"  {key:>12} : [white]{value}[/white]")
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

        "    [cyan]forge antigravity[/cyan]  Launch Antigravity CLI with optimized context\n"


        "    [cyan]forge start[/cyan]        Start the background context optimization daemon\n"

        "    [cyan]forge mcp[/cyan]          Start the stdio Model Context Protocol (MCP) server\n"

        "    [cyan]forge config[/cyan]       Configure PromptForge, ResponseForge, and Output optimization profiles\n"

        "    [cyan]forge profile[/cyan]      View or set optimization profiles\n"

        "    [cyan]forge status[/cyan]       Show repository, daemon, and optimization status\n"

        "    [cyan]forge stats[/cyan]        Usage statistics, cache metrics, and performance\n"

        "    [cyan]forge doctor[/cyan]       Verify installation, dependencies, and configuration\n"

        "    [cyan]forge inspect[/cyan]      Display pipeline, provider, and optimization stages\n"
        "    [cyan]forge explain[/cyan]      Explain pipeline stages, concepts, and topics\n"
        "    [cyan]forge commit[/cyan]       Generate Conventional Commit from staged changes\n"
        "    [cyan]forge auth login[/cyan]   Authenticate and configure AI providers\n"
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

