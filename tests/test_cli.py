"""Smoke tests for the slim Forge CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from forgecli import __version__
from forgecli.cli.main import app


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "claude" in result.output
    assert "codex" in result.output
    assert "cursor" in result.output
    assert "aider" in result.output
    assert "graph" in result.output


def test_cli_banner() -> None:
    runner = CliRunner()
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Forge" in result.output
    assert "forge claude" in result.output


def test_wrapper_help_registered() -> None:
    runner = CliRunner()
    for cmd in ("claude", "codex", "cursor"):
        result = runner.invoke(app, [cmd, "--help"])
        assert result.exit_code == 0
        assert cmd in result.output.lower() or "Launch" in result.output


def test_wrapper_missing_binary_exits_cleanly(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("forgecli.runtime.wrappers.which", return_value=None):
        result = runner.invoke(app, ["claude"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "not installed" in result.output.lower()


def test_wrapper_prepares_context_and_launches(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("FORGECLI_FORGEGRAPH_BIN", "nonexistent-forgegraph")

    import subprocess
    from typing import Any

    original_run = subprocess.run
    launched: dict[str, Any] = {}

    def _fake_run(argv, *args, **kwargs):
        if argv and ("/usr/bin/claude" in argv[0] or argv[0] == "claude"):
            launched["argv"] = argv
            launched["cwd"] = kwargs.get("cwd")
            launched["env"] = kwargs.get("env")

            class _Result:
                returncode = 0

            return _Result()
        return original_run(argv, *args, **kwargs)

    with (
        patch("forgecli.runtime.wrappers.which", return_value="/usr/bin/claude"),
        patch("forgecli.runtime.wrappers.subprocess.run", side_effect=_fake_run),
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["claude"], catch_exceptions=False)

    assert result.exit_code == 0
    assert launched["argv"] in (["/usr/bin/claude"], ["claude"])
    env = launched["env"]
    assert env is not None
    assert "FORGE_CONTEXT" in env
    assert "FORGE_CONTEXT_FILE" in env


def test_graph_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["graph", "--help"])
    assert result.exit_code == 0
    assert "build" in result.output


def test_wrapper_help_new_commands() -> None:
    runner = CliRunner()
    for cmd in ("antigravity",):
        result = runner.invoke(app, [cmd, "--help"])
        assert result.exit_code == 0
        assert cmd in result.output.lower() or "Launch" in result.output


def test_graph_build_empty_directory(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["graph", "build", "-p", str(tmp_path)])
    assert result.exit_code == 0
    assert "No supported source files found. Nothing to build." in result.output


def test_graph_build_no_api_key(tmp_path: Path, monkeypatch) -> None:
    # Clear environment variables to ensure no keys are detected
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))

    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["graph", "build", "-p", str(tmp_path)])
    assert result.exit_code == 1
    assert "❌ API key required." in result.output
    assert (
        "Forge Graph requires an AI provider API key before a knowledge graph can be"
        in result.output
    )


@pytest.mark.parametrize(
    "cmd_name,binary_name",
    [
        ("claude", "claude"),
        ("codex", "codex"),
        ("cursor", "cursor"),
        ("antigravity", "antigravity"),
        ("aider", "aider"),
    ],
)
def test_wrapper_command_works_without_api_key(
    cmd_name: str, binary_name: str, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    # Ensure no API keys are set
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")

    import subprocess

    original_run = subprocess.run
    launched = {}

    def _fake_run(argv, *args, **kwargs):
        if argv and (binary_name in argv[0]):
            launched["argv"] = argv
            launched["env"] = kwargs.get("env", {})

            class _Result:
                returncode = 0

            return _Result()
        return original_run(argv, *args, **kwargs)

    with (
        patch("forgecli.runtime.wrappers.which", return_value=f"/usr/bin/{binary_name}"),
        patch("forgecli.runtime.wrappers.subprocess.run", side_effect=_fake_run),
    ):
        runner = CliRunner()
        result = runner.invoke(app, [cmd_name, "-p", str(tmp_path)], catch_exceptions=False)

    assert result.exit_code == 0
    assert launched.get("argv") is not None
    assert binary_name in launched["argv"][0]
    assert "FORGE_CONTEXT" in launched["env"]
    assert "FORGE_CONTEXT_FILE" in launched["env"]
    assert "FORGE_REPO_ROOT" in launched["env"]


def test_aider_receives_context_via_read_flag(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))
    (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")

    import subprocess

    original_run = subprocess.run
    launched: dict = {}

    def _fake_run(argv, *args, **kwargs):
        if argv and "aider" in argv[0]:
            launched["argv"] = argv

            class _Result:
                returncode = 0

            return _Result()
        return original_run(argv, *args, **kwargs)

    with (
        patch("forgecli.runtime.wrappers.which", return_value="/usr/bin/aider"),
        patch("forgecli.runtime.wrappers.subprocess.run", side_effect=_fake_run),
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["aider", "-p", str(tmp_path)], catch_exceptions=False)

    assert result.exit_code == 0
    argv = launched["argv"]
    assert "--read" in argv
    ctx_path = argv[argv.index("--read") + 1]
    assert ctx_path.endswith("_merged.md")
    assert Path(ctx_path).is_file()


def test_mcp_auto_configuration(tmp_path: Path, monkeypatch) -> None:
    # Set up mock directories
    mock_home = tmp_path / "mock_home"
    mock_home.mkdir()
    mock_repo = tmp_path / "mock_repo"
    mock_repo.mkdir()
    (mock_repo / "main.py").write_text("print('hi')", encoding="utf-8")

    # Monkeypatch Path.home() to return mock_home
    monkeypatch.setattr(Path, "home", lambda: mock_home)
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    import subprocess

    with (
        patch("forgecli.runtime.wrappers.which", return_value="/usr/bin/claude"),
        patch(
            "forgecli.runtime.wrappers.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ),
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["claude", "-p", str(mock_repo)], catch_exceptions=False)
        assert result.exit_code == 0

    # Verify ~/.claude.json got created and configured
    claude_json_file = mock_home / ".claude.json"
    assert claude_json_file.exists()
    claude_config = json.loads(claude_json_file.read_text(encoding="utf-8"))
    assert "forge" in claude_config.get("mcpServers", {})
    assert claude_config["mcpServers"]["forge"]["command"] == "forge"

    # Verify ~/.cursor/mcp.json got created and configured
    cursor_global_file = mock_home / ".cursor" / "mcp.json"
    assert cursor_global_file.exists()
    cursor_global_config = json.loads(cursor_global_file.read_text(encoding="utf-8"))
    assert "forge" in cursor_global_config.get("mcpServers", {})

    # Verify project-local config files
    assert (mock_repo / ".cursor" / "mcp.json").exists()
    assert (mock_repo / ".mcp.json").exists()

    # Verify Codex TOML got the forge server registered
    codex_toml = mock_home / ".codex" / "config.toml"
    assert codex_toml.exists()
    assert "[mcp_servers.forge]" in codex_toml.read_text(encoding="utf-8")

    # Verify Antigravity JSON got configured (unified ~/.gemini path)
    antigravity_json = mock_home / ".gemini" / "config" / "mcp_config.json"
    assert antigravity_json.exists()
    antigravity_config = json.loads(antigravity_json.read_text(encoding="utf-8"))
    assert "forge" in antigravity_config.get("mcpServers", {})


def test_wrapper_rejects_prompts_and_extra_arguments(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    with patch("forgecli.runtime.wrappers.which", return_value="/usr/bin/claude"):
        runner = CliRunner()
        result = runner.invoke(app, ["claude", "write code for me"], catch_exceptions=False)
        assert result.exit_code == 1
        assert "not supported" in result.output
