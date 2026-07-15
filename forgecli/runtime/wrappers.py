"""Launch supported terminal AI agents with Forge context.

All agents (Claude, Codex, Cursor, Antigravity, Gemini, Aider,
OpenCode, CommandCode) execute through a single unified runtime path:
context preparation → behavior optimization → MCP configuration → subprocess launch.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import typer

from forgecli.platform.shell import which
from forgecli.runtime.agents import AGENTS
from forgecli.runtime.prepare import build_merged_context, prepare_runtime_sync, resolve_repo_root


def launch_wrapper(
    wrapper_id: str,
    extra_args: list[str] | None = None,
    *,
    path: Path | None = None,
    force_prepare: bool = False,
) -> None:
    """Unified entry point — prepare optimized context and launch the selected AI CLI."""
    from forgecli.cli.ui import error, get_console, info, success

    spec = AGENTS.get(wrapper_id)
    if spec is None:
        error(f"Unknown wrapper: {wrapper_id}")
        raise typer.Exit(code=1)

    if extra_args:
        error(
            "Passing prompts or extra arguments to wrapper commands is not supported. "
            "Please run the command without arguments to launch the interactive CLI."
        )
        raise typer.Exit(code=1)

    if spec.binary == "antigravity" and Path("/usr/share/antigravity/antigravity").exists():
        binary_path = "/usr/share/antigravity/antigravity"
    else:
        binary_path = which(spec.binary)

    if binary_path is None:
        console = get_console()
        console.print(f"[red]✗[/red] {spec.name} is not installed.")
        console.print(spec.install_hint)
        raise typer.Exit(code=1)

    cwd = (path or Path.cwd()).resolve()
    repo_root = resolve_repo_root(cwd)

    from forgecli.cli.daemon_utils import check_daemon_health, start_daemon_background

    if not check_daemon_health():
        info("Forge Runtime daemon is not running. Starting in the background...")
        start_daemon_background()
        for _ in range(20):
            if check_daemon_health():
                break
            time.sleep(0.2)

    prepared = prepare_runtime_sync(repo_root, force=force_prepare, quiet=False)
    if prepared.from_cache:
        info("Reusing cached Forge context.")

    merged_context = build_merged_context(
        repo_context=prepared.context_summary,
        repo_root=prepared.root,
    )
    merged_file = prepared.context_file.parent / f"{prepared.context_file.stem}_merged.md"
    merged_file.write_text(merged_context, encoding="utf-8")

    if spec.supports_mcp:
        try:
            from forgecli.runtime.mcp_config import (
                configure_mcp_for_agent,
                configure_project_local_mcp,
            )
            configure_mcp_for_agent(spec, repo_root)
            configure_project_local_mcp(repo_root)
        except Exception:
            pass

    env = os.environ.copy()
    env["FORGE_CONTEXT"] = merged_context
    env["FORGE_CONTEXT_FILE"] = str(merged_file)
    env["FORGE_REPO_ROOT"] = str(prepared.root)

    argv = [binary_path, *(extra_args or [])]
    if spec.context_flag:
        argv += [spec.context_flag, str(merged_file)]

    success(f"Launching {spec.name} with optimized context ...")

    completed = subprocess.run(argv, cwd=str(prepared.root), env=env)
    raise typer.Exit(code=completed.returncode)
