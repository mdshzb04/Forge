"""Tests for the forge commit subcommand."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from forgecli.cli.main import app
from forgecli.providers.base import ChatMessage, ChatResponse, Role


def test_commit_no_staged_changes(tmp_path: Path, monkeypatch) -> None:
    # Setup temporary directory as working directory
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    # Mock subprocess.run for git diff --cached to return empty output
    fake_run = MagicMock()
    fake_run.return_value = subprocess.CompletedProcess(
        args=["git", "diff", "--cached"], returncode=0, stdout=""
    )

    with patch("subprocess.run", fake_run):
        result = runner.invoke(app, ["commit", "--no-live"], catch_exceptions=False)

    assert result.exit_code == 1
    assert "No staged changes found" in result.output
    fake_run.assert_any_call(
        ["git", "diff", "--cached"],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(tmp_path),
    )


def test_commit_git_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    # Mock subprocess.run to raise CalledProcessError
    fake_run = MagicMock(
        side_effect=subprocess.CalledProcessError(
            returncode=128, cmd="git diff --cached", stderr="Not a git repository"
        )
    )

    with patch("subprocess.run", fake_run):
        result = runner.invoke(app, ["commit", "--no-live"], catch_exceptions=False)

    assert result.exit_code == 1
    assert "Failed to run 'git diff --cached'" in result.output


def test_commit_successful_with_yes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    # Mock git diff --cached to return a diff
    diff_output = "diff --git a/file.txt b/file.txt\n+hello"

    # We mock subprocess.run. We need to distinguish between:
    # 1. git diff --cached
    # 2. git commit -m ...
    def side_effect(args, **kwargs):
        if args == ["git", "diff", "--cached"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=diff_output)
        elif args[0:2] == ["git", "commit"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="Committed")
        raise ValueError(f"Unexpected subprocess call: {args}")

    fake_run = MagicMock(side_effect=side_effect)

    # Let's also mock the provider's chat response so we get a Conventional Commit message
    mock_chat_response = ChatResponse(
        model="mock-model",
        message=ChatMessage(role=Role.ASSISTANT, content="feat(core): add greeting feature"),
    )

    async def fake_chat(*args, **kwargs):
        return mock_chat_response

    with (
        patch("subprocess.run", fake_run),
        patch("forgecli.providers.mock.MockProvider.chat", fake_chat),
    ):
        result = runner.invoke(app, ["commit", "--no-live", "--yes"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "feat(core): add greeting feature" in result.output
    assert "Changes successfully committed!" in result.output
    # Check that git commit was called with the message
    fake_run.assert_any_call(
        ["git", "commit", "-m", "feat(core): add greeting feature"],
        check=True,
        cwd=Path(tmp_path),
    )


def test_commit_user_aborts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    diff_output = "diff --git a/file.txt b/file.txt\n+hello"

    def side_effect(args, **kwargs):
        if args == ["git", "diff", "--cached"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=diff_output)
        raise ValueError(f"Unexpected subprocess call: {args}")

    fake_run = MagicMock(side_effect=side_effect)
    mock_chat_response = ChatResponse(
        model="mock-model",
        message=ChatMessage(role=Role.ASSISTANT, content="feat(core): add greeting feature"),
    )

    async def fake_chat(*args, **kwargs):
        return mock_chat_response

    with (
        patch("subprocess.run", fake_run),
        patch("forgecli.providers.mock.MockProvider.chat", fake_chat),
    ):
        # We invoke and pass "n" to the prompt
        result = runner.invoke(app, ["commit", "--no-live"], input="n\n", catch_exceptions=False)

    assert result.exit_code == 0
    assert "Commit aborted." in result.output
    # Verify commit was NOT called
    for call in fake_run.call_args_list:
        assert "commit" not in call[0][0]


def test_commit_user_confirms(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    diff_output = "diff --git a/file.txt b/file.txt\n+hello"

    def side_effect(args, **kwargs):
        if args == ["git", "diff", "--cached"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=diff_output)
        elif args[0:2] == ["git", "commit"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="Committed")
        raise ValueError(f"Unexpected subprocess call: {args}")

    fake_run = MagicMock(side_effect=side_effect)
    mock_chat_response = ChatResponse(
        model="mock-model",
        message=ChatMessage(role=Role.ASSISTANT, content="feat(core): add greeting feature"),
    )

    async def fake_chat(*args, **kwargs):
        return mock_chat_response

    with (
        patch("subprocess.run", fake_run),
        patch("forgecli.providers.mock.MockProvider.chat", fake_chat),
    ):
        # We invoke and pass "y" to the prompt
        result = runner.invoke(app, ["commit", "--no-live"], input="y\n", catch_exceptions=False)

    assert result.exit_code == 0
    assert "feat(core): add greeting feature" in result.output
    assert "Changes successfully committed!" in result.output
    fake_run.assert_any_call(
        ["git", "commit", "-m", "feat(core): add greeting feature"],
        check=True,
        cwd=Path(tmp_path),
    )
