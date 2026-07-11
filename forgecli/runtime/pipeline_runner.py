"""Pipeline Runner — assembles and executes the full Forge middleware pipeline.

Provides the canonical 19-stage execution chain:
  Telemetry → Auth → Policy → Cache → History → Token → Context →
  Conversation → Caveman → Ponytail → Repository → DepGraph →
  SymbolLookup → Graphify → SemanticRetrieval → Streaming →
  Resilience → Provider → ResponseOptimizer
"""



from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:

    from forgecli.middleware.pipeline import MiddlewarePipeline
    from forgecli.runtime_core.request import AIRequest
    from forgecli.runtime_core.response import AIResponse





def build_default_pipeline(

    repo_root: Path | None = None,

    ponytail_intensity: str = "lite",

    caveman_intensity: str = "lite",

) -> MiddlewarePipeline:

    """Build the full production middleware pipeline.

    Returns a MiddlewarePipeline with all 19 stages wired in priority order.
    Each middleware delegates to its real implementation or passes through
    gracefully when dependencies are unavailable.
    """

    from forgecli.middleware.builder import PipelineBuilder
    from forgecli.middleware.caveman_adapter import CavemanAdapterMiddleware
    from forgecli.middleware.defaults import (
        AuthenticationMiddleware,
        CachingMiddleware,
        ContextOptimizerMiddleware,
        ConversationMiddleware,
        DependencyGraphMiddleware,
        GraphifyMiddleware,
        HistoryCompressorMiddleware,
        PolicyMiddleware,
        ProviderMiddleware,
        RepositoryPlannerMiddleware,
        ResponseOptimizerMiddleware,
        SemanticRetrievalMiddleware,
        StreamingMiddleware,
        SymbolLookupMiddleware,
        TelemetryMiddleware,
        TokenPlannerMiddleware,
    )
    from forgecli.middleware.ponytail_adapter import PonytailAdapterMiddleware
    from forgecli.resilience.middleware import ResilienceMiddleware



    builder = PipelineBuilder()





    builder.add(TelemetryMiddleware())

    builder.add(AuthenticationMiddleware())

    builder.add(PolicyMiddleware())

    builder.add(CachingMiddleware())

    builder.add(HistoryCompressorMiddleware())

    builder.add(TokenPlannerMiddleware())

    builder.add(ContextOptimizerMiddleware())

    builder.add(ConversationMiddleware())



    builder.add(CavemanAdapterMiddleware(intensity=caveman_intensity))

    builder.add(PonytailAdapterMiddleware(intensity=ponytail_intensity))



    builder.add(RepositoryPlannerMiddleware())

    builder.add(DependencyGraphMiddleware())

    builder.add(SymbolLookupMiddleware())



    builder.add(GraphifyMiddleware())

    builder.add(SemanticRetrievalMiddleware())



    builder.add(StreamingMiddleware())

    builder.add(ResilienceMiddleware())

    builder.add(ProviderMiddleware())

    builder.add(ResponseOptimizerMiddleware())



    return builder.build()





async def run_pipeline_async(

    request: AIRequest,

    repo_root: Path,

    session_id: str = "default",

    provider: str = "openai",

    model: str = "gpt-4o-mini",

    ponytail_intensity: str = "lite",

    caveman_intensity: str = "lite",

    metadata: dict[str, Any] | None = None,

) -> AIResponse:

    """Execute the full pipeline asynchronously and return the final AIResponse.

    Args:
        request: The AIRequest to process.
        repo_root: Git repository root path.
        session_id: Session identifier for conversation persistence.
        provider: Target provider name.
        model: Target model name.
        ponytail_intensity: Ponytail optimization level.
        caveman_intensity: Caveman optimization level.
        metadata: Optional extra metadata to attach to the request context.

    Returns:
        The final AIResponse after all pipeline stages.
    """

    import uuid

    from forgecli.middleware.context import RequestContext
    from forgecli.runtime_core.context import RuntimeContext



    pipeline = build_default_pipeline(

        repo_root=repo_root,

        ponytail_intensity=ponytail_intensity,

        caveman_intensity=caveman_intensity,

    )



    execution_id = uuid.uuid4().hex[:12]

    runtime_ctx = RuntimeContext(

        session_id=session_id,

        workspace=repo_root,

        repository_root=repo_root,

        current_provider=provider,

        current_model=model,

    )



    req_ctx = RequestContext(

        ai_request=request,

        runtime_context=runtime_ctx,

        provider=provider,

        model=model,

        execution_id=execution_id,

        tracing_ids={"trace_id": execution_id},

        metadata=dict(metadata or {}),

        conversation=[],

    )



    response_ctx = await pipeline.execute_async(req_ctx)



    if response_ctx.ai_response:

        return response_ctx.ai_response



    from forgecli.runtime_core.response import AIResponse

    return AIResponse(

        response_id=f"resp-{execution_id}",

        request_id=request.request_id,

        content="",

        finish_reason="error",

        latency_ms=0.0,

    )





def run_pipeline_sync(

    request: AIRequest,

    repo_root: Path,

    session_id: str = "default",

    provider: str = "openai",

    model: str = "gpt-4o-mini",

    ponytail_intensity: str = "lite",

    caveman_intensity: str = "lite",

    metadata: dict[str, Any] | None = None,

) -> AIResponse:

    """Synchronous wrapper around run_pipeline_async.

    Use this for CLI invocations or non-async contexts.
    """

    import asyncio



    return asyncio.run(

        run_pipeline_async(

            request=request,

            repo_root=repo_root,

            session_id=session_id,

            provider=provider,

            model=model,

            ponytail_intensity=ponytail_intensity,

            caveman_intensity=caveman_intensity,

            metadata=metadata,

        )

    )

