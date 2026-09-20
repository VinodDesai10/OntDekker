"""
TravelConnection Pydantic schemas.

Covers response shapes for:
  GET /api/v1/guides/my-connections   — traveler's previously connected guides

TravelConnections are created/updated by the service layer in response to
Kafka events (EXPEDITION_COMPLETED) — there is no direct create endpoint.
The traveler can bookmark a connection via POST /guides/{id}/bookmark.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


# ---------------------------------------------------------------------------
# Response — single connection
# ---------------------------------------------------------------------------

class TravelConnectionResponse(BaseModel):
    """A guide–traveler connection record.

    Returned as part of the traveler's "My Guides" / previous connections view.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    guide_id: UUID
    traveler_id: UUID

    first_met: Optional[datetime]
    last_interaction: Optional[datetime]

    expeditions_together: int = Field(ge=0)
    conversation_count: int = Field(ge=0)
    photos_shared: int = Field(ge=0)

    bookmarked: bool

    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# List response
# ---------------------------------------------------------------------------

class TravelConnectionListResponse(BaseModel):
    """Paginated list of a traveler's guide connections."""

    traveler_id: UUID
    connections: List[TravelConnectionResponse] = Field(default_factory=list)
    pagination: PaginationMeta
