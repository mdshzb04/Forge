"""Launch Claude Code, Codex, Cursor, OpenCode, and CommandCode CLI with Forge-optimized context."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import typer

from forgecli.cli.ui import error, get_console, info
from forgecli.platform.shell import which
from forgecli.runtime.prepare import prepare_runtime_sync, resolve_repo_root


@dataclass(frozen=True)
class WrapperSpec:
    name: str
    binary: str
    install_hint: str


WRAPPERS: dict[str, WrapperSpec] = {
    "claude": WrapperSpec(
        name="Claude Code",
        binary="claude",
        install_hint="Install Claude Code: https://docs.anthropic.com/en/docs/claude-code",
    ),
    "codex": WrapperSpec(
        name="Codex CLI",
        binary="codex",
        install_hint="Install OpenAI Codex CLI: https://developers.openai.com/codex/cli/",
    ),
    "cursor": WrapperSpec(
        name="Cursor CLI",
        binary="cursor",
        install_hint="Install Cursor CLI: https://cursor.com/docs/cli/overview",
    ),
    "opencode": WrapperSpec(
        name="OpenCode CLI",
        binary="opencode",
        install_hint="Install OpenCode CLI: https://opencode.ai/",
    ),
    "commandcode": WrapperSpec(
        name="CommandCode CLI",
        binary="commandcode",
        install_hint="Install CommandCode CLI: https://commandcode.ai/",
    ),
    "antigravity": WrapperSpec(
        name="Antigravity CLI",
        binary="antigravity",
        install_hint="Install Antigravity CLI",
    ),
}


def launch_wrapper(
    wrapper_id: str,
    extra_args: list[str] | None = None,
    *,
    path: Path | None = None,
    force_prepare: bool = False,
) -> None:
    """Prepare lightweight context and launch the selected AI CLI."""
    spec = WRAPPERS.get(wrapper_id)
    if spec is None:
        error(f"Unknown wrapper: {wrapper_id}")
        raise typer.Exit(code=1)

    if extra_args:
        error(
            "Passing prompts or extra arguments to wrapper commands is not supported. Please run the command without arguments to launch the interactive CLI."
        )
        raise typer.Exit(code=1)

    binary_path = which(spec.binary)
    if binary_path is None and wrapper_id == "commandcode":
        # Check alternative binary names for commandcode
        binary_path = which("command-code")

    if binary_path is None:
        console = get_console()
        console.print(f"[red]✗[/red] {spec.name} is not installed.")
        console.print(spec.install_hint)
        raise typer.Exit(code=1)

    # 1. Detect current repository
    cwd = (path or Path.cwd()).resolve()
    repo_root = resolve_repo_root(cwd)

    # 2. Ensure the daemon is running
    import time

    import httpx

    from forgecli.cli.daemon import is_daemon_running, start_daemon_background

    if not is_daemon_running():
        info("Forge Runtime daemon is not running. Starting it in the background...")
        start_daemon_background()
        # Wait a moment for it to spin up
        for _ in range(20):
            if is_daemon_running():
                break
            time.sleep(0.2)

    # 3. Optimize context, prompts, and tokens (aggressively reusing cache)
    prepared = prepare_runtime_sync(repo_root, force=force_prepare, quiet=False)

    if prepared.from_cache:
        info("Reusing cached Forge context.")

    # 4. Notify daemon to refresh/ensure context is registered
    try:
        with httpx.Client(timeout=2.0) as client:
            client.get(f"http://127.0.0.1:16868/context?path={repo_root}")
    except Exception:
        pass

    # 5. Automatically configure MCP server for launched CLIs
    try:
        from forgecli.runtime.mcp_config import configure_mcp_for_all

        configure_mcp_for_all(repo_root)
    except Exception:
        pass

    env = os.environ.copy()
    env["FORGE_CONTEXT"] = prepared.context_summary
    env["FORGE_CONTEXT_FILE"] = str(prepared.context_file)
    env["FORGE_REPO_ROOT"] = str(prepared.root)

    argv = [binary_path, *(extra_args or [])]
    info(f"Launching [accent]{spec.name}[/accent] ...")

    completed = subprocess.run(
        argv,
        cwd=str(prepared.root),
        env=env,
    )
    raise typer.Exit(code=completed.returncode)
