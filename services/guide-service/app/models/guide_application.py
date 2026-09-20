"""
GuideApplication model.

Any registered user can submit a guide application.
The application moves through a review workflow before a GuideProfile is created.

KYC document URLs reference MinIO private objects — pre-signed URLs are
generated at request time; only the object key/URL is stored here.

Database: guide_db
Table:    guide_applications
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    UUID,
    UniqueConstraint,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from shared import Base, TimestampMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ApplicationStatus(str, PyEnum):
    """State machine for a guide application.

    DRAFT         — saved by applicant, not yet submitted.
    SUBMITTED     — submitted and awaiting admin review.
    UNDER_REVIEW  — assigned to an admin reviewer.
    APPROVED      — application accepted; GuideProfile created.
    REJECTED      — application declined with optional review_notes.
    """
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class GuideApplication(Base, TimestampMixin):
    """A guide application submitted by a registered user.

    One user may only have one non-rejected application at a time.
    The UniqueConstraint enforces this at the database level.

    TimestampMixin provides: created_at, updated_at
    """

    __tablename__ = "guide_applications"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # External service reference (no SQL FK to user_db)
    # ------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="UUID reference to user_db.user_profiles. NOT a SQL FK.",
    )

    # ------------------------------------------------------------------
    # Application content
    # ------------------------------------------------------------------
    biography: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Applicant's guiding biography / motivation.",
    )
    areas_covered: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text description of regions/cities the applicant covers.",
    )
    languages: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated list of languages (stored as text; normalised on approval).",
    )
    experience_years: Mapped[Optional[int]] = mapped_column(
        # reuse Integer directly
        nullable=True,
        comment="Self-reported years of guiding experience.",
    )
    certifications: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional certifications or qualifications.",
    )

    # ------------------------------------------------------------------
    # KYC / identity document (MinIO private object URL)
    # ------------------------------------------------------------------
    identity_document_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="MinIO private object URL for identity document. Pre-signed at access time.",
    )

    # ------------------------------------------------------------------
    # Status and review metadata
    # ------------------------------------------------------------------
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus, name="application_status_enum", create_type=True),
        nullable=False,
        default=ApplicationStatus.DRAFT,
    )

    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when application was formally submitted.",
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when admin completed review.",
    )

    # External reference — reviewer is an admin user in user_db/auth_db
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID reference to admin user who reviewed. NOT a SQL FK.",
    )
    review_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal admin notes; also used for rejection reason.",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # Only one active (non-rejected) application per user.
        # Allows re-application after rejection by not including REJECTED status
        # in the unique constraint — enforced at the service layer.
        UniqueConstraint(
            "user_id",
            name="uq_guide_application_user",
        ),
        Index("ix_guide_applications_user_id", "user_id"),
        Index("ix_guide_applications_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<GuideApplication id={self.id} user_id={self.user_id} "
            f"status={self.status}>"
        )
