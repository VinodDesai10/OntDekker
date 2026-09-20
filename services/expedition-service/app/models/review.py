"""
ExpeditionReview model.

Represents a post-expedition peer review written by one participant
about another participant (including the organiser).

Key constraints enforced here:
  - A review can only be submitted after the expedition status = COMPLETED.
    This is enforced in the service layer, not the database.
  - reviewer_id ≠ reviewee_id is enforced via a CheckConstraint — you
    cannot review yourself.
  - UniqueConstraint on (expedition_id, reviewer_id, reviewee_id) ensures
    each participant can write exactly one review per reviewee per expedition.

Review dimensions match the documentation:
  - Overall rating
  - Communication
  - Safety
  - Punctuality
  - Organisation
  - Friendliness
  - Would travel again (boolean)

All rating columns use SMALLINT (1–5) with CheckConstraints.
These ratings feed into the User Service reputation system (via Kafka
REVIEW_SUBMITTED event in Phase 2).

Database: trip_db
Table:    expedition_reviews
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
    UniqueConstraint,
    UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.expedition import Expedition


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class ExpeditionReview(Base, TimestampMixin):
    """A post-expedition peer review between two participants.

    TimestampMixin provides: created_at, updated_at

    Key design decisions:
    - reviewer_id  — UUID of the user writing the review (NOT a SQL FK).
    - reviewee_id  — UUID of the user being reviewed (NOT a SQL FK).
    - Both IDs are plain UUIDs referencing user_db.user_profiles. They have
      no SQL-level FK because we never query user_db directly.
    - All numeric ratings are SMALLINT (1–5) with individual CheckConstraints.
      SMALLINT is appropriate: values fit in 2 bytes; no arithmetic precision
      issues arise.
    - would_travel_again is a boolean, not a rating scale — keeps the UI
      clear ("Would you travel with this person again? Yes / No").
    - comment is optional free text. The UI may allow up to 1000 characters;
      that limit is enforced in the Pydantic schema, not the DB column.
    - A self-review CheckConstraint (reviewer_id != reviewee_id) is enforced
      at the database level as a safety net.
    - No soft delete: reviews are permanent once submitted (moderation
      actions go through Moderation Service, not here).
    """

    __tablename__ = "expedition_reviews"

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
    # Foreign key into trip_db (real SQL FK, same database)
    # ------------------------------------------------------------------
    expedition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expeditions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # External references — no SQL FKs to user_db
    # ------------------------------------------------------------------
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="UUID of the participant writing this review. NOT a SQL FK.",
    )
    reviewee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="UUID of the participant being reviewed. NOT a SQL FK.",
    )

    # ------------------------------------------------------------------
    # Numeric ratings (1–5, SMALLINT)
    # ------------------------------------------------------------------
    rating_overall: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="Overall experience rating (1–5).",
    )
    rating_communication: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="Communication quality rating (1–5).",
    )
    rating_safety: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="Safety-consciousness rating (1–5).",
    )
    rating_punctuality: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="Punctuality and reliability rating (1–5).",
    )
    rating_organisation: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="Organisation and planning rating (1–5).",
    )
    rating_friendliness: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="Friendliness and attitude rating (1–5).",
    )

    # ------------------------------------------------------------------
    # Boolean summary
    # ------------------------------------------------------------------
    would_travel_again: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Whether the reviewer would travel with this person again.",
    )

    # ------------------------------------------------------------------
    # Optional free text
    # ------------------------------------------------------------------
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional written review. Max length enforced in Pydantic schema (1000 chars).",
    )

    # ------------------------------------------------------------------
    # Relationship back to the expedition aggregate
    # ------------------------------------------------------------------
    expedition: Mapped["Expedition"] = relationship(
        "Expedition",
        back_populates="reviews",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # One review per reviewer per reviewee per expedition
        UniqueConstraint(
            "expedition_id", "reviewer_id", "reviewee_id",
            name="uq_review_expedition_reviewer_reviewee",
        ),
        # Prevent self-reviews at the database level
        CheckConstraint(
            "reviewer_id != reviewee_id",
            name="ck_review_no_self_review",
        ),
        # All rating columns must be within 1–5
        CheckConstraint(
            "rating_overall BETWEEN 1 AND 5",
            name="ck_review_rating_overall",
        ),
        CheckConstraint(
            "rating_communication BETWEEN 1 AND 5",
            name="ck_review_rating_communication",
        ),
        CheckConstraint(
            "rating_safety BETWEEN 1 AND 5",
            name="ck_review_rating_safety",
        ),
        CheckConstraint(
            "rating_punctuality BETWEEN 1 AND 5",
            name="ck_review_rating_punctuality",
        ),
        CheckConstraint(
            "rating_organisation BETWEEN 1 AND 5",
            name="ck_review_rating_organisation",
        ),
        CheckConstraint(
            "rating_friendliness BETWEEN 1 AND 5",
            name="ck_review_rating_friendliness",
        ),
        # Fetch all reviews for a given expedition
        Index("ix_reviews_expedition_id", "expedition_id"),
        # Fetch all reviews written by a user (their review history)
        Index("ix_reviews_reviewer_id", "reviewer_id"),
        # Fetch all reviews received by a user (their reputation data)
        Index("ix_reviews_reviewee_id", "reviewee_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExpeditionReview id={self.id} expedition={self.expedition_id} "
            f"reviewer={self.reviewer_id} reviewee={self.reviewee_id} "
            f"overall={self.rating_overall}>"
        )
