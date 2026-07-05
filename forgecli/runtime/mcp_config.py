"""Automated configuration and detection of Forge MCP server for AI CLIs."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

from forgecli.cli.ui import info, success


def configure_mcp_for_all(repo_root: Path) -> None:
    """Detect and automatically configure Forge MCP server for Claude, Cursor, and local project."""
    configure_claude_mcp()
    configure_cursor_mcp(repo_root)
    configure_project_local_mcp(repo_root)


def configure_claude_mcp() -> None:
    """Ensure ~/.claude.json is configured with the forge MCP server."""
    claude_config_path = Path.home() / ".claude.json"
    forge_mcp_entry = {"command": "forge", "args": ["mcp"]}

    try:
        data: dict = {}
        if claude_config_path.exists():
            content = claude_config_path.read_text(encoding="utf-8").strip()
            if content:
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    info("Could not parse ~/.claude.json as valid JSON. Skipping auto-config.")
                    return

        if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
            data["mcpServers"] = {}

        if "forge" not in data["mcpServers"]:
            data["mcpServers"]["forge"] = forge_mcp_entry
            claude_config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            success("✨ Configured Forge MCP server in ~/.claude.json for Claude Code.")
    except Exception as e:
        info(f"Note: Could not auto-configure Claude Code MCP: {e}")
        info("You can manually configure Claude Code using: claude mcp add forge -- forge mcp")


def configure_cursor_mcp(repo_root: Path) -> None:
    """Ensure Cursor is configured with the forge MCP server globally and project-locally."""
    # 1. Global ~/.cursor/mcp.json
    cursor_global_path = Path.home() / ".cursor" / "mcp.json"
    forge_mcp_entry = {"command": "forge", "args": ["mcp"]}

    try:
        cursor_global_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if cursor_global_path.exists():
            content = cursor_global_path.read_text(encoding="utf-8").strip()
            if content:
                with contextlib.suppress(json.JSONDecodeError):
                    data = json.loads(content)

        if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
            data["mcpServers"] = {}

        if "forge" not in data["mcpServers"]:
            data["mcpServers"]["forge"] = forge_mcp_entry
            cursor_global_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            success("✨ Configured Forge MCP server in ~/.cursor/mcp.json for Cursor.")
    except Exception as e:
        info(f"Note: Could not auto-configure Cursor global MCP: {e}")

    # 2. Project-local .cursor/mcp.json
    cursor_local_dir = repo_root / ".cursor"
    cursor_local_path = cursor_local_dir / "mcp.json"
    try:
        cursor_local_dir.mkdir(parents=True, exist_ok=True)
        data = {}
        if cursor_local_path.exists():
            content = cursor_local_path.read_text(encoding="utf-8").strip()
            if content:
                with contextlib.suppress(json.JSONDecodeError):
                    data = json.loads(content)

        if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
            data["mcpServers"] = {}

        if "forge" not in data["mcpServers"]:
            data["mcpServers"]["forge"] = forge_mcp_entry
            cursor_local_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            success(
                f"✨ Configured Forge MCP server in {repo_root.name}/.cursor/mcp.json for Cursor."
            )
    except Exception as e:
        info(f"Note: Could not auto-configure Cursor local MCP: {e}")


def configure_project_local_mcp(repo_root: Path) -> None:
    """Create a project-local .mcp.json file for tools that support auto-discovery."""
    mcp_local_path = repo_root / ".mcp.json"
    forge_mcp_entry = {"command": "forge", "args": ["mcp"]}

    try:
        data: dict = {}
        if mcp_local_path.exists():
            content = mcp_local_path.read_text(encoding="utf-8").strip()
            if content:
                with contextlib.suppress(json.JSONDecodeError):
                    data = json.loads(content)

        if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
            data["mcpServers"] = {}

        if "forge" not in data["mcpServers"]:
            data["mcpServers"]["forge"] = forge_mcp_entry
            mcp_local_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            success("✨ Created project-local .mcp.json for auto-discovery of Forge MCP server.")
    except Exception as e:
        info(f"Note: Could not write project-local .mcp.json: {e}")
