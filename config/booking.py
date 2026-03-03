"""Booking data model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Booking(BaseModel):
    """A room booking record."""

    id: str = Field(description="Unique booking identifier")
    zone_id: str = Field(description="Booked zone ID")
    date: str = Field(description="ISO date string (YYYY-MM-DD)")
    start_hour: int = Field(ge=0, le=23, description="Start hour (0-23)")
    duration_hours: int = Field(ge=1, le=8, default=1, description="Duration in hours")
    people_count: int = Field(ge=1, default=10, description="Expected attendees")
    title: str = Field(default="", description="Booking title")
    created_by: str = Field(default="anonymous", description="Creator username")
    status: str = Field(default="confirmed", description="confirmed or cancelled")
