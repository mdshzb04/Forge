"""End-to-end integration tests for the unified Forge runtime pipeline.

Tests verify complete request flows through the full middleware pipeline,
wrapper execution, plugin lifecycle, and diagnostic commands.
"""



from __future__ import annotations

import asyncio
from pathlib import Path


def _make_repo(tmp_path: Path) -> Path:

    """Create a minimal mock repo with .git and some source files."""

    (tmp_path / ".git").mkdir()

    (tmp_path / "src").mkdir()

    (tmp_path / "src" / "main.py").write_text("def hello(): return 'world'\n", encoding="utf-8")

    (tmp_path / "src" / "utils.py").write_text("import os\n\ndef helper(): pass\n", encoding="utf-8")

    (tmp_path / "README.md").write_text("# Test Repo\n", encoding="utf-8")

    return tmp_path





class TestUnifiedPipeline:

    """E2E tests for the full middleware pipeline execution."""



    def test_build_default_pipeline_contains_all_stages(self) -> None:

        from forgecli.runtime.pipeline_runner import build_default_pipeline

        pipeline = build_default_pipeline()

        stages = pipeline.list()

        names = [type(s).__name__ for s in stages]



        assert "TelemetryMiddleware" in names

        assert "AuthenticationMiddleware" in names

        assert "PolicyMiddleware" in names

        assert "ProviderMiddleware" in names

        assert "ResponseOptimizerMiddleware" in names

        assert "PonytailAdapterMiddleware" in names

        assert "CavemanAdapterMiddleware" in names

        assert "ResilienceMiddleware" in names



    def test_pipeline_stages_sorted_by_priority(self) -> None:

        from forgecli.runtime.pipeline_runner import build_default_pipeline

        pipeline = build_default_pipeline()

        stages = pipeline.list()

        priorities = [s.priority for s in stages]

        assert priorities == sorted(priorities, reverse=True)



        assert priorities[0] == 1000



    def test_pipeline_async_execution_with_mock_provider(self, tmp_path: Path) -> None:

        from forgecli.runtime.pipeline_runner import run_pipeline_async
        from forgecli.runtime_core.request import AIRequest



        repo = _make_repo(tmp_path)

        request = AIRequest(

            request_id="e2e-test-1",

            prompt="What does main.py do?",

            provider_name="mock",

            model_name="mock-model",

            temperature=0.2,

            stream=False,

            session_id="e2e-session",

        )



        async def _run():

            response = await run_pipeline_async(

                request=request,

                repo_root=repo,

                provider="mock",

                model="mock-model",

            )

            return response



        response = asyncio.run(_run())

        assert response is not None

        assert response.request_id == "e2e-test-1"



    def test_pipeline_sync_execution(self, tmp_path: Path) -> None:

        from forgecli.runtime.pipeline_runner import run_pipeline_sync
        from forgecli.runtime_core.request import AIRequest



        repo = _make_repo(tmp_path)

        request = AIRequest(

            request_id="e2e-sync-1",

            prompt="Hello",

            provider_name="mock",

            model_name="mock-model",

            temperature=0.2,

            stream=False,

            session_id="e2e-sync",

        )

        response = run_pipeline_sync(request=request, repo_root=repo, provider="mock", model="mock-model")

        assert response is not None



    def test_pipeline_with_ponytail_caveman_enabled(self, tmp_path: Path) -> None:

        from forgecli.runtime.pipeline_runner import build_default_pipeline

        pipeline = build_default_pipeline(

            repo_root=tmp_path,

            ponytail_intensity="ultra",

            caveman_intensity="full",

        )

        stages = pipeline.list()

        names = [type(s).__name__ for s in stages]

        assert "PonytailAdapterMiddleware" in names

        assert "CavemanAdapterMiddleware" in names





class TestUnifiedWrappers:

    """E2E tests for the unified wrapper launch path."""



    def test_all_wrappers_registered_in_agents(self) -> None:

        from forgecli.runtime.agents import AGENTS

        expected = {"claude", "codex", "cursor", "antigravity", "gemini", "aider", "opencode", "commandcode"}

        assert set(AGENTS) == expected



    def test_all_wrappers_have_valid_specs(self) -> None:

        from forgecli.runtime.agents import AGENTS, AgentSpec, MCPTarget

        for spec in AGENTS.values():

            assert isinstance(spec, AgentSpec)

            assert spec.id

            assert spec.name

            assert spec.binary

            assert isinstance(spec.install_hint, str)

            for target in spec.mcp_targets:

                assert isinstance(target, MCPTarget)

                assert target.base in {"home", "repo"}

                assert target.fmt in {"json", "toml"}



    def test_mcp_agents_have_targets(self) -> None:

        from forgecli.runtime.agents import AGENTS

        for agent_id, spec in AGENTS.items():

            if spec.supports_mcp:

                assert len(spec.mcp_targets) > 0, f"{agent_id} supports MCP but has no targets"

            else:

                assert agent_id == "aider", "Only aider should have supports_mcp=False"



    def test_context_flag_agents_work(self) -> None:

        from forgecli.runtime.agents import AGENTS

        aider = AGENTS["aider"]

        assert aider.context_flag == "--read"

        assert not aider.supports_mcp



    def test_prepare_and_merge_context(self, tmp_path: Path) -> None:

        from forgecli.runtime.prepare import build_merged_context, prepare_runtime_sync

        repo = _make_repo(tmp_path)

        prepared = prepare_runtime_sync(repo, force=True)

        merged = build_merged_context(repo_context=prepared.context_summary, repo_root=prepared.root)

        assert len(merged) > 0

        assert "Repository:" in merged or "Repository" in merged





class TestDiagnosticCommands:

    """E2E tests for CLI diagnostic commands."""



    def test_diagnostics_module_imports(self) -> None:

        from forgecli.cli.commands_diagnostics import (
            doctor_cmd,
            explain_cmd,
            profile_cmd,
            stats_cmd,
            status_cmd,
        )

        assert callable(status_cmd)

        assert callable(stats_cmd)

        assert callable(profile_cmd)

        assert callable(explain_cmd)

        assert callable(doctor_cmd)



    def test_explain_has_all_topics(self) -> None:



        import subprocess
        import sys

        for topic in ["pipeline", "ponytail", "caveman", "graphify", "mcp", "daemon"]:

            result = subprocess.run(

                [sys.executable, "-m", "forgecli.cli.main", "explain", topic],

                capture_output=True, text=True,

            )

            assert result.returncode == 0, f"explain {topic} failed"

            assert len(result.stdout) > 50, f"explain {topic} output too short"



    def test_stats_command_runs(self) -> None:

        import subprocess
        import sys

        result = subprocess.run(

            [sys.executable, "-m", "forgecli.cli.main", "stats"],

            capture_output=True, text=True,

        )

        assert result.returncode == 0

        assert "Forge Statistics" in result.stdout or "Pipeline stages" in result.stdout



    def test_inspect_command_runs(self) -> None:

        import subprocess
        import sys

        result = subprocess.run(

            [sys.executable, "-m", "forgecli.cli.main", "inspect"],

            capture_output=True, text=True,

        )

        assert result.returncode == 0

        assert "Middleware Pipeline" in result.stdout



    def test_doctor_command_runs(self) -> None:

        import subprocess
        import sys

        result = subprocess.run(

            [sys.executable, "-m", "forgecli.cli.main", "doctor"],

            capture_output=True, text=True,

        )

        assert result.returncode == 0

        assert "Forge Doctor" in result.stdout





class TestPluginLifecycle:

    """E2E tests for plugin install/list/remove flow."""



    def test_plugin_list_runs(self) -> None:

        import subprocess
        import sys

        result = subprocess.run(

            [sys.executable, "-m", "forgecli.cli.main", "plugin", "list"],

            capture_output=True, text=True,

        )

        assert result.returncode == 0



    def test_plugin_doctor_runs(self) -> None:

        import subprocess
        import sys

        result = subprocess.run(

            [sys.executable, "-m", "forgecli.cli.main", "plugin", "doctor"],

            capture_output=True, text=True,

        )

        assert result.returncode == 0





class TestContextPreparation:

    """E2E tests for context preparation pipeline."""



    def test_prepare_empty_repo(self, tmp_path: Path, monkeypatch) -> None:

        monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))

        monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))

        monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

        (tmp_path / ".git").mkdir()

        from forgecli.runtime.prepare import prepare_runtime_sync

        prepared = prepare_runtime_sync(tmp_path, force=True)

        assert prepared.context_summary.strip()

        assert "Empty repository" in prepared.context_summary



    def test_behavior_instructions_included(self, tmp_path: Path, monkeypatch) -> None:

        monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))

        monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))

        monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

        (tmp_path / ".git").mkdir()

        from forgecli.runtime.prepare import build_merged_context, prepare_runtime_sync

        prepared = prepare_runtime_sync(tmp_path, force=True)

        merged = build_merged_context(repo_context=prepared.context_summary, repo_root=tmp_path)

        assert "SYSTEM INSTRUCTION" in merged





class TestMiddlewareDefaults:

    """Verify all 17 middleware defaults delegate correctly."""



    def test_all_default_middlewares_instantiate(self) -> None:

        from forgecli.middleware.defaults import (
            AuthenticationMiddleware,
            CachingMiddleware,
            ContextOptimizerMiddleware,
            ConversationMiddleware,
            DependencyGraphMiddleware,
            GraphifyMiddleware,
            HistoryCompressorMiddleware,
            PolicyMiddleware,
            PromptOptimizerMiddleware,
            ProviderMiddleware,
            RepositoryPlannerMiddleware,
            ResponseOptimizerMiddleware,
            SemanticRetrievalMiddleware,
            StreamingMiddleware,
            SymbolLookupMiddleware,
            TelemetryMiddleware,
            TokenPlannerMiddleware,
        )

        classes = [

            TelemetryMiddleware, AuthenticationMiddleware, PolicyMiddleware,

            CachingMiddleware, HistoryCompressorMiddleware, TokenPlannerMiddleware,

            ContextOptimizerMiddleware, ConversationMiddleware, PromptOptimizerMiddleware,

            RepositoryPlannerMiddleware, DependencyGraphMiddleware, SymbolLookupMiddleware,

            GraphifyMiddleware, SemanticRetrievalMiddleware, StreamingMiddleware,

            ProviderMiddleware, ResponseOptimizerMiddleware,

        ]

        for cls in classes:

            mw = cls()

            assert mw.enabled is True

            assert isinstance(mw.priority, int)



    def test_all_default_middlewares_execute(self) -> None:

        from forgecli.middleware.context import RequestContext, ResponseContext
        from forgecli.middleware.defaults import (
            AuthenticationMiddleware,
            CachingMiddleware,
            ContextOptimizerMiddleware,
            ConversationMiddleware,
            DependencyGraphMiddleware,
            GraphifyMiddleware,
            HistoryCompressorMiddleware,
            PolicyMiddleware,
            PromptOptimizerMiddleware,
            ProviderMiddleware,
            RepositoryPlannerMiddleware,
            ResponseOptimizerMiddleware,
            SemanticRetrievalMiddleware,
            StreamingMiddleware,
            SymbolLookupMiddleware,
            TelemetryMiddleware,
            TokenPlannerMiddleware,
        )
        from forgecli.runtime_core.context import RuntimeContext
        from forgecli.runtime_core.request import AIRequest
        from forgecli.runtime_core.response import AIResponse



        req = AIRequest(

            request_id="test-mw",

            prompt="test",

            provider_name="mock",

            model_name="mock",

            session_id="test",

        )

        ctx = RuntimeContext(session_id="test", workspace=Path("."), repository_root=Path("."))

        req_ctx = RequestContext(

            ai_request=req, runtime_context=ctx, execution_id="test",

        )



        async def mock_next(r: RequestContext) -> ResponseContext:

            return ResponseContext(

                ai_response=AIResponse(

                    response_id="r", request_id="r", content="ok",

                    finish_reason="stop", latency_ms=1.0,

                )

            )



        mws = [

            TelemetryMiddleware(), AuthenticationMiddleware(), PolicyMiddleware(),

            CachingMiddleware(), HistoryCompressorMiddleware(), TokenPlannerMiddleware(),

            ContextOptimizerMiddleware(), ConversationMiddleware(), PromptOptimizerMiddleware(),

            RepositoryPlannerMiddleware(), DependencyGraphMiddleware(), SymbolLookupMiddleware(),

            GraphifyMiddleware(), SemanticRetrievalMiddleware(), StreamingMiddleware(),

            ProviderMiddleware(), ResponseOptimizerMiddleware(),

        ]

        for mw in mws:

            resp = asyncio.run(mw(req_ctx, mock_next))

            assert resp.ai_response is not None

