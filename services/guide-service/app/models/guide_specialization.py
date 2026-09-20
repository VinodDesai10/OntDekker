"""
GuideSpecialization model.

Stores the specialization categories for a guide
(e.g. "alpine", "sea kayaking", "cultural heritage").
A guide can have multiple specializations; each row is one category entry.

Database: guide_db
Table:    guide_specializations
"""

import uuid
from typing import TYPE_CHECKING

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


class GuideSpecialization(Base, TimestampMixin):
    """One specialization category for a guide.

    FK → guide_profiles.id with CASCADE delete.
    TimestampMixin provides: created_at, updated_at
    """

    __tablename__ = "guide_specializations"

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
    # Specialization category (free-form tag, e.g. "alpine", "trekking")
    # ------------------------------------------------------------------
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Specialization category tag (e.g. 'alpine', 'sea kayaking').",
    )

    # ------------------------------------------------------------------
    # Relationship back to parent
    # ------------------------------------------------------------------
    guide: Mapped["GuideProfile"] = relationship(
        "GuideProfile",
        back_populates="specializations",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # A guide cannot have duplicate category entries.
        UniqueConstraint(
            "guide_id", "category",
            name="uq_guide_specialization_guide_category",
        ),
        Index("ix_guide_specializations_guide_id", "guide_id"),
        Index("ix_guide_specializations_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<GuideSpecialization guide_id={self.guide_id} category={self.category!r}>"
