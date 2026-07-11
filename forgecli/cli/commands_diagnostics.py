"""Subcommands for system diagnostics, status, profiling, statistics, and explain."""



from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

import typer

from forgecli.cli.daemon_utils import check_daemon_health
from forgecli.cli.ui import error, get_console, success, warn
from forgecli.config.loader import ConfigLoader
from forgecli.platform.paths import ProjectPaths
from forgecli.runtime.prepare import resolve_repo_root


def status_cmd() -> None:

    """Show current repository, optimization, and daemon status."""

    console = get_console()

    console.print()

    console.print("  [bold cyan]Forge Status[/bold cyan]")

    console.print()



    cwd = Path.cwd()

    try:

        repo_root = resolve_repo_root(cwd)

        console.print(f"  Repository          : [green]Ready[/green] ({repo_root.name})")

    except Exception:

        console.print("  Repository          : [red]Not a Git Repository[/red]")

        repo_root = None



    if repo_root:

        graph_file = repo_root / "forgegraph-out" / "graph.json"

        if graph_file.exists():

            console.print("  ForgeGraph          : [green]Ready[/green]")

        else:

            console.print("  ForgeGraph          : [yellow]Missing[/yellow] (run 'forge graph build' to index)")

    else:

        console.print("  ForgeGraph          : [red]N/A[/red]")



    paths = ProjectPaths.from_env()

    context_cache_dir = paths.cache_dir / "runtime" / "context"

    cache_files = list(context_cache_dir.glob("*.md")) if context_cache_dir.exists() else []

    if cache_files:

        console.print(f"  Cache               : [green]HIT[/green] ({len(cache_files)} cached profiles)")

    else:

        console.print("  Cache               : [yellow]MISS[/yellow] (no cached context yet)")



    loader = ConfigLoader()

    try:

        settings = loader.load()

    except Exception:

        from forgecli.config.settings import ForgeSettings

        settings = ForgeSettings()



    p_val = settings.prompt_optimizer.intensity if settings.prompt_optimizer.enabled else "off"

    console.print(f"  Ponytail            : [white]{p_val.capitalize()}[/white]")

    c_val = settings.caveman.intensity if settings.caveman.enabled else "off"

    console.print(f"  Caveman             : [white]{c_val.capitalize()}[/white]")

    o_val = settings.output_optimization.intensity if settings.output_optimization.enabled else "off"

    console.print(f"  Output Optimization : [white]{o_val.capitalize()}[/white]")



    if check_daemon_health():

        console.print("  Daemon              : [green]Running[/green]")

    else:

        console.print("  Daemon              : [yellow]Stopped[/yellow]")



    console.print()





def stats_cmd() -> None:

    """Show Forge usage statistics, cache metrics, and pipeline performance."""

    console = get_console()

    console.print()

    console.print("  [bold cyan]Forge Statistics[/bold cyan]")

    console.print()



    paths = ProjectPaths.from_env()



    context_cache = paths.cache_dir / "runtime" / "context"

    cache_files = list(context_cache.glob("*.md")) if context_cache.exists() else []

    cache_size = sum(f.stat().st_size for f in cache_files) if cache_files else 0

    cache_age = max((time.time() - f.stat().st_mtime) for f in cache_files) if cache_files else 0



    console.print(f"  Cached profiles    : {len(cache_files)}")

    console.print(f"  Cache size         : {_format_size(cache_size)}")

    if cache_files:

        console.print(f"  Newest cache age   : {_format_duration(cache_age)}")



    try:

        repo_root = resolve_repo_root(Path.cwd())

        py_files = list(repo_root.rglob("*.py"))

        all_files = list(repo_root.rglob("*"))

        skip = {".git", ".venv", "node_modules", "__pycache__", "dist", "build", ".forge", "forgegraph-out"}

        trackable = [f for f in all_files if not any(s in f.parts for s in skip)]

        console.print()

        console.print(f"  Repository         : {repo_root.name}")

        console.print(f"  Python files       : {len(py_files)}")

        console.print(f"  Total trackable    : {len(trackable)}")

    except Exception:

        pass



    try:

        graph_file = Path.cwd() / "forgegraph-out" / "graph.json"

        if graph_file.exists():

            data = json.loads(graph_file.read_text())

            nodes = len(data.get("nodes", [])) if isinstance(data, dict) else len(data)

            console.print()

            console.print(f"  Graph nodes        : {nodes}")

            console.print(f"  Graph file size    : {_format_size(graph_file.stat().st_size)}")

    except Exception:

        pass



    try:

        from forgecli.sdk.manager import PluginManager

        manager = PluginManager()

        plugins = manager.list()

        enabled_count = sum(1 for s, _ in plugins if s.enabled)

        console.print()

        console.print(f"  Installed plugins  : {len(plugins)}")

        console.print(f"  Enabled plugins    : {enabled_count}")

    except Exception:

        pass



    try:

        from forgecli.providers.base import default_registry

        names = default_registry.names()

        configured = sum(1 for n in names if _check_api_key(n))

        console.print()

        console.print(f"  Providers          : {len(names)}")

        console.print(f"  With API keys      : {configured}")

    except Exception:

        pass



    from forgecli.middleware.defaults import (
        AuthenticationMiddleware,
        CachingMiddleware,
        ContextOptimizerMiddleware,
        ConversationMiddleware,
        DependencyGraphMiddleware,
        GraphifyMiddleware,
        HistoryCompressorMiddleware,
        PolicyMiddleware,
        PromptOptimizerMiddleware,
        ProviderMiddleware,
        RepositoryPlannerMiddleware,
        ResponseOptimizerMiddleware,
        SemanticRetrievalMiddleware,
        StreamingMiddleware,
        SymbolLookupMiddleware,
        TelemetryMiddleware,
        TokenPlannerMiddleware,
    )

    pipeline_mws = [

        TelemetryMiddleware, AuthenticationMiddleware, PolicyMiddleware, CachingMiddleware,

        HistoryCompressorMiddleware, TokenPlannerMiddleware, ContextOptimizerMiddleware,

        ConversationMiddleware, PromptOptimizerMiddleware, RepositoryPlannerMiddleware,

        DependencyGraphMiddleware, SymbolLookupMiddleware, GraphifyMiddleware,

        SemanticRetrievalMiddleware, StreamingMiddleware, ProviderMiddleware,

        ResponseOptimizerMiddleware,

    ]

    console.print()

    console.print(f"  Pipeline stages    : {len(pipeline_mws)}")



    console.print()





def profile_cmd(

    ponytail: str = typer.Option(None, "--ponytail", "-p", help="Set Ponytail intensity (off|lite|full|ultra)"),

    caveman: str = typer.Option(None, "--caveman", "-c", help="Set Caveman intensity (off|lite|full|ultra|wenyan)"),

) -> None:

    """View or set optimization profiles."""

    console = get_console()



    if ponytail or caveman:

        from forgecli.config.writer import update_config

        path = update_config(ponytail=ponytail, caveman=caveman)

        console.print()

        console.print(f"  [green]✓[/green] Profile updated in [white]{path}[/white]")



    loader = ConfigLoader()

    try:

        settings = loader.load()

    except Exception:

        from forgecli.config.settings import ForgeSettings

        settings = ForgeSettings()



    console.print()

    console.print("  [bold cyan]Forge Optimization Profile[/bold cyan]")

    console.print()



    def _color(val: str, enabled: bool) -> str:

        if not enabled or val == "off":

            return "[dim]off[/dim]"

        colors = {"lite": "yellow", "full": "green", "ultra": "cyan", "wenyan": "magenta"}

        c = colors.get(val, "white")

        return f"[{c}]{val}[/{c}]"



    p_intensity = settings.prompt_optimizer.intensity if settings.prompt_optimizer.enabled else "off"

    c_intensity = settings.caveman.intensity if settings.caveman.enabled else "off"

    o_intensity = settings.output_optimization.intensity if settings.output_optimization.enabled else "off"



    console.print(f"  Ponytail (prompt)     : {_color(p_intensity, settings.prompt_optimizer.enabled)}")

    console.print("    YAGNI rules — ship minimum viable change, challenge requirements")

    console.print()

    console.print(f"  Caveman (style)       : {_color(c_intensity, settings.caveman.enabled)}")

    console.print("    Be concise, drop filler, keep technical terms exact")

    console.print()

    console.print(f"  Output Optimization   : {_color(o_intensity, settings.output_optimization.enabled)}")

    console.print("    Validate syntax, strip noise, ensure clean responses")

    console.print()

    console.print("  [dim]Change with: forge profile --ponytail ultra --caveman full[/dim]")

    console.print()





def explain_cmd(

    topic: str = typer.Argument(None, help="Topic to explain (pipeline, ponytail, caveman, graphify, mcp, daemon)"),

) -> None:

    """Explain Forge concepts, pipeline stages, or diagnostics."""

    console = get_console()



    explanations = {

        "pipeline": (

            "Pipeline",

            "The Forge middleware pipeline processes every AI request through 19 stages:\n"

            "  1. Telemetry (1000)   — Trace spans + metrics\n"

            "  2. Auth (950)         — Token validation\n"

            "  3. Policy (900)       — Safety/compliance checks\n"

            "  4. Cache (850)        — Exact-match prompt cache\n"

            "  5. History (800)      — Compress long conversations\n"

            "  6. TokenPlanner (750) — Budget token limits\n"

            "  7. ContextOpt (700)   — Trim to fit budget\n"

            "  8. Conversation (650) — Session persistence\n"

            "  9. Caveman (580)      — Output conciseness\n"

            "  10. Ponytail (600)    — Prompt engineering\n"

            "  11. Repository (550)  — File scanning\n"

            "  12. DepGraph (500)    — Import relationship graph\n"

            "  13. SymbolLookup (450)— Extract classes/functions\n"

            "  14. Graphify (400)    — Knowledge graph injection\n"

            "  15. Semantic (350)    — Relevance ranking\n"

            "  16. Streaming (300)   — Stream interception\n"

            "  17. Resilience (250)  — Circuit breaker + retry\n"

            "  18. Provider (200)    — LLM API call (terminal)\n"

            "  19. ResponseOpt (100) — Post-process output",

        ),

        "ponytail": (

            "Ponytail",

            "Ponytail is a prompt optimization ruleset that implements YAGNI (You Ain't "

            "Gonna Need It) principles. It rewrites prompts to instruct models to ship "

            "the simplest diff that solves the problem.\n\n"

            "Modes: off → lite → full → ultra\n"

            "  off:   No rewriting\n"

            "  lite:  One-line hint naming lazier alternative\n"

            "  full:  Full ladder ruleset, shortest diff\n"

            "  ultra: Aggressive YAGNI, challenges requirements",

        ),

        "caveman": (

            "Caveman",

            "Caveman is an output optimization ruleset that reduces LLM response verbosity. "

            "It injects system prompts instructing the model to communicate in concise, "

            "token-efficient style.\n\n"

            "Modes: off → lite → full → ultra → wenyan\n"

            "  off:    Normal responses\n"

            "  lite:   Drop filler words and pleasantries\n"

            "  full:   Fragment pattern [thing][action][reason]\n"

            "  ultra:  Maximum compression\n"

            "  wenyan: Classical Chinese (文言) for ultimate density",

        ),

        "graphify": (

            "Graphify",

            "Graphify builds a knowledge graph of your codebase — mapping symbols "

            "(classes, functions), their dependencies, and structural relationships. "

            "The graph enables intelligent context retrieval during AI requests.\n\n"

            "Build it with: forge graph build\n"

            "Inspect it with: forge inspect",

        ),

        "mcp": (

            "Model Context Protocol",

            "The Model Context Protocol (MCP) is a standard interface that allows AI "

            "clients to retrieve context from external tools. Forge implements an MCP "

            "server that exposes:\n"

            "  - get_optimized_context: Compressed repo context\n"

            "  - get_summary: Repository overview\n"

            "  - get_dependency_graph: Import relationships\n"

            "  - file_lookup: File contents by path\n"

            "  - symbol_lookup: Class/function definitions\n"

            "  - semantic_search: Keyword search across codebase",

        ),

        "daemon": (

            "Daemon",

            "The Forge daemon runs in the background on port 16868. It watches your "

            "repository for changes and maintains an up-to-date context cache. When "

            "you launch a wrapper command, the daemon ensures the latest context is "

            "available.\n\n"

            "Start: forge start\n"

            "Status: forge status\n"

            "Health: http://127.0.0.1:16868/health",

        ),

    }



    if topic:

        topic_lower = topic.lower()

        if topic_lower in explanations:

            title, body = explanations[topic_lower]

        else:

            matches = [k for k in explanations if topic_lower in k]

            if len(matches) == 1:

                title, body = explanations[matches[0]]

            else:

                console.print()

                console.print(f"  [yellow]Unknown topic: {topic}[/yellow]")

                console.print(f"  Available: {', '.join(sorted(explanations.keys()))}")

                console.print()

                return



        console.print()

        console.print(f"  [bold cyan]{title}[/bold cyan]")

        console.print()

        for line in body.split("\n"):

            console.print(f"  {line}")

        console.print()

        return



    console.print()

    console.print("  [bold cyan]Forge Explain — Available Topics[/bold cyan]")

    console.print()

    for key, (title, _) in explanations.items():

        console.print(f"  [cyan]forge explain {key}[/cyan]  — {title}")

    console.print()





def doctor_cmd() -> None:

    """Run system checks to verify Forge configuration and dependencies."""

    console = get_console()

    console.print()

    console.print("  [bold cyan]Forge Doctor — System Diagnostics[/bold cyan]")

    console.print()



    git_bin = shutil.which("git")

    if git_bin:

        success("Git detected")

    else:

        error("Git not found in PATH")



    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    success(f"Python {py_ver} detected (version is compatible)")



    cwd = Path.cwd()

    try:

        resolve_repo_root(cwd)

        success("Current directory is inside a Git repository")

    except Exception:

        warn("Current directory is not a Git repository (some commands require indexing)")



    paths = ProjectPaths.from_env()

    try:

        test_file = paths.cache_dir / "doctor_test.txt"

        test_file.write_text("test", encoding="utf-8")

        test_file.unlink()

        success("Cache directory is healthy and writeable")

    except Exception as e:

        error(f"Cache directory is not healthy: {e}")



    loader = ConfigLoader()

    try:

        loader.load()

        success("Configuration file loaded correctly")

    except Exception as e:

        warn(f"No custom configuration file loaded (using default settings): {e}")



    if check_daemon_health():

        success("Background daemon is running")

    else:

        warn("Background daemon is stopped (run 'forge start' to start it)")





    _check_provider_keys(console)





    _check_ai_clis(console)





    _check_plugin_health(console)



    console.print()





def _check_provider_keys(console) -> None:

    console.print()

    console.print("  [bold]Provider API Keys[/bold]")

    provider_keys = {

        "openai": "OPENAI_API_KEY",

        "anthropic": "ANTHROPIC_API_KEY",

        "google": "GOOGLE_API_KEY",

        "openrouter": "OPENROUTER_API_KEY",

        "groq": "GROQ_API_KEY",

        "mistral": "MISTRAL_API_KEY",

        "cohere": "COHERE_API_KEY",

        "deepseek": "DEEPSEEK_API_KEY",

    }

    any_configured = False

    for name, env_var in sorted(provider_keys.items()):

        if os.environ.get(env_var):

            console.print(f"    [green]✓[/green] {name:<15} configured")

            any_configured = True

    if not any_configured:

        console.print("    [yellow]⚠[/yellow] No provider API keys configured")





def _check_ai_clis(console) -> None:

    console.print()

    console.print("  [bold]AI CLI Wrappers[/bold]")

    clis = {

        "claude": ["claude", "claude-code"],

        "codex": ["codex"],

        "cursor": ["cursor"],

        "antigravity": ["antigravity"],

        "gemini": ["gemini"],

    }

    for label, bins in clis.items():

        found = any(shutil.which(b) for b in bins)

        if found:

            console.print(f"    [green]✓[/green] {label}")

        else:

            console.print(f"    [dim]-[/dim] {label} [dim](not installed)[/dim]")





def _check_plugin_health(console) -> None:

    try:

        from forgecli.sdk.manager import PluginManager

        manager = PluginManager()

        plugins = manager.list()

        console.print()

        console.print("  [bold]Plugin Health[/bold]")

        if not plugins:

            console.print("    [dim]No plugins installed[/dim]")

            return

        for state, _loaded in plugins:

            status = "[green]enabled[/green]" if state.enabled else "[yellow]disabled[/yellow]"

            version = state.version or "unknown"

            console.print(f"    [green]✓[/green] {state.name}  v{version}  {status}")

    except Exception:

        pass





def _format_size(size_bytes: int) -> str:

    if size_bytes < 1024:

        return f"{size_bytes} B"

    elif size_bytes < 1024 * 1024:

        return f"{size_bytes / 1024:.1f} KB"

    elif size_bytes < 1024 * 1024 * 1024:

        return f"{size_bytes / (1024 * 1024):.1f} MB"

    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"





def _format_duration(seconds: float) -> str:

    if seconds < 60:

        return f"{seconds:.0f}s"

    elif seconds < 3600:

        return f"{seconds / 60:.0f}m"

    return f"{seconds / 3600:.0f}h"





def _check_api_key(provider_name: str) -> bool:

    env_map = {

        "openai": "OPENAI_API_KEY",

        "anthropic": "ANTHROPIC_API_KEY",

        "google": "GOOGLE_API_KEY",

        "openrouter": "OPENROUTER_API_KEY",

        "groq": "GROQ_API_KEY",

        "mistral": "MISTRAL_API_KEY",

        "cohere": "COHERE_API_KEY",

    }

    env_var = env_map.get(provider_name)

    if env_var:

        return bool(os.environ.get(env_var))

    return False

