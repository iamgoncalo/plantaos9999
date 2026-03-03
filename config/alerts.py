"""Alert data model."""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field


class Alert(BaseModel):
    """A building alert."""

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    zone_id: str = Field(description="Zone that triggered the alert")
    severity: str = Field(description="info, warning, or critical")
    message: str = Field(description="Human-readable alert message")
    timestamp: str = Field(description="ISO timestamp string")
    category: str = Field(
        default="comfort", description="comfort, energy, occupancy, safety"
    )
