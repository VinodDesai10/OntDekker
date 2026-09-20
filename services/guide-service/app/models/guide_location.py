"""
GuideLocation model.

Stores the geographic areas (country / region / city) covered by a guide.
A guide can cover multiple locations; each row is one coverage entry.

Database: guide_db
Table:    guide_locations
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.guide_profile import GuideProfile


class GuideLocation(Base, TimestampMixin):
    """One geographic coverage area for a guide.

    FK → guide_profiles.id with CASCADE delete.
    TimestampMixin provides: created_at, updated_at
    """

    __tablename__ = "guide_locations"

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
    # FK to guide_profiles (same database — real SQL FK)
    # ------------------------------------------------------------------
    guide_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guide_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Location fields (country is required; region/city are optional)
    # ------------------------------------------------------------------
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Country name (e.g. 'India', 'Japan').",
    )
    region: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="State / province / region (e.g. 'Himachal Pradesh').",
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="City or locality (e.g. 'Manali').",
    )

    # ------------------------------------------------------------------
    # Relationship back to parent
    # ------------------------------------------------------------------
    guide: Mapped["GuideProfile"] = relationship(
        "GuideProfile",
        back_populates="locations",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # A guide cannot have duplicate country+region+city combinations.
        UniqueConstraint(
            "guide_id", "country", "region", "city",
            name="uq_guide_location_guide_country_region_city",
        ),
        Index("ix_guide_locations_guide_id", "guide_id"),
        # Supports directory queries filtered by country
        Index("ix_guide_locations_country", "country"),
    )

    def __repr__(self) -> str:
        parts = [self.country]
        if self.region:
            parts.append(self.region)
        if self.city:
            parts.append(self.city)
        return f"<GuideLocation guide_id={self.guide_id} location={', '.join(parts)}>"
