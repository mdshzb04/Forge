"""Unit tests for Dialogue Session Manager, History Compression, and Adapters (Phase 3)."""



from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from forgecli.conversation.manager import SessionManager
from forgecli.conversation.session import Session
from forgecli.graph.repository import (
    BuildResult,
    ExplainResult,
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    QueryResult,
    RepositoryGraph,
)
from forgecli.memory.middleware import HistoryCompressionMiddleware
from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.middleware.forgegraph_adapter import ForgeGraphAdapterMiddleware
from forgecli.middleware.promptforge_adapter import PromptForgeAdapterMiddleware
from forgecli.middleware.responseforge_adapter import ResponseForgeAdapterMiddleware
from forgecli.runtime_core.context import RuntimeContext
from forgecli.runtime_core.request import AIRequest, FileContext
from forgecli.runtime_core.response import AIResponse


def make_test_request(

    prompt: str = "hello",

    messages: list[dict[str, str]] | None = None,

    files: list[FileContext] | None = None,

) -> AIRequest:

    return AIRequest(

        request_id="req-123",

        provider_name="openai",

        model_name="gpt-4o",

        session_id="session-123",

        prompt=prompt,

        messages=messages or [],

        attached_files=files or [],

    )





def test_session_intelligence() -> None:



    session = Session(session_id="s1")

    session.append_message("user", "hello")

    session.append_message("assistant", "hi")

    assert len(session.history) == 2

    assert session.history[0]["role"] == "user"



    session.clear_history()

    assert len(session.history) == 0





def test_session_manager_persistence() -> None:

    with tempfile.TemporaryDirectory() as tmp_dir:

        persistence_path = Path(tmp_dir)

        manager = SessionManager(persistence_dir=persistence_path)





        session = manager.get_or_create_session("sess-1")

        session.append_message("user", "hello persistence")

        manager.save_session("sess-1")





        manager2 = SessionManager(persistence_dir=persistence_path)

        loaded = manager2.get_or_create_session("sess-1")

        assert len(loaded.history) == 1

        assert loaded.history[0]["content"] == "hello persistence"





        manager2.delete_session("sess-1")

        manager3 = SessionManager(persistence_dir=persistence_path)

        loaded3 = manager3.get_or_create_session("sess-1")

        assert len(loaded3.history) == 0





@pytest.mark.asyncio

async def test_history_compression_middleware() -> None:



    middleware = HistoryCompressionMiddleware(keep_recent_turns=2)

    assert middleware.priority == 700



    messages = [

        {"role": "user", "content": "turn 1"},

        {"role": "assistant", "content": "turn 2"},

        {"role": "user", "content": "turn 3"},

        {"role": "assistant", "content": "turn 4"},

    ]

    ai_req = make_test_request(messages=messages)

    req_ctx = RequestContext(

        ai_request=ai_req,

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-123",

    )



    async def call_next(req: RequestContext) -> ResponseContext:

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-123",

                request_id=req.ai_request.request_id,

                content="success",

                finish_reason="stop",

                latency_ms=1.0,

            ),

            execution_id=req.execution_id,

        )



    await middleware(req_ctx, call_next)





    assert len(req_ctx.ai_request.messages) == 3

    assert req_ctx.ai_request.messages[0]["role"] == "system"

    assert "COMPRESSED CONVERSATION HISTORY" in req_ctx.ai_request.messages[0]["content"]

    assert req_ctx.ai_request.messages[1]["content"] == "turn 3"

    assert req_ctx.ai_request.messages[2]["content"] == "turn 4"





@pytest.mark.asyncio

async def test_promptforge_adapter_middleware() -> None:

    middleware = PromptForgeAdapterMiddleware(intensity="lite")

    assert middleware.priority == 600



    ai_req = make_test_request(prompt="write a script")

    req_ctx = RequestContext(

        ai_request=ai_req,

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-123",

    )



    async def call_next(req: RequestContext) -> ResponseContext:

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-123",

                request_id=req.ai_request.request_id,

                content="success",

                finish_reason="stop",

                latency_ms=1.0,

            ),

            execution_id=req.execution_id,

        )



    await middleware(req_ctx, call_next)



    assert req_ctx.metadata.get("promptforge_optimized") is True



    assert "lazier" in req_ctx.ai_request.messages[0]["content"].lower()





@pytest.mark.asyncio

async def test_responseforge_adapter_middleware() -> None:

    middleware = ResponseForgeAdapterMiddleware(intensity="lite")

    assert middleware.priority == 580



    ai_req = make_test_request(prompt="how to compile c++")

    req_ctx = RequestContext(

        ai_request=ai_req,

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-123",

    )



    async def call_next(req: RequestContext) -> ResponseContext:

        return ResponseContext(

            ai_response=AIResponse(

                response_id="resp-123",

                request_id=req.ai_request.request_id,

                content="success",

                finish_reason="stop",

                latency_ms=1.0,

            ),

            execution_id=req.execution_id,

        )



    await middleware(req_ctx, call_next)



    assert req_ctx.metadata.get("responseforge_optimized") is True



    assert "concise" in req_ctx.ai_request.messages[0]["content"].lower() or "omit" in req_ctx.ai_request.messages[0]["content"].lower()





class FakeRepositoryGraph(RepositoryGraph):

    def __init__(self, available: bool = True, snapshot: GraphSnapshot | None = None) -> None:

        self._available = available

        self._snapshot = snapshot



    async def is_available(self) -> bool:

        return self._available



    async def load(self) -> GraphSnapshot:

        if self._snapshot is None:

            raise Exception("No snapshot")

        return self._snapshot



    async def build(self, *, force: bool = False) -> BuildResult:

        return BuildResult(snapshot=self._snapshot)



    async def query(self, question: str, *, budget: int = 2000) -> QueryResult:

        return QueryResult(question=question, answer="fake")



    async def explain(self, target: str) -> ExplainResult:

        return ExplainResult(target=target, explanation="fake")



    async def shortest_path(self, a: str, b: str) -> list[GraphEdge]:

        return []



    async def affected(self, target: str, *, relation = None, depth: int = 2) -> list[GraphEdge]:

        return []





@pytest.mark.asyncio

async def test_forgegraph_adapter_middleware() -> None:



    with tempfile.TemporaryDirectory() as tmp_dir:

        repo_root = Path(tmp_dir)

        source_file = "utils.py"

        full_path = repo_root / source_file

        full_path.write_text("def helper_func(): pass", encoding="utf-8")





        node = GraphNode(id="n1", label="helper_func", source_file=source_file)

        snapshot = GraphSnapshot(root=str(repo_root), nodes=(node,), edges=())



        graph = FakeRepositoryGraph(available=True, snapshot=snapshot)

        middleware = ForgeGraphAdapterMiddleware(graph)

        assert middleware.priority == 400





        ai_req = make_test_request(prompt="helper_func")

        req_ctx = RequestContext(

            ai_request=ai_req,

            runtime_context=RuntimeContext(session_id="test", workspace=repo_root, repository_root=repo_root),

            execution_id="exec-123",

        )



        async def call_next(req: RequestContext) -> ResponseContext:

            return ResponseContext(

                ai_response=AIResponse(

                    response_id="resp-123",

                    request_id=req.ai_request.request_id,

                    content="success",

                    finish_reason="stop",

                    latency_ms=1.0,

                ),

                execution_id=req.execution_id,

            )



        await middleware(req_ctx, call_next)





        assert len(req_ctx.ai_request.attached_files) == 1

        assert req_ctx.ai_request.attached_files[0].filepath == "utils.py"

        assert req_ctx.ai_request.attached_files[0].content == "def helper_func(): pass"

        assert req_ctx.metadata.get("forgegraph_queried") is True

        assert req_ctx.metadata.get("forgegraph_matched_nodes_count") == 1

