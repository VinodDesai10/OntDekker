"""
GuideProfile model — the root aggregate of the Guide Service.

Every guide profile is linked to a registered user in the Auth/User Service.
user_id is a plain UUID — NOT a SQL foreign key — cross-service boundary rule.

Database: guide_db
Table:    guide_profiles
"""

import uuid
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UUID,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared import Base, AuditMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.guide_location import GuideLocation
    from app.models.guide_language import GuideLanguage
    from app.models.guide_availability import GuideAvailability
    from app.models.guide_review import GuideReview
    from app.models.travel_connection import TravelConnection
    from app.models.guide_specialization import GuideSpecialization


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VerificationStatus(str, PyEnum):
    """Verification state of a guide profile.

    PENDING     — application approved, awaiting identity/location verification.
    VERIFIED    — fully verified guide; Verified Guide Badge is active.
    SUSPENDED   — verified but currently suspended by moderation.
    REVOKED     — verification permanently revoked.
    """
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class GuideProfile(Base, AuditMixin, SoftDeleteMixin):
    """Root aggregate for a verified guide.

    Created automatically when a GuideApplication is approved.
    AuditMixin provides: created_at, updated_at, created_by, updated_by
    SoftDeleteMixin provides: is_deleted, deleted_at, deleted_by
    """

    __tablename__ = "guide_profiles"

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
    # External service reference (UUID only, no SQL FK to user_db)
    # ------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        comment="UUID reference to user_db.user_profiles. NOT a SQL FK.",
    )

    # ------------------------------------------------------------------
    # Profile content
    # ------------------------------------------------------------------
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Guide biography shown on public profile.",
    )
    profile_image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="MinIO object URL for profile photo.",
    )
    cover_image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="MinIO object URL for cover image.",
    )
    years_experience: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Self-reported years of guiding experience.",
    )

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------
    price_per_day: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Guide's daily rate in USD. Nullable until set by guide.",
    )

    # ------------------------------------------------------------------
    # Aggregate stats (denormalised for read performance)
    # ------------------------------------------------------------------
    rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="Rolling average rating (1.00–5.00). Recomputed after each review.",
    )
    review_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of reviews received.",
    )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, name="verification_status_enum", create_type=True),
        nullable=False,
        default=VerificationStatus.PENDING,
        comment="Current verification state.",
    )

    # ------------------------------------------------------------------
    # Relationships (children; all cascade on guide profile hard-delete)
    # ------------------------------------------------------------------
    locations: Mapped[List["GuideLocation"]] = relationship(
        "GuideLocation",
        back_populates="guide",
        cascade="all, delete-orphan",
        lazy="select",
    )
    languages: Mapped[List["GuideLanguage"]] = relationship(
        "GuideLanguage",
        back_populates="guide",
        cascade="all, delete-orphan",
        lazy="select",
    )
    availability: Mapped[Optional["GuideAvailability"]] = relationship(
        "GuideAvailability",
        back_populates="guide",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="select",
    )
    reviews: Mapped[List["GuideReview"]] = relationship(
        "GuideReview",
        back_populates="guide",
        cascade="all, delete-orphan",
        lazy="select",
    )
    travel_connections: Mapped[List["TravelConnection"]] = relationship(
        "TravelConnection",
        back_populates="guide",
        cascade="all, delete-orphan",
        lazy="select",
    )
    specializations: Mapped[List["GuideSpecialization"]] = relationship(
        "GuideSpecialization",
        back_populates="guide",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        CheckConstraint(
            "years_experience IS NULL OR years_experience >= 0",
            name="ck_guide_profile_years_experience_non_negative",
        ),
        CheckConstraint(
            "price_per_day IS NULL OR price_per_day >= 0",
            name="ck_guide_profile_price_non_negative",
        ),
        CheckConstraint(
            "rating IS NULL OR (rating >= 1.00 AND rating <= 5.00)",
            name="ck_guide_profile_rating_range",
        ),
        CheckConstraint(
            "review_count >= 0",
            name="ck_guide_profile_review_count_non_negative",
        ),
        # user_id already has unique=True above; explicit index for FK-style lookups
        Index("ix_guide_profiles_user_id", "user_id"),
        Index("ix_guide_profiles_verification_status", "verification_status"),
        Index("ix_guide_profiles_is_deleted", "is_deleted"),
    )

    def __repr__(self) -> str:
        return (
            f"<GuideProfile id={self.id} user_id={self.user_id} "
            f"status={self.verification_status}>"
        )
