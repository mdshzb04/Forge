"""Response context container for the Forge middleware engine.

Aggregates AI response targets, token allocations, timing latencies, and metadata.
"""



from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from forgecli.runtime_core.response import AIResponse


class ResponseContext(BaseModel):

    """Pydantic model holding context outputs for a completed pipeline run."""



    model_config = ConfigDict(

        arbitrary_types_allowed=True,

        extra="allow",

        populate_by_name=True,

    )



    ai_response: AIResponse | None = Field(

        default=None,

        description="The resolved completion response payload from the driver.",

    )

    stream_iterator: Any | None = Field(

        default=None,

        description="An AsyncIterator yielding StreamEvent objects if streaming was requested.",

    )

    timing_ms: float = Field(

        default=0.0,

        ge=0.0,

        description="Execution time duration inside pipeline scopes.",

    )

    usage: dict[str, int] = Field(

        default_factory=dict,

        description="Completed token allocations and caching counts.",

    )

    provider_metadata: dict[str, Any] = Field(

        default_factory=dict,

        description="Downstream specific vendor options (e.g. stop reasons).",

    )

    errors: list[str] = Field(

        default_factory=list,

        description="Collection of non-fatal error strings during execution.",

    )

    streaming_metadata: dict[str, Any] = Field(

        default_factory=dict,

        description="State tracking parameters for token yield loops.",

    )

    telemetry: dict[str, Any] = Field(

        default_factory=dict,

        description="Trace identifiers or metrics passed to observability exporters.",

    )

