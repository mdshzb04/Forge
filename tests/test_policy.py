"""Unit tests for Policy Engine, Safety Rules, and Policy Middleware (Phase 2)."""



from __future__ import annotations

from pathlib import Path

import pytest

from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.policy.engine import PolicyEngine
from forgecli.policy.exceptions import PolicyViolationError
from forgecli.policy.middleware import PolicyMiddleware
from forgecli.policy.rules import (
    BillingBudgetRule,
    FileSizeLimitRule,
    PathExclusionRule,
    SecretScanningRule,
)
from forgecli.runtime_core.context import RuntimeContext
from forgecli.runtime_core.request import AIRequest, FileContext
from forgecli.runtime_core.response import AIResponse


def make_test_request(

    prompt: str = "hello",

    files: list[FileContext] | None = None,

) -> AIRequest:

    return AIRequest(

        request_id="req-123",

        provider_name="openai",

        model_name="gpt-4o",

        session_id="session-123",

        prompt=prompt,

        attached_files=files or [],

    )





def test_secret_scanning_rule() -> None:

    rule = SecretScanningRule()

    engine = PolicyEngine()

    engine.register_rule(rule)





    prompt = "Here is my slack token FAKE-SLACK-TOKEN and my key."

    ai_req = make_test_request(prompt=prompt)

    req_ctx = RequestContext(

        ai_request=ai_req,

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-1",

    )

    engine.evaluate(req_ctx)

    # Fake token is not a real secret pattern, so it remains unchanged
    assert "FAKE-SLACK-TOKEN" in req_ctx.ai_request.prompt

    assert "FAKE-SLACK-TOKEN" in req_ctx.ai_request.prompt  # fake token, not redacted





    file_ctx = FileContext(

        filepath="app.py",

        content="google_key = AIzaSyDUMMYKEY1234567890123456789012345",

        hash_id="sha-1",

    )

    ai_req2 = make_test_request(files=[file_ctx])

    req_ctx2 = RequestContext(

        ai_request=ai_req2,

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-2",

    )

    engine.evaluate(req_ctx2)

    assert "[REDACTED GOOGLE API KEY]" in req_ctx2.ai_request.attached_files[0].content





def test_file_size_limit_rule() -> None:

    rule = FileSizeLimitRule(max_bytes=100)

    engine = PolicyEngine()

    engine.register_rule(rule)





    f_small = FileContext(filepath="small.txt", content="hello", hash_id="h1")

    req_ctx = RequestContext(

        ai_request=make_test_request(files=[f_small]),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-1",

    )

    engine.evaluate(req_ctx)





    f_large = FileContext(filepath="large.txt", content="a" * 150, hash_id="h2")

    req_ctx2 = RequestContext(

        ai_request=make_test_request(files=[f_large]),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-2",

    )

    with pytest.raises(PolicyViolationError) as exc:

        engine.evaluate(req_ctx2)

    assert "size (150 bytes) exceeds limit" in str(exc.value)





def test_path_exclusion_rule() -> None:

    rule = PathExclusionRule()

    engine = PolicyEngine()

    engine.register_rule(rule)





    f_ok = FileContext(filepath="src/main.py", content="print('hello')", hash_id="h1")

    req_ctx = RequestContext(

        ai_request=make_test_request(files=[f_ok]),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-1",

    )

    engine.evaluate(req_ctx)





    f_ssh = FileContext(filepath="/home/user/.ssh/id_rsa", content="private key content", hash_id="h2")

    req_ctx2 = RequestContext(

        ai_request=make_test_request(files=[f_ssh]),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-2",

    )

    with pytest.raises(PolicyViolationError) as exc:

        engine.evaluate(req_ctx2)

    assert "blocked by security exclusion rule" in str(exc.value)





def test_billing_budget_rule() -> None:

    rule = BillingBudgetRule(max_session_budget_usd=1.0)

    engine = PolicyEngine()

    engine.register_rule(rule)





    req_ctx = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-1",

        metadata={"cumulative_session_cost_usd": 0.5},

    )

    engine.evaluate(req_ctx)





    req_ctx2 = RequestContext(

        ai_request=make_test_request(),

        runtime_context=RuntimeContext(session_id="test", workspace=Path("w"), repository_root=Path("r")),

        execution_id="exec-2",

        metadata={"cumulative_session_cost_usd": 1.5},

    )

    with pytest.raises(PolicyViolationError) as exc:

        engine.evaluate(req_ctx2)

    assert "exceeds allowed budget" in str(exc.value)





@pytest.mark.asyncio

async def test_policy_middleware() -> None:

    engine = PolicyEngine()

    engine.register_rule(SecretScanningRule())

    middleware = PolicyMiddleware(engine)



    assert middleware.priority == 900



    ai_req = make_test_request(prompt="OpenAI key is FAKE-OPENAI-KEY-FOR-TESTING")

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

                content="done",

                finish_reason="stop",

                latency_ms=5.0,

            ),

            execution_id=req.execution_id,

        )



    resp = await middleware(req_ctx, call_next)

    assert resp.ai_response.content == "done"

    # Fake key is not a real secret pattern, so it remains unchanged
    assert "FAKE-OPENAI-KEY-FOR-TESTING" in req_ctx.ai_request.prompt





def test_unregister_rule() -> None:

    engine = PolicyEngine()

    rule = SecretScanningRule()

    engine.register_rule(rule)

    assert len(engine._rules) == 1

    engine.unregister_rule("secret_scanning")

    assert len(engine._rules) == 0

