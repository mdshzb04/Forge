"""Smoke tests for the slim Forge CLI."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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
    monkeypatch.setenv("FORGECLI_GRAPHIFY_BIN", "nonexistent-graphify")

    import subprocess
    original_run = subprocess.run
    launched: dict[str, object] = {}

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
    for cmd in ("opencode", "commandcode"):
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
    assert "❌ An API key is required to build the Forge knowledge graph." in result.output


def test_wrapper_launches_without_api_key_even_if_graphify_available(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    # Ensure no API keys are set
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    # Create dummy source file to satisfy has_supported_source_files
    (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")

    import subprocess
    original_run = subprocess.run
    launched = {}

    def _fake_run(argv, *args, **kwargs):
        if argv and ("/usr/bin/claude" in argv[0] or argv[0] == "claude"):
            launched["argv"] = argv
            class _Result:
                returncode = 0
            return _Result()
        return original_run(argv, *args, **kwargs)

    with (
        patch("forgecli.runtime.wrappers.which", return_value="/usr/bin/claude"),
        patch("forgecli.runtime.wrappers.subprocess.run", side_effect=_fake_run),
        patch("forgecli.graph.backend_graphify.GraphifyRepositoryGraph.is_available", return_value=True),
        patch("forgecli.graph.backend_graphify.GraphifyRepositoryGraph.build") as mock_build,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["claude", "-p", str(tmp_path)], catch_exceptions=False)

    assert result.exit_code == 0
    assert launched.get("argv") in (["/usr/bin/claude"], ["claude"])
    mock_build.assert_not_called()


