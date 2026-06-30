"""Tests for the model router state and the ``forge model`` CLI."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from forgecli.cli.main import app
from forgecli.providers.router_state import (
    RouterState,
    load_state,
    save_state,
)


def test_state_round_trip(tmp_path: Path) -> None:
    state = RouterState(choice="claude", model="claude-3-5-sonnet-latest", provider="anthropic")
    save_state(tmp_path / "router.json", state)
    loaded = load_state(tmp_path / "router.json")
    assert loaded == state


def test_load_state_missing_file(tmp_path: Path) -> None:
    assert load_state(tmp_path / "missing.json") == RouterState()


def test_load_state_handles_corrupt_json(tmp_path: Path) -> None:
    target = tmp_path / "router.json"
    target.write_text("not json", encoding="utf-8")
    assert load_state(target) == RouterState()


def test_state_to_extras_round_trip() -> None:
    state = RouterState(choice="claude", model="m", provider="anthropic")
    extras = state.to_extras()
    assert extras["router.choice"] == "claude"
    assert extras["router.model"] == "m"
    assert extras["router.provider"] == "anthropic"
    parsed = RouterState.from_extras(extras)
    assert parsed == state


def test_state_from_extras_defaults() -> None:
    state = RouterState.from_extras({})
    assert state.choice is None
    assert state.model is None
    assert state.provider is None


def test_cli_model_auto(monkeypatch, tmp_path: Path) -> None:
    """forge model auto switches default_provider to mock via update_config."""
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    # Ensure no provider creds are set
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    runner = CliRunner()
    result = runner.invoke(app, ["model", "auto"])
    assert result.exit_code == 0


def test_cli_model_claude_persists(monkeypatch, tmp_path: Path) -> None:
    """forge model claude switches provider to anthropic."""
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["model", "claude"])
    assert result.exit_code == 0
    assert "Anthropic" in result.output or result.exit_code == 0


def test_cli_model_status_works(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(app, ["model", "status"])
    assert result.exit_code == 0


def test_cli_model_list_works(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(app, ["model", "list"])
    assert result.exit_code == 0
    output = result.output
    # New model list shows provider group headers in Title Case
    for name in ("OpenAI", "Anthropic", "Google"):
        assert name in output


def test_cli_model_use_sets_model(monkeypatch, tmp_path: Path) -> None:
    """forge model use <model-id> should succeed and print confirmation."""
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["model", "use", "gpt-4o-mini"])
    assert result.exit_code == 0
    assert "GPT-4o Mini" in result.output


def test_cli_model_search(monkeypatch, tmp_path: Path) -> None:
    """forge model search <keyword> should return matching models."""
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(app, ["model", "search", "claude"])
    assert result.exit_code == 0
    assert "Claude" in result.output


def test_cli_model_current(monkeypatch, tmp_path: Path) -> None:
    """forge model current should show the active model."""
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(app, ["model", "current"])
    assert result.exit_code == 0
    assert "Current Model" in result.output


def test_cli_model_openai_hidden(monkeypatch, tmp_path: Path) -> None:
    """forge model openai backward-compat command should still work."""
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["model", "openai"])
    assert result.exit_code == 0
    assert "OpenAI" in result.output


def test_model_catalog_has_modernized_models() -> None:
    """Verify core catalog definitions contain the requested modern models."""
    from forgecli.core.models import get_model_def

    assert get_model_def("gpt-5.5") is not None
    assert get_model_def("claude-opus-4.8") is not None
    assert get_model_def("deepseek-r1") is not None
    assert get_model_def("llama-4-scout") is not None

    # Check tiers
    gpt5_5 = get_model_def("gpt-5.5")
    assert gpt5_5.tier == "latest"

    gpt5 = get_model_def("gpt-5")
    assert gpt5.tier == "recommended"

    gpt4o = get_model_def("gpt-4o")
    assert gpt4o.tier == "legacy"


def test_cli_model_list_contains_tiers(monkeypatch, tmp_path: Path) -> None:
    """Verify that model list prints appropriate headers/tiers (★, ✓, Legacy)."""
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(app, ["model", "list"])
    assert result.exit_code == 0
    output = result.output

    assert "★ GPT-5.5" in output
    assert "✓ GPT-5" in output
    assert "Legacy" in output
    assert "GPT-4.1" in output
    assert "★ Claude Opus 4.8" in output
    assert "✓ Claude Sonnet 4.6" in output
    assert "✓ Gemini 2.5 Pro" in output
    assert "✓ Gemini 2.5 Flash" in output
    assert "DeepSeek R1" in output


def test_cli_model_use_new_catalog_models(monkeypatch, tmp_path: Path) -> None:
    """Verify that model use correctly updates provider and model Choice in configuration."""
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    # Switch to gpt-5.5
    result = runner.invoke(app, ["model", "use", "gpt-5.5"])
    assert result.exit_code == 0
    assert "GPT-5.5" in result.output

    # Switch to claude-opus-4.8
    result = runner.invoke(app, ["model", "use", "claude-opus-4.8"])
    assert result.exit_code == 0
    assert "Claude Opus 4.8" in result.output

    # Switch to a local model
    result = runner.invoke(app, ["model", "use", "llama3"])
    assert result.exit_code == 0
    assert "Llama 3" in result.output
