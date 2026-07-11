"""Capability schema definitions for the Forge Provider Runtime.

Allows providers and models to declare features dynamically using non-hardcoded capabilities maps.
"""



from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Capability(StrEnum):

    """Enumeration of all supported model and provider features."""



    TOOL_CALLING = "tool_calling"

    VISION = "vision"

    REASONING = "reasoning"

    STREAMING = "streaming"

    JSON_MODE = "json_mode"

    EMBEDDINGS = "embeddings"

    COMPUTER_USE = "computer_use"

    AUDIO = "audio"

    VIDEO = "video"

    LONG_CONTEXT = "long_context"

    STRUCTURED_OUTPUTS = "structured_outputs"

    BATCH = "batch"

    PROMPT_CACHING = "prompt_caching"

    CONTEXT_CACHING = "context_caching"





class ProviderCapabilities(BaseModel):

    """Encapsulates the capabilities map supported by a provider or model."""



    supported_capabilities: set[Capability] = Field(default_factory=set)



    def supports(self, capability: Capability) -> bool:

        """Check if the capability is supported.

        Args:
            capability: The capability to query.
        """

        return capability in self.supported_capabilities



    def add(self, capability: Capability) -> None:

        """Add a supported capability.

        Args:
            capability: The capability to enable.
        """

        self.supported_capabilities.add(capability)



    def remove(self, capability: Capability) -> None:

        """Remove a supported capability.

        Args:
            capability: The capability to disable.
        """

        self.supported_capabilities.discard(capability)

