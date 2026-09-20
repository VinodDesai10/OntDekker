"""
Participant Pydantic schemas.

Covers responses for:
  GET  /api/v1/expeditions/{id}/participants
  GET  /api/v1/expeditions/{id}/participants/{user_id}

Participants are created implicitly (via join or join-request approval)
so there is no ParticipantCreate schema — the service layer handles
participant row creation internally.

ParticipantRemove is used for:
  DELETE /api/v1/expeditions/{id}/participants/{user_id}
  (organiser removing a participant)
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.participant import ParticipantRole, ParticipantStatus


class ParticipantResponse(BaseModel):
    """Full participant record.

    Returned when listing all participants for an expedition or
    viewing a single participant's details.
    The user's display name and avatar come from User Service —
    the frontend merges them client-side or via a BFF aggregation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    expedition_id: UUID
    user_id: UUID
    role: ParticipantRole
    status: ParticipantStatus
    joined_at: datetime
    created_at: datetime
    updated_at: datetime


class ParticipantRoleUpdate(BaseModel):
    """Request body for promoting/demoting a participant's role.

    Used by:
      PATCH /api/v1/expeditions/{id}/participants/{user_id}/role

    Only ORGANIZER or CO_ORGANIZER can perform this action.
    Changing role to ORGANIZER transfers ownership — service layer
    enforces that the current organiser loses ORGANIZER status.
    """

    role: ParticipantRole = Field(
        ...,
        description="New role to assign to the participant.",
    )
