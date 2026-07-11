"""Request context container for the Forge middleware engine.

Aggregates AI prompt details, system environments, and tracking identifiers.
"""



from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from forgecli.runtime_core.context import CancellationToken, RuntimeContext
from forgecli.runtime_core.request import AIRequest


class RequestContext(BaseModel):

    """Pydantic model holding context inputs for a single pipeline execution pass."""



    model_config = ConfigDict(

        arbitrary_types_allowed=True,

        extra="allow",

        populate_by_name=True,

    )



    ai_request: AIRequest = Field(

        ...,

        description="The original AI model query request payload.",

    )

    runtime_context: RuntimeContext = Field(

        ...,

        description="The thread-safe active runtime context state wrapper.",

    )

    provider: str | None = Field(

        default=None,

        description="The target provider driver identifier.",

    )

    model: str | None = Field(

        default=None,

        description="The target provider model name.",

    )

    repository: str | None = Field(

        default=None,

        description="Path or alias of the target workspace codebase repository.",

    )

    conversation: list[dict[str, str]] = Field(

        default_factory=list,

        description="List of structured historical chat logs.",

    )

    metadata: dict[str, Any] = Field(

        default_factory=dict,

        description="Extensible request-scoped metadata for intermediate states.",

    )

    cancellation_token: CancellationToken | None = Field(

        default=None,

        description="Token signaling context execution cancel status.",

    )

    execution_id: str = Field(

        ...,

        description="Unique tracing UUID for the request pass.",

    )

    tracing_ids: dict[str, str] = Field(

        default_factory=dict,

        description="Collection of external correlations or pipeline hop tags.",

    )

