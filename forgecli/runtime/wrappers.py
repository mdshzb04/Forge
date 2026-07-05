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

    # 2. Optimize context, prompts, and tokens (aggressively reusing cache)
    prepared = prepare_runtime_sync(repo_root, force=force_prepare, quiet=False)
    if prepared.from_cache:
        info("Reusing cached Forge context.")

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
