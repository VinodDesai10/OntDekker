"""
GuideReview model.

Travelers submit reviews for guides after completing expeditions together.
reviewer_id and expedition_id are cross-service UUID references — no SQL FKs.

Database: guide_db
Table:    guide_reviews
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UUID,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.guide_profile import GuideProfile


class GuideReview(Base, TimestampMixin):
    """A traveler's review of a guide.

    Rating categories mirror the expedition review system for consistency:
    knowledge, friendliness, communication, safety, professionalism, overall.

    FK → guide_profiles.id with CASCADE delete.
    reviewer_id → User Service (no SQL FK — cross-service).
    expedition_id → Expedition Service (no SQL FK — cross-service).

    TimestampMixin provides: created_at, updated_at
    """

    __tablename__ = "guide_reviews"

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
    # External service references (no SQL FKs)
    # ------------------------------------------------------------------
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="UUID reference to user_db.user_profiles. NOT a SQL FK.",
    )
    expedition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID reference to trip_db.expeditions. NOT a SQL FK. Nullable for direct connections.",
    )

    # ------------------------------------------------------------------
    # Rating dimensions (SMALLINT, 1–5 each)
    # ------------------------------------------------------------------
    rating_overall: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rating_knowledge: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rating_friendliness: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rating_communication: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rating_safety: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rating_professionalism: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # ------------------------------------------------------------------
    # Qualitative feedback
    # ------------------------------------------------------------------
    would_recommend: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Would the traveler recommend this guide to others?",
    )
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text review body.",
    )

    # ------------------------------------------------------------------
    # Relationship back to parent
    # ------------------------------------------------------------------
    guide: Mapped["GuideProfile"] = relationship(
        "GuideProfile",
        back_populates="reviews",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # One review per reviewer per guide (a traveler can only review a guide once).
        UniqueConstraint(
            "guide_id", "reviewer_id",
            name="uq_guide_review_guide_reviewer",
        ),
        # Self-review prevention
        CheckConstraint(
            "guide_id != reviewer_id",
            name="ck_guide_review_no_self_review",
        ),
        # Rating range checks
        CheckConstraint("rating_overall        BETWEEN 1 AND 5", name="ck_guide_review_overall"),
        CheckConstraint("rating_knowledge      BETWEEN 1 AND 5", name="ck_guide_review_knowledge"),
        CheckConstraint("rating_friendliness   BETWEEN 1 AND 5", name="ck_guide_review_friendliness"),
        CheckConstraint("rating_communication  BETWEEN 1 AND 5", name="ck_guide_review_communication"),
        CheckConstraint("rating_safety         BETWEEN 1 AND 5", name="ck_guide_review_safety"),
        CheckConstraint("rating_professionalism BETWEEN 1 AND 5", name="ck_guide_review_professionalism"),
        # Indexes
        Index("ix_guide_reviews_guide_id", "guide_id"),
        Index("ix_guide_reviews_reviewer_id", "reviewer_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<GuideReview id={self.id} guide_id={self.guide_id} "
            f"reviewer_id={self.reviewer_id} overall={self.rating_overall}>"
        )
