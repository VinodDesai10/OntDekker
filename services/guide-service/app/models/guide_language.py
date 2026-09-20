"""
GuideLanguage model.

Stores the languages spoken by a guide.
A guide can speak multiple languages; each row is one language entry.

Database: guide_db
Table:    guide_languages
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


class GuideLanguage(Base, TimestampMixin):
    """One language entry for a guide.

    FK → guide_profiles.id with CASCADE delete.
    TimestampMixin provides: created_at, updated_at
    """

    __tablename__ = "guide_languages"

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
    # Language
    # ------------------------------------------------------------------
    language: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        comment="Language name in English (e.g. 'Hindi', 'Japanese', 'French').",
    )

    # ------------------------------------------------------------------
    # Relationship back to parent
    # ------------------------------------------------------------------
    guide: Mapped["GuideProfile"] = relationship(
        "GuideProfile",
        back_populates="languages",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # A guide cannot list the same language twice.
        UniqueConstraint(
            "guide_id", "language",
            name="uq_guide_language_guide_language",
        ),
        Index("ix_guide_languages_guide_id", "guide_id"),
        # Supports directory queries filtered by language
        Index("ix_guide_languages_language", "language"),
    )

    def __repr__(self) -> str:
        return f"<GuideLanguage guide_id={self.guide_id} language={self.language!r}>"
