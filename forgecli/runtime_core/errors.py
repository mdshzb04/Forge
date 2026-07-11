"""Custom exceptions for the Forge runtime.

Provides structured error context to support diagnostics and telemetry.
"""



from __future__ import annotations

from typing import Any


class ForgeError(Exception):

    """Base exception class for all errors inside the Forge runtime.

    Includes a structured dictionary payload to carry context (e.g., error codes,
    failing filenames, network status flags) to the diagnostics or telemetry collectors.
    """



    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:

        """Initialize the exception with a message and structured context.

        Args:
            message: A human-readable description of the error.
            context: A dictionary of key-value diagnostics context.
        """

        super().__init__(message)

        self.message: str = message

        self.context: dict[str, Any] = context or {}



    def __str__(self) -> str:

        if self.context:

            return f"{self.message} (Context: {self.context})"

        return self.message





class ConfigurationError(ForgeError):

    """Raised when there is an error resolving or parsing application configuration."""





class SessionError(ForgeError):

    """Raised when there is an error loading, resolving, or tracking session state."""





class PipelineError(ForgeError):

    """Raised when request execution halts during the middleware pipeline."""





class ProviderError(ForgeError):

    """Raised when a downstream LLM provider client (e.g. Anthropic, OpenAI) fails."""





class PolicyViolationError(ForgeError):

    """Raised when the compliance or security policy engine blocks a request/response."""





class PluginError(ForgeError):

    """Raised when dynamic loader or runtime hooks fail inside third-party plugins."""

