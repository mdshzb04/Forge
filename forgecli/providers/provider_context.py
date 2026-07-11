"""Execution context schema for the Forge Provider Runtime."""



from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from forgecli.middleware.context import RequestContext, ResponseContext
from forgecli.providers.base import Provider
from forgecli.providers.provider_capabilities import ProviderCapabilities
from forgecli.runtime_core.context import CancellationToken


class ProviderContext(BaseModel):

    """Encapsulates context arguments required by a provider to process execution requests."""



    model_config = ConfigDict(arbitrary_types_allowed=True)



    provider: Provider

    model: str

    workspace: Path

    request_context: RequestContext

    response_context: ResponseContext | None = None

    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)

    configuration: dict[str, Any] = Field(default_factory=dict)

    telemetry: dict[str, Any] = Field(default_factory=dict)

    cancellation_token: CancellationToken | None = None

