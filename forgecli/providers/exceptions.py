"""Exceptions module for the Forge Provider Runtime.

Standardizes error profiles during provider registration, initialization, and dispatch.
"""



from __future__ import annotations

from forgecli.runtime_core.errors import ForgeError


class ProviderError(ForgeError):

    """Base exception for all provider runtime errors."""



    pass





class ProviderNotFoundError(ProviderError):

    """Raised when a requested provider is not registered or cannot be resolved."""



    pass





class ProviderInitializationError(ProviderError):

    """Raised when a provider fails to initialize."""



    pass





class ProviderRegistrationError(ProviderError):

    """Raised when a duplicate provider registration occurs or is invalid."""



    pass





class ProviderExecutionError(ProviderError):

    """Raised when request execution on the provider fails."""



    pass

