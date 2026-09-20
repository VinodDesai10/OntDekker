"""
ExpeditionDiscussionMessage model.

Represents a single message posted in an expedition's discussion thread.

Design rules (mirrors the participant identity convention):
  - expedition_id is a real SQL FK into expeditions.id (same database, trip_db).
  - author_id is a plain UUID (NOT a SQL FK) — it is the JWT `sub` claim,
    i.e., the auth-service account UUID.  Display name / avatar are resolved
    later by the frontend via the user-service batchProfilesByAuth() flow.
  - No soft-delete in this revision; messages are immutable for now.
  - TimestampMixin provides created_at / updated_at.

Database: trip_db
Table:    expedition_discussion_messages
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.expedition import Expedition


class ExpeditionDiscussionMessage(Base, TimestampMixin):
    """A single message in an expedition's discussion thread.

    TimestampMixin provides: created_at, updated_at

    Key design decisions:
    - No FK to user_db — referential integrity enforced at the application
      layer via JWT identity, matching the existing participant convention.
    - Content is TEXT (up to ~1 GiB at the DB level); the service layer
      enforces a 2000-character application limit.
    - CheckConstraint ensures content is never an empty/whitespace-only
      string at the database level (secondary guard behind app validation).
    - Index on (expedition_id, created_at) supports the primary read path:
      "fetch all messages for expedition X ordered by time".
    """

    __tablename__ = "expedition_discussion_messages"

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
    # Foreign key into trip_db (same database — real SQL FK)
    # ------------------------------------------------------------------
    expedition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expeditions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # External reference (UUID only, no SQL FK to auth_db / user_db)
    # ------------------------------------------------------------------
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment=(
            "UUID of the message author — the JWT 'sub' claim (auth-service UUID). "
            "NOT a SQL FK.  Display name resolved via user-service."
        ),
    )

    # ------------------------------------------------------------------
    # Message content
    # ------------------------------------------------------------------
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationship back to the expedition aggregate
    # ------------------------------------------------------------------
    expedition: Mapped["Expedition"] = relationship(
        "Expedition",
        back_populates="discussion_messages",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # Primary read path: all messages for an expedition ordered by time
        Index(
            "ix_expedition_discussion_expedition_created",
            "expedition_id",
            "created_at",
        ),
        # Secondary: all messages by a specific author (audit / moderation)
        Index("ix_expedition_discussion_author_id", "author_id"),
        # DB-level guard: content must not be blank
        CheckConstraint(
            "LENGTH(TRIM(content)) > 0",
            name="ck_expedition_discussion_content_not_empty",
        ),
    )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return (
            f"<ExpeditionDiscussionMessage id={self.id} "
            f"expedition={self.expedition_id} author={self.author_id} "
            f"content={preview!r}>"
        )
