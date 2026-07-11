"""Metadata configuration schema for the Forge Provider Runtime."""



from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderMetadata(BaseModel):

    """Represents configuration, supported models, and limits for a provider."""



    name: str

    version: str

    default_model: str

    supported_models: list[str] = Field(default_factory=list)

    context_windows: dict[str, int] = Field(default_factory=dict)

