"""Event schemas for the Forge Provider Runtime."""



from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from forgecli.providers.health import ProviderHealthState
from forgecli.runtime_core.events import SystemEvent


@dataclass

class ProviderEvent(SystemEvent):

    """Base class for all provider-related events."""



    provider_name: str





@dataclass

class ProviderRegistered(ProviderEvent):

    """Fired when a provider is successfully registered in the manager."""



    metadata: Any





@dataclass

class ProviderStarted(ProviderEvent):

    """Fired when a provider completes dynamic initialization."""



    pass





@dataclass

class ProviderStopped(ProviderEvent):

    """Fired when a provider completes shutdown operations."""



    pass





@dataclass

class ProviderHealthChanged(ProviderEvent):

    """Fired when a provider's checked health state changes."""



    old_state: ProviderHealthState

    new_state: ProviderHealthState

    details: str | None = None





@dataclass

class ProviderSelected(ProviderEvent):

    """Fired when a provider is resolved and chosen to execute a request."""



    model_name: str

    execution_id: str





@dataclass

class ProviderFailed(ProviderEvent):

    """Fired when a request fails to execute on the selected provider."""



    error_message: str

    execution_id: str





@dataclass

class ProviderRecovered(ProviderEvent):

    """Fired when a provider recovers after a previous failure."""



    execution_id: str

