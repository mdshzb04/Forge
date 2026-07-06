"""Subcommands for system diagnostics and status reports."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from forgecli.cli.daemon import is_daemon_running
from forgecli.cli.ui import error, get_console, info, success, warn
from forgecli.config.loader import ConfigLoader
from forgecli.platform.paths import ProjectPaths
from forgecli.runtime.prepare import resolve_repo_root


def status_cmd() -> None:
    """Show current repository, optimization, and daemon status."""
    console = get_console()
    console.print()
    console.print("  [bold cyan]Forge Status[/bold cyan]")
    console.print()

    # 1. Repository
    cwd = Path.cwd()
    try:
        repo_root = resolve_repo_root(cwd)
        console.print(f"  Repository          : [green]Ready[/green] ({repo_root.name})")
    except Exception:
        console.print("  Repository          : [red]Not a Git Repository[/red]")
        repo_root = None

    # 2. ForgeGraph
    if repo_root:
        graph_file = repo_root / "forgegraph-out" / "graph.json"
        if graph_file.exists():
            console.print("  ForgeGraph          : [green]Ready[/green]")
        else:
            console.print("  ForgeGraph          : [yellow]Missing[/yellow] (run 'forge graph build' to index)")
    else:
        console.print("  ForgeGraph          : [red]N/A[/red]")

    # 3. Cache
    paths = ProjectPaths.from_env()
    context_cache_dir = paths.cache_dir / "runtime" / "context"
    cache_files = list(context_cache_dir.glob("*.md")) if context_cache_dir.exists() else []
    if cache_files:
        console.print(f"  Cache               : [green]HIT[/green] ({len(cache_files)} cached profiles)")
    else:
        console.print("  Cache               : [yellow]MISS[/yellow] (no cached context yet)")

    # 4. Optimization Profiles
    loader = ConfigLoader()
    try:
        settings = loader.load()
    except Exception:
        from forgecli.config.settings import ForgeSettings
        settings = ForgeSettings()

    # Ponytail
    p_val = settings.prompt_optimizer.intensity if settings.prompt_optimizer.enabled else "off"
    console.print(f"  Ponytail            : [white]{p_val.capitalize()}[/white]")

    # Caveman
    c_val = settings.caveman.intensity if settings.caveman.enabled else "off"
    console.print(f"  Caveman             : [white]{c_val.capitalize()}[/white]")

    # Output Optimization
    o_val = settings.output_optimization.intensity if settings.output_optimization.enabled else "off"
    console.print(f"  Output Optimization : [white]{o_val.capitalize()}[/white]")

    # 5. Daemon
    if is_daemon_running():
        console.print("  Daemon              : [green]Running[/green]")
    else:
        console.print("  Daemon              : [yellow]Stopped[/yellow]")

    console.print()


def doctor_cmd() -> None:
    """Run system checks to verify Forge configuration and dependencies."""
    console = get_console()
    console.print()
    console.print("  [bold cyan]Forge Doctor — System Diagnostics[/bold cyan]")
    console.print()

    # Check Git
    git_bin = shutil.which("git")
    if git_bin:
        success("Git detected")
    else:
        error("Git not found in PATH")

    # Check Python
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    success(f"Python {py_ver} detected (version is compatible)")

    # Check Repository
    cwd = Path.cwd()
    try:
        resolve_repo_root(cwd)
        success("Current directory is inside a Git repository")
    except Exception:
        warn("Current directory is not a Git repository (some commands require indexing)")

    # Check Cache directory
    paths = ProjectPaths.from_env()
    try:
        test_file = paths.cache_dir / "doctor_test.txt"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        success("Cache directory is healthy and writeable")
    except Exception as e:
        error(f"Cache directory is not healthy: {e}")

    # Check Configuration
    loader = ConfigLoader()
    try:
        loader.load()
        success("Configuration file loaded correctly")
    except Exception as e:
        warn(f"No custom configuration file loaded (using default settings): {e}")

    # Check Daemon status
    if is_daemon_running():
        success("Background daemon is running")
    else:
        warn("Background daemon is stopped (run 'forge start' to start it)")

    # Check AI CLI Wrappers
    clis = {
        "claude": ["claude", "claude-code"],
        "cursor": ["cursor"],
        "codex": ["codex"],
        "antigravity": ["antigravity"],
    }
    for label, bins in clis.items():
        found = False
        for b in bins:
            if shutil.which(b):
                found = True
                break
        if found:
            success(f"AI CLI: {label} detected")
        else:
            info(f"AI CLI: {label} not detected (wrapper will run when installed)")

    console.print()
