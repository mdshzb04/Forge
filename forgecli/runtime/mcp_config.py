"""Automated registration of the Forge MCP server for terminal AI agents.

Registration is driven entirely by the agent registry in
:mod:`forgecli.runtime.agents`. Each agent declares one or more
:class:`~forgecli.runtime.agents.MCPTarget` locations; this module writes the
``forge`` MCP entry into each, handling both JSON and TOML config formats.
Writes are idempotent and best-effort — a failure for one agent never blocks a
launch, it just falls back to the FORGE_CONTEXT env vars + project ``.mcp.json``.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

from forgecli.cli.ui import info, success
from forgecli.runtime.agents import AGENTS, AgentSpec, MCPTarget

_FORGE_ENTRY = {"command": "forge", "args": ["mcp"]}


def configure_mcp_for_all(repo_root: Path) -> None:
    """Register the Forge MCP server for every supported agent + project-local."""
    for spec in AGENTS.values():
        configure_mcp_for_agent(spec, repo_root)
    configure_project_local_mcp(repo_root)


def configure_mcp_for_agent(spec: AgentSpec, repo_root: Path) -> None:
    """Write the Forge MCP entry into every target declared by ``spec``."""
    if not spec.supports_mcp:
        return
    for target in spec.mcp_targets:
        path = _resolve_target_path(target, repo_root)
        try:
            if target.fmt == "toml":
                _write_toml_mcp(path, target.table)
            else:
                _write_json_mcp(path, target.table)
        except Exception as e:  # best-effort: never block a launch
            info(f"Note: Could not auto-configure {target.label or spec.name} MCP: {e}")


def _resolve_target_path(target: MCPTarget, repo_root: Path) -> Path:
    anchor = Path.home() if target.base == "home" else repo_root
    return anchor / target.relpath


def _write_json_mcp(path: Path, table: str) -> None:
    """Idempotently add the ``forge`` server to a JSON config at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if path.exists():
        content = path.read_text(encoding="utf-8").strip()
        if content:
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                info(f"Could not parse {path} as valid JSON. Skipping auto-config.")
                return

    servers = data.get(table)
    if not isinstance(servers, dict):
        servers = {}
        data[table] = servers

    if "forge" in servers:
        return

    servers["forge"] = dict(_FORGE_ENTRY)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    success(f"✨ Configured Forge MCP server in {path}.")


def _write_toml_mcp(path: Path, table: str) -> None:
    """Idempotently add the ``forge`` server to a TOML config at ``path``.

    Reads existing TOML with the stdlib ``tomllib`` to detect an existing
    ``forge`` entry, then appends a minimal ``[<table>.forge]`` block. Appending
    (rather than full re-serialization) preserves the user's existing formatting
    and avoids a hard dependency on a TOML writer.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        with contextlib.suppress(Exception):
            import tomllib

            parsed = tomllib.loads(existing)
            servers = parsed.get(table)
            if isinstance(servers, dict) and "forge" in servers:
                return

    block = (
        f"\n[{table}.forge]\n"
        'command = "forge"\n'
        'args = ["mcp"]\n'
    )
    prefix = existing if existing.endswith("\n") or not existing else existing + "\n"
    path.write_text(prefix + block, encoding="utf-8")
    success(f"✨ Configured Forge MCP server in {path}.")


def configure_project_local_mcp(repo_root: Path) -> None:
    """Create a project-local .mcp.json for tools that support auto-discovery."""
    _write_json_mcp(repo_root / ".mcp.json", "mcpServers")


__all__ = [
    "configure_mcp_for_agent",
    "configure_mcp_for_all",
    "configure_project_local_mcp",
]
