"""Launch Claude Code, Codex, Cursor, OpenCode, and CommandCode CLI with Forge-optimized context."""

from __future__ import annotations

import asyncio
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import typer

from forgecli.cli.commands_graph import setup_graphify_credentials
from forgecli.cli.ui import error, get_console, info
from forgecli.graph.backend_graphify import GraphifyRepositoryGraph
from forgecli.platform.shell import which
from forgecli.runtime.prepare import prepare_runtime_sync, resolve_repo_root
from forgecli.utils.fs import has_supported_source_files

_SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".forge",
    "graphify-out",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


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
    """Prepare lightweight context, build/update graph, and launch the selected AI CLI."""
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

    # 2. Build or update the repository knowledge graph
    backend = GraphifyRepositoryGraph(root=repo_root)
    if asyncio.run(backend.is_available()) and has_supported_source_files(repo_root):
        active_provider = setup_graphify_credentials(repo_root)
        if not active_provider:
            error(
                "No API key configured. Run 'forge auth login' or export "
                "OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY before running 'forge graph build'."
            )
            raise typer.Exit(code=1)

        graph_json = backend.artifacts.graph_json
        needs_build = not graph_json.exists()
        needs_update = False

        if graph_json.exists() and not force_prepare:
            graph_mtime = graph_json.stat().st_mtime
            for p in repo_root.rglob('*'):
                try:
                    parts = p.relative_to(repo_root).parts
                    if any(part.startswith('.') or part in _SKIP_DIRS for part in parts[:-1]):
                        continue
                    if p.is_file() and not p.name.startswith('.') and p.stat().st_mtime > graph_mtime:
                        needs_update = True
                        break
                except ValueError:
                    continue

            if force_prepare or needs_build:
                info("Building repository knowledge graph...")
                asyncio.run(backend.build(force=force_prepare))
            elif needs_update:
                info("Updating repository knowledge graph...")
                asyncio.run(backend.update_graph())

    # 3-6. Optimize context, prompts, and tokens (aggressively reusing cache)
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
