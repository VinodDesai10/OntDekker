"""
Itinerary Pydantic schemas.

Covers request/response shapes for:
  GET  /api/v1/expeditions/{id}/itinerary        — list all days
  PUT  /api/v1/expeditions/{id}/itinerary        — replace full itinerary
  POST /api/v1/expeditions/{id}/itinerary        — add a single day
  PATCH /api/v1/expeditions/{id}/itinerary/{day} — update one day
  DELETE /api/v1/expeditions/{id}/itinerary/{day}— delete one day

The PUT (replace) endpoint accepts ItineraryBulkUpdate which contains
a list of ItineraryCreate objects. The service layer deletes all
existing days and inserts the new set in one transaction.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItineraryDayCreate(BaseModel):
    """A single itinerary day for creation or replacement.

    day_number is 1-indexed. The UniqueConstraint in the database
    prevents duplicate day numbers per expedition.
    """

    day_number: int = Field(
        ...,
        ge=1,
        le=365,
        description="Day number within the expedition (1-indexed, max 365).",
    )
    title: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Short title for this day (e.g., 'Rest Day at Namche Bazaar').",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=3000,
        description="Detailed activities for this day (max 3000 chars).",
    )
    location: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Primary location or camp name for this day.",
        examples=["Namche Bazaar (3,440 m)"],
    )
    activity_time: Optional[time] = Field(
        default=None,
        description="Planned start time for the main activity (HH:MM:SS local time).",
        examples=["06:00:00"],
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Additional organiser notes or instructions for this day.",
    )


class ItineraryDayUpdate(BaseModel):
    """Partial update for a single itinerary day.

    All fields are optional — only provided fields are updated.
    day_number cannot be changed via update (use delete + create instead).
    """

    title: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=200,
    )
    description: Optional[str] = Field(default=None, max_length=3000)
    location: Optional[str] = Field(default=None, max_length=300)
    activity_time: Optional[time] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=2000)


class ItineraryBulkUpdate(BaseModel):
    """Body for PUT /api/v1/expeditions/{id}/itinerary.

    Replaces the entire itinerary in one transaction.
    The service layer validates that day_numbers are unique within the list
    before performing the delete-and-reinsert operation.
    """

    days: List[ItineraryDayCreate] = Field(
        ...,
        min_length=1,
        max_length=365,
        description="Complete ordered list of itinerary days. Replaces all existing days.",
    )

    @field_validator("days")
    @classmethod
    def day_numbers_must_be_unique(
        cls, days: List[ItineraryDayCreate]
    ) -> List[ItineraryDayCreate]:
        numbers = [d.day_number for d in days]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Each day_number must be unique within the itinerary.")
        return days


class ItineraryDayResponse(BaseModel):
    """Full itinerary day record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    expedition_id: UUID
    day_number: int
    title: str
    description: Optional[str]
    location: Optional[str]
    activity_time: Optional[time]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class ItineraryResponse(BaseModel):
    """Full itinerary for an expedition — list of days ordered by day_number."""

    expedition_id: UUID = Field(
        ...,
        description="The expedition this itinerary belongs to.",
    )
    days: List[ItineraryDayResponse] = Field(
        default_factory=list,
        description="Itinerary days ordered ascending by day_number.",
    )
    total_days: int = Field(
        ...,
        ge=0,
        description="Total number of planned days.",
    )
