"""Regression tests for forge ask and forge build UX fixes."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from forgecli.cli.commands_ask import _clean_answer, _print_answer
from forgecli.cli.main import app
from forgecli.orchestrator import AskWorkflow, Orchestrator, PluginRegistry
from forgecli.plugins import Intent
from forgecli.providers.base import ChatMessage, ChatRequest, ChatResponse, Role
from forgecli.providers.mock import MockProvider, MockProviderConfig


def test_clean_answer_strips_internal_terms() -> None:
    text = "Graphify found auth.py and Ponytail optimized the prompt."
    cleaned = _clean_answer(text)
    assert "graphify" not in cleaned.lower()
    assert "ponytail" not in cleaned.lower()


def test_ask_workflow_greeting_uses_short_pipeline() -> None:
    provider = MockProvider(MockProviderConfig())
    registry = PluginRegistry()
    registry.register_workflow(AskWorkflow())
    orchestrator = Orchestrator(registry, provider=provider)
    result = asyncio.run(orchestrator.run("hi", intent=Intent.ASK))
    assert result.success
    assert "Hi!" in result.summary
    stage_names = [stage["name"] for stage in result.stages]
    assert "ponytail-optimize" not in stage_names
    assert "graphify-retrieval" not in stage_names


def test_cli_ask_prints_answer_once(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))

    async def _fake_run(question: str, path: Path, live: bool, verbose: bool = False) -> None:
        assert question == "hi"
        _print_answer("Hi! How can I help you today?")

    with patch("forgecli.cli.commands_ask._run_ask", side_effect=_fake_run):
        runner = CliRunner()
        result = runner.invoke(app, ["ask", "hi", "--mock"])
    assert result.exit_code == 0
    assert result.output.count("Hi! How can I help you today?") == 1


def test_cli_ask_greeting_mock_mode(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(app, ["ask", "hello", "--mock"])
    assert result.exit_code == 0
    assert "Hi!" in result.output
    assert "Ponytail" not in result.output
    assert "Graphify" not in result.output


def test_resolve_provider_forces_mock_when_live_false(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from forgecli.cli.bootstrap import resolve_provider_and_decision
    from forgecli.providers.mock import MockProvider

    provider, decision = resolve_provider_and_decision(live=False, cwd=tmp_path)
    assert isinstance(provider, MockProvider)
    assert decision.provider_name == "mock"


def test_build_default_live_flag_is_true() -> None:
    from typer.main import get_command

    click_cmd = get_command(app)
    build_params = click_cmd.commands["build"].params
    live_param = next(p for p in build_params if p.name == "live")

    assert "--live" in live_param.opts
    assert "--mock" in live_param.secondary_opts
    assert live_param.default is True


@pytest.mark.parametrize(
    ("prompt", "expected_file"),
    [
        ("Create main.go with hello world", "main.go"),
        ("Create index.html landing page", "index.html"),
    ],
)
def test_mock_build_no_demo_patch(prompt: str, expected_file: str) -> None:
    provider = MockProvider(MockProviderConfig())
    request = ChatRequest(
        model="mock-model",
        messages=[
            ChatMessage(role=Role.SYSTEM, content="Return ONLY a unified diff."),
            ChatMessage(role=Role.USER, content=prompt),
        ],
    )
    response = asyncio.run(provider.chat(request))
    assert expected_file not in response.message.content
    assert "diff --git" not in response.message.content


def test_build_render_shows_only_files() -> None:
    from io import StringIO

    from rich.console import Console

    from forgecli.cli.commands_build import render_pipeline_result

    diff = (
        "diff --git a/main.go b/main.go\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/main.go\n"
        "@@ -0,0 +1,3 @@\n"
        "+package main\n"
        "+\n"
        "+func main() {}\n"
    )
    buffer = StringIO()
    with patch("forgecli.cli.commands_build.get_console", return_value=Console(file=buffer)):
        render_pipeline_result(
            success=True,
            prompt="Create main.go",
            diff_text=diff,
            applied_files=[],
            stages=[],
            decision_provider="mock",
            decision_model="mock-model",
            optimized_notes=[],
            ponytail_active=False,
            test_returncode=None,
            failure_stage=None,
            retrieval_text="",
            internal_summary="internal diagnostics",
            verbose=False,
            diff=False,
        )
    output = buffer.getvalue()
    assert "main.go" in output
    assert "package main" in output
    assert "Build completed" not in output
    assert "internal diagnostics" not in output


def test_cli_build_mock_offline_no_demo_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["build", "--mock", "--no-tests", "Create main.go with hello world"],
    )
    assert result.exit_code == 0
    assert "main.go" not in result.output or "No AI provider" in result.output
    assert "package main" not in result.output


class _RecordingProvider:
    name = "recorder"

    def __init__(self) -> None:
        self.last_request: ChatRequest | None = None

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.last_request = request
        diff = (
            "diff --git a/main.go b/main.go\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/main.go\n"
            "@@ -0,0 +1,5 @@\n"
            "+package main\n"
            "+\n"
            "+import \"fmt\"\n"
            "+\n"
            "+func main() { fmt.Println(\"hi\") }\n"
        )
        return ChatResponse(
            model="recorder-model",
            message=ChatMessage(role=Role.ASSISTANT, content=diff),
            finish_reason="stop",
        )


def test_build_pipeline_uses_injected_provider_for_diff(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    provider = _RecordingProvider()

    def _fake_resolve(*, live: bool, cwd: Path):
        from forgecli.providers.router import RouteDecision, SelectionMode

        return provider, RouteDecision(
            provider_name="recorder",
            model="recorder-model",
            mode=SelectionMode.EXPLICIT,
        )

    with patch(
        "forgecli.cli.bootstrap.resolve_provider_and_decision",
        side_effect=_fake_resolve,
    ):
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["build", "--no-tests", "Create main.go that prints hi"],
        )

    assert result.exit_code == 0
    assert provider.last_request is not None
    user_message = next(
        message.content
        for message in provider.last_request.messages
        if message.role is Role.USER
    )
    assert "main.go" in user_message.lower() or "Create main.go" in user_message
    assert "main.go" in result.output
    assert "package main" in result.output


def test_is_file_requested() -> None:
    from pathlib import Path

    from forgecli.build.diff_extract import is_file_requested

    root = Path(__file__).parent.parent
    # 1. File exists
    assert is_file_requested("tests/test_ask_build_regressions.py", "anything", root) is True

    # 2. File doesn't exist, but requested in prompt
    assert is_file_requested("main.go", "Create a main.go file", root) is True
    assert is_file_requested("src/promise-example.js", "implement a promise-example.js module", root) is True
    assert is_file_requested("foo.py", "generate foo.py", root) is True

    # 3. File doesn't exist, and NOT requested in prompt
    assert is_file_requested("foo.py", "Create a main.go file", root) is False
    assert is_file_requested("main.rs", "Implement a simple webserver in python", root) is False

    # 4. Token matching
    assert is_file_requested("math_ops.py", "Create math operations module", root) is True

    # 5. Tests matching
    assert is_file_requested("tests/test_regression.py", "Add regression tests", root) is True


def test_filter_diff_unrequested_files() -> None:
    from pathlib import Path

    from forgecli.build.diff_extract import filter_diff

    diff = (
        "diff --git a/main.go b/main.go\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/main.go\n"
        "@@ -0,0 +1,3 @@\n"
        "+package main\n"
        "diff --git a/foo.py b/foo.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/foo.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+print('foo')\n"
    )

    filtered = filter_diff(diff, "Create main.go with hello world", Path("/tmp"))
    assert "main.go" in filtered
    assert "foo.py" not in filtered


def test_clean_source_code_removes_ponytail_comments() -> None:
    from forgecli.build.apply import clean_source_code

    code = (
        "def main():\n"
        "    # YAGNI: we cut unused functions\n"
        "    # safe because this is simple\n"
        "    # Ponytail rules: don't write too much\n"
        "    # regular comment about logic\n"
        "    x = 1  # reasoning: optimizer said so\n"
        "    y = 2\n"
    )
    cleaned = clean_source_code(code)
    assert "YAGNI" not in cleaned
    assert "safe because" not in cleaned
    assert "Ponytail" not in cleaned
    assert "optimizer" not in cleaned
    assert "regular comment about logic" in cleaned
    assert "y = 2" in cleaned


def test_cli_build_unrequested_files_blocked(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path))
    provider = _RecordingProvider()

    def _fake_resolve(*, live: bool, cwd: Path):
        from forgecli.providers.router import RouteDecision, SelectionMode

        return provider, RouteDecision(
            provider_name="recorder",
            model="recorder-model",
            mode=SelectionMode.EXPLICIT,
        )

    # Let the recorder provider return a diff containing a requested file (main.go)
    # and a placeholder file (foo.py)
    class _CustomRecordingProvider(_RecordingProvider):
        async def chat(self, request: ChatRequest) -> ChatResponse:
            self.last_request = request
            diff = (
                "diff --git a/main.go b/main.go\n"
                "new file mode 100644\n"
                "--- /dev/null\n"
                "+++ b/main.go\n"
                "@@ -0,0 +1,5 @@\n"
                "+package main\n"
                "+func main() {}\n"
                "diff --git a/foo.py b/foo.py\n"
                "new file mode 100644\n"
                "--- /dev/null\n"
                "+++ b/foo.py\n"
                "@@ -0,0 +1,2 @@\n"
                "+print('foo')\n"
            )
            return ChatResponse(
                model="recorder-model",
                message=ChatMessage(role=Role.ASSISTANT, content=diff),
                finish_reason="stop",
            )

    provider = _CustomRecordingProvider()

    with patch(
        "forgecli.cli.bootstrap.resolve_provider_and_decision",
        side_effect=_fake_resolve,
    ):
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["build", "--no-tests", "-p", str(tmp_path), "Create main.go that prints hi"],
        )

    assert result.exit_code == 0
    # main.go should be created
    assert (tmp_path / "main.go").exists()
    # foo.py should NOT be created
    assert not (tmp_path / "foo.py").exists()

