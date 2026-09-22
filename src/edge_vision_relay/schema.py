"""Stable, versioned event contracts exchanged by devices and the relay."""

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"


class EventEnvelope(BaseModel):
    """A transport-safe observation; payload is intentionally domain-extensible."""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    event_id: UUID = Field(default_factory=uuid4)
    device_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    class Config:
        extra = "forbid"

    def normalized(self) -> "EventEnvelope":
        """Return an equivalent event with a timezone-aware UTC timestamp."""
        timestamp = self.captured_at
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return self.copy(update={"captured_at": timestamp.astimezone(timezone.utc)})
