"""Tests for the forge auth subcommand group."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from forgecli.cli.main import app


def test_auth_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["auth", "--help"])
    assert result.exit_code == 0
    assert "login" in result.output


@patch("forgecli.cli.commands_auth.set_api_key")
@patch("forgecli.cli.commands_auth.bootstrap_context")
@patch("forgecli.cli.commands_auth.load_state")
@patch("forgecli.cli.commands_auth.save_state")
def test_auth_login_success_and_default(
    mock_save_state: MagicMock,
    mock_load_state: MagicMock,
    mock_bootstrap_context: MagicMock,
    mock_set_api_key: MagicMock,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))

    # Mock bootstrap context and router
    mock_router = MagicMock()
    mock_router.default_model_for.return_value = "gemini-2.5-pro"
    mock_context = MagicMock()
    mock_context.container.resolve.return_value = mock_router
    mock_bootstrap_context.return_value = mock_context

    mock_state = MagicMock()
    mock_load_state.return_value = mock_state

    runner = CliRunner()
    # Inputs:
    # 1. Selection: "1" (google)
    # 2. API Key: "my-secret-key"
    # 3. Set as active default: "y"
    result = runner.invoke(
        app,
        ["auth", "login"],
        input="1\nmy-secret-key\ny\n",
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Successfully saved API key for google" in result.output
    assert "Set 'google' (gemini-2.5-pro) as the active default provider" in result.output

    mock_set_api_key.assert_called_once_with("google", "my-secret-key")
    mock_router.default_model_for.assert_called_once_with("google")
    assert mock_state.choice == "google"
    assert mock_state.provider == "google"
    assert mock_state.model == "gemini-2.5-pro"
    mock_save_state.assert_called_once()


@patch("forgecli.cli.commands_auth.set_api_key")
def test_auth_login_invalid_selection(mock_set_api_key: MagicMock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["auth", "login"],
        input="99\n",
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    assert "Invalid selection: 99" in result.output
    mock_set_api_key.assert_not_called()


@patch("forgecli.cli.commands_auth.set_api_key")
def test_auth_login_empty_api_key(mock_set_api_key: MagicMock) -> None:
    runner = CliRunner()
    # Select google (1), then enter empty API key
    result = runner.invoke(
        app,
        ["auth", "login"],
        input="1\n\n",
        catch_exceptions=False,
    )
    # click prompt aborted since empty input was entered twice or click prompt aborts on EOF/empty
    assert result.exit_code == 1
    mock_set_api_key.assert_not_called()


@patch("forgecli.cli.commands_auth.set_api_key")
@patch("typer.prompt")
def test_auth_login_abort_on_provider_selection(mock_prompt: MagicMock, mock_set_api_key: MagicMock) -> None:
    mock_prompt.side_effect = typer.Abort()
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["auth", "login"],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    assert "Cancelled." in result.output
    mock_set_api_key.assert_not_called()
