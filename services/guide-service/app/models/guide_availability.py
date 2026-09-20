"""
GuideAvailability model.

One-to-one with GuideProfile. Stores the guide's current availability status
and an optional availability note (e.g. "Back in October").

Database: guide_db
Table:    guide_availability
"""

import uuid
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    UUID,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.guide_profile import GuideProfile


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AvailabilityStatus(str, PyEnum):
    """Current availability state of a guide.

    AVAILABLE   — actively accepting connections from travelers.
    UNAVAILABLE — not currently available (e.g. off-season).
    VACATION    — guide is on personal travel.
    BUSY        — booked up for the near future.
    """
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    VACATION = "VACATION"
    BUSY = "BUSY"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class GuideAvailability(Base, TimestampMixin):
    """Current availability status for a guide (one-to-one with GuideProfile).

    FK → guide_profiles.id with CASCADE delete.
    TimestampMixin provides: created_at, updated_at
    """

    __tablename__ = "guide_availability"

    # ------------------------------------------------------------------
    # Primary key — matches guide_profiles.id (shared PK / one-to-one)
    # ------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # FK to guide_profiles (same database — real SQL FK, unique=one-to-one)
    # ------------------------------------------------------------------
    guide_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guide_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="One-to-one link to guide_profiles.",
    )

    # ------------------------------------------------------------------
    # Availability data
    # ------------------------------------------------------------------
    status: Mapped[AvailabilityStatus] = mapped_column(
        SAEnum(AvailabilityStatus, name="availability_status_enum", create_type=True),
        nullable=False,
        default=AvailabilityStatus.AVAILABLE,
    )
    note: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="Optional message shown to travelers (e.g. 'Back in October').",
    )

    # ------------------------------------------------------------------
    # Relationship back to parent
    # ------------------------------------------------------------------
    guide: Mapped["GuideProfile"] = relationship(
        "GuideProfile",
        back_populates="availability",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        Index("ix_guide_availability_guide_id", "guide_id"),
        Index("ix_guide_availability_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<GuideAvailability guide_id={self.guide_id} status={self.status}>"
        )
