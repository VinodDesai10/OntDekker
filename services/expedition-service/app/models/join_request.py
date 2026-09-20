"""
ExpeditionJoinRequest model.

Represents a request from a user to join a PRIVATE expedition.
When the organiser approves, a corresponding ExpeditionParticipant row
is created and this request's status is updated to APPROVED.

For PUBLIC expeditions, participants are added directly without
going through this table.

Database: trip_db
Table:    expedition_join_requests
"""

import uuid
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
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

class JoinRequestStatus(str, PyEnum):
    """Lifecycle of a join request.

    PENDING  — submitted, awaiting organiser decision.
    APPROVED — organiser accepted; a participant row will have been created.
    REJECTED — organiser declined the request.
    CANCELLED — the requester withdrew before a decision was made.
    """
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class ExpeditionJoinRequest(Base, TimestampMixin):
    """A user's request to join a private expedition.

    TimestampMixin provides: created_at, updated_at

    Key design decisions:
    - UniqueConstraint on (expedition_id, user_id) prevents submitting
      duplicate requests. A user must cancel their existing request before
      reapplying.
    - user_id has NO SQL FK to user_db; enforced at the application layer.
    - reviewed_by stores the organiser/co-organiser UUID who acted on the
      request (for audit purposes).
    - rejection_reason is optional, allows the organiser to give feedback.
    """

    __tablename__ = "expedition_join_requests"

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
    # External reference — no SQL FK to user_db
    # ------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="UUID reference to user_db.user_profiles. NOT a SQL FK.",
    )

    # ------------------------------------------------------------------
    # Request content and status
    # ------------------------------------------------------------------
    message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional introductory message from the applicant.",
    )
    status: Mapped[JoinRequestStatus] = mapped_column(
        SAEnum(JoinRequestStatus, name="join_request_status_enum", create_type=True),
        nullable=False,
        default=JoinRequestStatus.PENDING,
    )

    # ------------------------------------------------------------------
    # Review metadata (populated when organiser acts on the request)
    # ------------------------------------------------------------------
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID of the organiser/co-organiser who reviewed this request.",
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional reason provided by organiser when rejecting.",
    )

    # ------------------------------------------------------------------
    # Relationship back to the expedition aggregate
    # ------------------------------------------------------------------
    expedition: Mapped["Expedition"] = relationship(
        "Expedition",
        back_populates="join_requests",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # A user can only have one active request per expedition
        UniqueConstraint(
            "expedition_id", "user_id",
            name="uq_join_request_expedition_user",
        ),
        # Fetch all requests for an expedition (organiser inbox)
        Index("ix_join_requests_expedition_id", "expedition_id"),
        # Fetch all requests submitted by a user
        Index("ix_join_requests_user_id", "user_id"),
        # Filter pending requests (the most common query)
        Index("ix_join_requests_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExpeditionJoinRequest id={self.id} expedition={self.expedition_id} "
            f"user={self.user_id} status={self.status}>"
        )
