"""
Join Request Pydantic schemas.

Covers request/response shapes for:
  POST /api/v1/expeditions/{id}/join      — submit request
  POST /api/v1/expeditions/{id}/approve   — organiser approves
  POST /api/v1/expeditions/{id}/reject    — organiser rejects
  DELETE /api/v1/expeditions/{id}/join    — requester cancels

For PUBLIC expeditions, the service layer bypasses join requests
and creates a participant row directly — no JoinRequest row is
created. These schemas apply only to PRIVATE expeditions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.join_request import JoinRequestStatus


class JoinRequestCreate(BaseModel):
    """Body for POST /api/v1/expeditions/{id}/join.

    The user_id is resolved server-side from the JWT — it is NOT
    accepted from the client to prevent impersonation.
    The message is optional: applicants may introduce themselves.
    """

    message: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional introductory message to the organiser (max 1000 chars).",
        examples=["Hi! I've done Everest base camp twice and have UIAGM experience."],
    )


class JoinRequestDecision(BaseModel):
    """Body for approve/reject endpoints.

    Used by:
      POST /api/v1/expeditions/{id}/approve  — body: { user_id }
      POST /api/v1/expeditions/{id}/reject   — body: { user_id, rejection_reason }

    The user_id here identifies the applicant whose request is being acted on.
    The reviewer identity is resolved server-side from the organiser's JWT.
    """

    user_id: UUID = Field(
        ...,
        description="UUID of the applicant whose join request is being approved or rejected.",
    )
    rejection_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional reason for rejection. Only meaningful when rejecting.",
    )


class JoinRequestResponse(BaseModel):
    """Full join request record returned to both the applicant and organiser."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    expedition_id: UUID
    user_id: UUID
    message: Optional[str]
    status: JoinRequestStatus
    reviewed_by: Optional[UUID]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
