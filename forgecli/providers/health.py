"""Health monitoring schemas for the Forge Provider Runtime."""



from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ProviderHealthState(StrEnum):

    """Execution health states for client drivers."""



    HEALTHY = "healthy"

    DEGRADED = "degraded"

    UNAVAILABLE = "unavailable"

    MAINTENANCE = "maintenance"

    UNKNOWN = "unknown"





class ProviderHealth(BaseModel):

    """Represents current health diagnostics for a provider."""



    state: ProviderHealthState = ProviderHealthState.UNKNOWN

    last_checked: datetime = Field(default_factory=datetime.utcnow)

    details: str | None = None

