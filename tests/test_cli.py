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

    assert "graph" in result.output

    assert "auth" in result.output


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

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))

    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")

    runner = CliRunner()

    with patch("forgecli.core.credentials.get_api_key", return_value=None):
        result = runner.invoke(app, ["graph", "build", "-p", str(tmp_path)])

    assert result.exit_code == 1

    assert "❌ API key required." in result.output

    assert (
        "Forge Graph requires an AI provider API key before a knowledge graph can be"
        in result.output
    )


def test_graph_build_with_groq_api_key(tmp_path: Path, monkeypatch) -> None:

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))

    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")

    runner = CliRunner()

    from forgecli.providers.router_state import load_state, save_state

    state = load_state(tmp_path / "data" / "router.json")

    state.choice = "groq"

    state.provider = "groq"

    state.model = "llama-4-scout"

    save_state(tmp_path / "data" / "router.json", state)

    def mock_get_api_key(provider_name: str) -> str | None:

        if provider_name == "groq":
            return "sk-groq-test-key"

        return None

    from forgecli.graph.repository import BuildResult, GraphSnapshot

    mock_snapshot = GraphSnapshot(root=str(tmp_path), nodes=(), edges=(), communities=())

    mock_result = BuildResult(
        snapshot=mock_snapshot, artifacts={}, raw_output="mocked build output"
    )

    with (
        patch("forgecli.core.credentials.get_api_key", side_effect=mock_get_api_key),
        patch(
            "forgecli.graph.backend_forgegraph.ForgeRepositoryGraph.is_available", return_value=True
        ),
        patch(
            "forgecli.graph.backend_forgegraph.ForgeRepositoryGraph.build", return_value=mock_result
        ) as mock_build,
    ):
        result = runner.invoke(app, ["graph", "build", "-p", str(tmp_path)])

    assert result.exit_code == 0

    mock_build.assert_called_once()

    kwargs = mock_build.call_args[1]

    extra_args = kwargs.get("extra_args", [])

    assert "--backend" in extra_args

    assert "openai" in extra_args

    assert "--model" in extra_args

    assert "llama-3.1-70b-versatile" in extra_args

    import os

    assert os.environ.get("OPENAI_API_KEY") == "sk-groq-test-key"

    assert os.environ.get("OPENAI_BASE_URL") == "https://api.groq.com/openai/v1"


def test_graph_build_with_backend_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))

    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")

    runner = CliRunner()

    def mock_get_api_key(provider_name: str) -> str | None:
        if provider_name == "anthropic":
            return "sk-ant-override-key"
        return None

    from forgecli.graph.repository import BuildResult, GraphSnapshot

    mock_snapshot = GraphSnapshot(root=str(tmp_path), nodes=(), edges=(), communities=())
    mock_result = BuildResult(
        snapshot=mock_snapshot, artifacts={}, raw_output="mocked build output"
    )

    with (
        patch("forgecli.core.credentials.get_api_key", side_effect=mock_get_api_key),
        patch(
            "forgecli.graph.backend_forgegraph.ForgeRepositoryGraph.is_available", return_value=True
        ),
        patch(
            "forgecli.graph.backend_forgegraph.ForgeRepositoryGraph.build", return_value=mock_result
        ) as mock_build,
    ):
        result = runner.invoke(
            app,
            [
                "graph",
                "build",
                "-p",
                str(tmp_path),
                "--backend",
                "anthropic",
                "--model",
                "custom-claude-model",
            ],
        )

    assert result.exit_code == 0
    mock_build.assert_called_once()
    kwargs = mock_build.call_args[1]
    extra_args = kwargs.get("extra_args", [])
    assert "--backend" in extra_args
    assert "claude" in extra_args
    assert "--model" in extra_args
    assert "custom-claude-model" in extra_args

    import os

    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-override-key"


def test_graph_build_native_backend_skips_model(tmp_path: Path, monkeypatch) -> None:
    """Native backends (openai, claude, gemini) should NOT pass --model.

    Graphify already knows the correct default model for each native backend.
    Overriding it with Forge's router model names causes 404 errors when
    those names don't match what the upstream API accepts.
    """
    # Clean ALL provider env vars to prevent leaks from prior tests
    for ev in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
    ):
        monkeypatch.delenv(ev, raising=False)
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))

    # Set ANTHROPIC_API_KEY so anthropic is auto-detected
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-native-test")

    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")

    runner = CliRunner()

    from forgecli.graph.repository import BuildResult, GraphSnapshot

    mock_snapshot = GraphSnapshot(root=str(tmp_path), nodes=(), edges=(), communities=())
    mock_result = BuildResult(
        snapshot=mock_snapshot, artifacts={}, raw_output="mocked build output"
    )

    with (
        patch("forgecli.core.credentials.get_api_key", return_value=None),
        patch(
            "forgecli.graph.backend_forgegraph.ForgeRepositoryGraph.is_available",
            return_value=True,
        ),
        patch(
            "forgecli.graph.backend_forgegraph.ForgeRepositoryGraph.build",
            return_value=mock_result,
        ) as mock_build,
    ):
        result = runner.invoke(app, ["graph", "build", "-p", str(tmp_path)])

    assert result.exit_code == 0
    mock_build.assert_called_once()
    kwargs = mock_build.call_args[1]
    extra_args = kwargs.get("extra_args", [])

    # Should pass --backend claude (from anthropic mapping)
    assert "--backend" in extra_args
    assert "claude" in extra_args

    # Should NOT pass --model — let graphify use its own default
    assert "--model" not in extra_args


@pytest.mark.parametrize(
    "cmd_name,binary_name",
    [
        ("claude", "claude"),
        ("codex", "codex"),
        ("cursor", "cursor"),
        ("antigravity", "antigravity"),
    ],
)
def test_wrapper_command_works_without_api_key(
    cmd_name: str, binary_name: str, tmp_path: Path, monkeypatch
) -> None:

    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))

    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))

    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

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


def test_mcp_auto_configuration(tmp_path: Path, monkeypatch) -> None:

    mock_home = tmp_path / "mock_home"

    mock_home.mkdir()

    mock_repo = tmp_path / "mock_repo"

    mock_repo.mkdir()

    (mock_repo / "main.py").write_text("print('hi')", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: mock_home)

    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))

    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))

    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    import subprocess

    # 1. Test Claude Code MCP Configuration
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

    claude_json_file = mock_home / ".claude.json"

    assert claude_json_file.exists()

    claude_config = json.loads(claude_json_file.read_text(encoding="utf-8"))

    assert "forge" in claude_config.get("mcpServers", {})

    # Verify other agents' configs are NOT created yet
    assert not (mock_home / ".cursor" / "mcp.json").exists()

    # 2. Test Cursor MCP Configuration
    with (
        patch("forgecli.runtime.wrappers.which", return_value="/usr/bin/cursor"),
        patch(
            "forgecli.runtime.wrappers.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ),
    ):
        runner = CliRunner()

        result = runner.invoke(app, ["cursor", "-p", str(mock_repo)], catch_exceptions=False)

        assert result.exit_code == 0

    cursor_global_file = mock_home / ".cursor" / "mcp.json"

    assert cursor_global_file.exists()

    cursor_global_config = json.loads(cursor_global_file.read_text(encoding="utf-8"))

    assert "forge" in cursor_global_config.get("mcpServers", {})

    assert (mock_repo / ".cursor" / "mcp.json").exists()

    # 3. Test Codex MCP Configuration
    with (
        patch("forgecli.runtime.wrappers.which", return_value="/usr/bin/codex"),
        patch(
            "forgecli.runtime.wrappers.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ),
    ):
        runner = CliRunner()

        result = runner.invoke(app, ["codex", "-p", str(mock_repo)], catch_exceptions=False)

        assert result.exit_code == 0

    codex_toml = mock_home / ".codex" / "config.toml"

    assert codex_toml.exists()

    assert "[mcp_servers.forge]" in codex_toml.read_text(encoding="utf-8")

    # 4. Test Antigravity MCP Configuration
    with (
        patch("forgecli.runtime.wrappers.which", return_value="/usr/bin/antigravity"),
        patch(
            "forgecli.runtime.wrappers.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ),
    ):
        runner = CliRunner()

        result = runner.invoke(app, ["antigravity", "-p", str(mock_repo)], catch_exceptions=False)

        assert result.exit_code == 0

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
