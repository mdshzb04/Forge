"""Unit tests for the Token Budget Planner and Context Window Optimizer (Phase 4)."""



from __future__ import annotations

from pathlib import Path

import pytest

from forgecli.budget.middleware import ContextOptimizerMiddleware, TokenPlannerMiddleware
from forgecli.budget.planner import TokenBudget, TokenPlanner
from forgecli.budget.window import ContextWindowManager
from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.registry.model_registry import ModelProfile, ModelRegistry
from forgecli.runtime_core.context import RuntimeContext
from forgecli.runtime_core.request import AIRequest


def make_test_request(model_name: str = "gpt-4o", max_tokens: int | None = None) -> AIRequest:

    messages = [

        {"role": "system", "content": "You are a helpful assistant."},

        {"role": "user", "content": "A" * 8000},

        {"role": "assistant", "content": "B" * 4000},

        {"role": "user", "content": "C" * 800},

    ]

    return AIRequest(

        request_id="req-123",

        provider_name="openai",

        model_name=model_name,

        session_id="session-123",

        prompt="hello context",

        messages=messages,

        max_tokens=max_tokens,

    )





def test_token_planner_budget() -> None:

    registry = ModelRegistry()

    registry.register_profile(ModelProfile(

        name="small-model",

        context_window=2000,

        max_output_tokens=500,

        input_token_cost=1.0,

        output_token_cost=1.0,

        capabilities=set(),

    ))

    planner = TokenPlanner(registry=registry)





    budget = planner.plan_budget("small-model")

    assert budget.max_context_tokens == 2000

    assert budget.requested_completion_tokens == 500

    assert budget.reserved_system_tokens == 500

    assert budget.available_context_tokens == 1000





    budget2 = planner.plan_budget("unknown-model", requested_max_tokens=2048)

    assert budget2.max_context_tokens == 8192

    assert budget2.requested_completion_tokens == 2048

    assert budget2.available_context_tokens == 5644





def test_context_window_trimming() -> None:

    planner = TokenPlanner()

    manager = ContextWindowManager(planner)





    budget = TokenBudget(

        model_name="test",

        max_context_tokens=3000,

        requested_completion_tokens=1000,

        reserved_system_tokens=500,

        available_context_tokens=1500,

    )















    req = make_test_request()



    trimmed = manager.trim_messages(req.messages, budget)





    assert trimmed[0]["role"] == "system"



    assert trimmed[-1]["content"] == "C" * 800





    assert not any("A" * 8000 in m.get("content", "") for m in trimmed)





@pytest.mark.asyncio

async def test_budget_middlewares() -> None:



    planner_mw = TokenPlannerMiddleware()

    optimizer_mw = ContextOptimizerMiddleware()



    assert planner_mw.priority == 750

    assert optimizer_mw.priority == 700



    req_ctx = RequestContext(

        ai_request=make_test_request(model_name="gpt-4o"),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-123",

    )



    async def mock_call(req: RequestContext) -> ResponseContext:

        return ResponseContext(execution_id=req.execution_id)





    await planner_mw(req_ctx, mock_call)

    budget = req_ctx.metadata.get("token_budget")

    assert budget is not None

    assert budget.max_context_tokens == 128000





    budget.available_context_tokens = 1500

    req_ctx.metadata["token_budget"] = budget





    await optimizer_mw(req_ctx, mock_call)





    assert len(req_ctx.ai_request.messages) < 4

    assert req_ctx.ai_request.messages[0]["role"] == "system"

