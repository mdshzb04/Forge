"""Tests for registry-driven MCP auto-configuration (JSON + TOML writers)."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from forgecli.runtime.agents import AGENTS, AgentSpec, MCPTarget
from forgecli.runtime.mcp_config import (
    _write_json_mcp,
    _write_toml_mcp,
    configure_mcp_for_agent,
)


def test_write_json_mcp_creates_and_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "mcp.json"

    _write_json_mcp(path, "mcpServers")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["mcpServers"]["forge"] == {"command": "forge", "args": ["mcp"]}

    # Second write must not duplicate or error.
    _write_json_mcp(path, "mcpServers")
    data2 = json.loads(path.read_text(encoding="utf-8"))
    assert list(data2["mcpServers"].keys()) == ["forge"]


def test_write_json_mcp_preserves_existing_servers(tmp_path: Path) -> None:
    path = tmp_path / "mcp.json"
    path.write_text(
        json.dumps({"mcpServers": {"other": {"command": "x"}}}), encoding="utf-8"
    )

    _write_json_mcp(path, "mcpServers")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "other" in data["mcpServers"]
    assert "forge" in data["mcpServers"]


def test_write_toml_mcp_creates_and_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / ".codex" / "config.toml"

    _write_toml_mcp(path, "mcp_servers")
    assert path.exists()
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"]["forge"]["command"] == "forge"
    assert parsed["mcp_servers"]["forge"]["args"] == ["mcp"]

    before = path.read_text(encoding="utf-8")
    _write_toml_mcp(path, "mcp_servers")
    assert path.read_text(encoding="utf-8") == before  # no duplicate block


def test_write_toml_mcp_preserves_existing_content(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('model = "gpt-5"\n', encoding="utf-8")

    _write_toml_mcp(path, "mcp_servers")
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["model"] == "gpt-5"
    assert "forge" in parsed["mcp_servers"]


def test_configure_mcp_for_agent_toml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    configure_mcp_for_agent(AGENTS["codex"], tmp_path)
    toml_path = tmp_path / ".codex" / "config.toml"
    assert toml_path.exists()
    assert "[mcp_servers.forge]" in toml_path.read_text(encoding="utf-8")


def test_configure_mcp_for_agent_skips_when_unsupported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # aider declares no MCP targets and supports_mcp=False.
    configure_mcp_for_agent(AGENTS["aider"], tmp_path)
    assert not any(tmp_path.iterdir())


def test_all_five_agents_registered() -> None:
    assert set(AGENTS) == {"claude", "codex", "cursor", "antigravity", "aider"}
    for spec in AGENTS.values():
        assert isinstance(spec, AgentSpec)
        for target in spec.mcp_targets:
            assert isinstance(target, MCPTarget)
            assert target.fmt in {"json", "toml"}
            assert target.base in {"home", "repo"}
