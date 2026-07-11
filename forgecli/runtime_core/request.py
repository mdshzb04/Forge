"""Request models for the Universal AI Runtime.

Standardizes file system context payloads and remote model instructions.
"""



from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FileContext(BaseModel):

    """Encapsulates a file's location, content, and git status context."""



    model_config = ConfigDict(

        extra="allow",

        populate_by_name=True,

    )



    filepath: str = Field(

        ...,

        description="The absolute or relative path to the file on disk.",

    )

    content: str = Field(

        ...,

        description="The raw string content of the file.",

    )

    hash_id: str = Field(

        ...,

        description="A unique hash (e.g., git blob hash or SHA256) of the file content.",

    )

    is_modified: bool = Field(

        default=False,

        description="Indicates whether this file has local uncommitted modifications.",

    )





class AIRequest(BaseModel):

    """Pydantic model representing an execution request to the Forge runtime."""



    model_config = ConfigDict(

        extra="allow",

        populate_by_name=True,

    )



    request_id: str = Field(

        ...,

        description="A unique UUID or string identifier for the request tracing.",

    )

    prompt: str = Field(

        ...,

        description="The primary user input message or command instruction.",

    )

    system_instruction: str | None = Field(

        default=None,

        description="Global system level priming context or guidelines.",

    )

    messages: list[dict[str, str]] = Field(

        default_factory=list,

        description="Historical conversational context message lists.",

    )

    attached_files: list[FileContext] = Field(

        default_factory=list,

        description="List of files to inject into the request's context workspace.",

    )

    provider_name: str = Field(

        ...,

        description="The targeted provider name (e.g., 'anthropic', 'openai').",

    )

    model_name: str = Field(

        ...,

        description="The targeted model identifier (e.g., 'claude-3-5-sonnet').",

    )

    temperature: float = Field(

        default=0.2,

        ge=0.0,

        le=2.0,

        description="Controls model execution randomness.",

    )

    max_tokens: int | None = Field(

        default=None,

        gt=0,

        description="Token limit parameter, if configured.",

    )

    stream: bool = Field(

        default=True,

        description="Whether this request expects a streaming chunk response.",

    )

    session_id: str = Field(

        ...,

        description="The active workspace session or chat history tracking ID.",

    )

    metadata: dict[str, Any] = Field(

        default_factory=dict,

        description="Extensible metadata mapping for custom plugins or telemetry logs.",

    )

