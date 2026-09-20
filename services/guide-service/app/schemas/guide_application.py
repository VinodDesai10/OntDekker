"""
GuideApplication Pydantic schemas.

Covers request/response shapes for:
  POST /api/v1/guides/apply       — submit application (GuideApplicationCreate)
  GET  /api/v1/guides/apply       — view own application (GuideApplicationResponse)

The user_id is never in any request body — always resolved from JWT.
reviewed_by, reviewed_at, review_notes are admin-only fields populated
  by the admin review workflow, not by applicant submissions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.guide_application import ApplicationStatus


# ---------------------------------------------------------------------------
# Create — POST /api/v1/guides/apply
# ---------------------------------------------------------------------------

class GuideApplicationCreate(BaseModel):
    """Request body for submitting a guide application.

    biography is required — the primary review material.
    All other fields are optional at submission time but encouraged.

    identity_document_url: the client uploads the document to MinIO first
    and submits the resulting object URL. Binary never sent to this service.
    """

    biography: str = Field(
        ...,
        min_length=100,
        max_length=3000,
        description="Guide biography and motivation (100–3000 characters).",
    )
    areas_covered: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Description of geographic areas covered.",
    )
    languages: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Comma-separated list of spoken languages.",
        examples=["English, Hindi, Japanese"],
    )
    experience_years: Optional[int] = Field(
        default=None,
        ge=0,
        le=80,
        description="Self-reported years of guiding experience.",
    )
    certifications: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional certifications or qualifications.",
    )
    identity_document_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="MinIO private object URL for identity document (KYC). "
                    "Upload to MinIO first, then submit the URL here.",
    )


# ---------------------------------------------------------------------------
# Update — PATCH /api/v1/guides/apply  (draft edits before submission)
# ---------------------------------------------------------------------------

class GuideApplicationUpdate(BaseModel):
    """Request body for updating a DRAFT application before submission.

    All fields optional. Only allowed while status is DRAFT.
    """

    biography: Optional[str] = Field(
        default=None,
        min_length=100,
        max_length=3000,
    )
    areas_covered: Optional[str] = Field(default=None, max_length=1000)
    languages: Optional[str] = Field(default=None, max_length=500)
    experience_years: Optional[int] = Field(default=None, ge=0, le=80)
    certifications: Optional[str] = Field(default=None, max_length=1000)
    identity_document_url: Optional[str] = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Response — all application endpoints
# ---------------------------------------------------------------------------

class GuideApplicationResponse(BaseModel):
    """Full guide application record.

    Returned to the applicant and to admins.
    review_notes and reviewed_by are visible to admins; the service layer
    may strip sensitive fields for applicant-facing responses.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID

    biography: Optional[str]
    areas_covered: Optional[str]
    languages: Optional[str]
    experience_years: Optional[int]
    certifications: Optional[str]
    identity_document_url: Optional[str]

    status: ApplicationStatus

    submitted_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[UUID]
    review_notes: Optional[str]

    created_at: datetime
    updated_at: datetime
