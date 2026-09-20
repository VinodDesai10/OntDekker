"""
ExpeditionParticipant model.

Represents a confirmed member of an expedition.
This is separate from join requests — a participant is already approved.

The user_id is a UUID reference to User Service (user_db). It is NOT a
SQL-level foreign key because we do not access user_db directly.

Database: trip_db
Table:    expedition_participants
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    UUID,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.expedition import Expedition


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ParticipantRole(str, PyEnum):
    """Role of a participant within the expedition.

    ORGANIZER     — the user who created the expedition; has full control.
    CO_ORGANIZER  — granted organiser-level permissions by the organiser.
    PARTICIPANT   — standard member.
    """
    ORGANIZER = "ORGANIZER"
    CO_ORGANIZER = "CO_ORGANIZER"
    PARTICIPANT = "PARTICIPANT"


class ParticipantStatus(str, PyEnum):
    """Participation status.

    ACTIVE  — currently participating.
    LEFT    — voluntarily left the expedition.
    REMOVED — removed by the organiser.
    """
    ACTIVE = "ACTIVE"
    LEFT = "LEFT"
    REMOVED = "REMOVED"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class ExpeditionParticipant(Base, TimestampMixin):
    """Confirmed participant in an expedition.

    TimestampMixin provides: created_at, updated_at

    Key design decisions:
    - UniqueConstraint on (expedition_id, user_id) prevents duplicate
      participation rows.
    - joined_at records the exact moment participation was confirmed
      (when a join request was approved or when an organiser was auto-added).
    - user_id has NO SQL FK to user_db — referential integrity is enforced
      at the application layer via JWT identity.
    """

    __tablename__ = "expedition_participants"

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
    # External reference (UUID only, no SQL FK to user_db)
    # ------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="UUID reference to user_db.user_profiles. NOT a SQL FK.",
    )

    # ------------------------------------------------------------------
    # Participant metadata
    # ------------------------------------------------------------------
    role: Mapped[ParticipantRole] = mapped_column(
        SAEnum(ParticipantRole, name="participant_role_enum", create_type=True),
        nullable=False,
        default=ParticipantRole.PARTICIPANT,
    )
    status: Mapped[ParticipantStatus] = mapped_column(
        SAEnum(ParticipantStatus, name="participant_status_enum", create_type=True),
        nullable=False,
        default=ParticipantStatus.ACTIVE,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Timestamp when the user was confirmed as a participant.",
    )

    # ------------------------------------------------------------------
    # Relationship back to the expedition aggregate
    # ------------------------------------------------------------------
    expedition: Mapped["Expedition"] = relationship(
        "Expedition",
        back_populates="participants",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # A user can only be a participant once per expedition
        UniqueConstraint("expedition_id", "user_id", name="uq_participant_expedition_user"),
        # Lookup all participants for an expedition
        Index("ix_participants_expedition_id", "expedition_id"),
        # Lookup all expeditions a user is in (My Trips)
        Index("ix_participants_user_id", "user_id"),
        # Filter active participants only
        Index("ix_participants_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExpeditionParticipant expedition={self.expedition_id} "
            f"user={self.user_id} role={self.role} status={self.status}>"
        )
