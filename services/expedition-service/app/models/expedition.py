"""
Expedition model — the root aggregate of the Expedition Service.

Every expedition belongs to exactly one community (community_id is a UUID
reference to Community Service, NOT a foreign key into community_db).
The organizer_id is a UUID reference to a user managed by User/Auth Service.

Database: trip_db
Table:    expeditions
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
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
    from app.models.participant import ExpeditionParticipant
    from app.models.join_request import ExpeditionJoinRequest
    from app.models.itinerary import ExpeditionItinerary
    from app.models.gallery import ExpeditionGallery
    from app.models.gear_item import GearItem
    from app.models.review import ExpeditionReview
    from app.models.discussion import ExpeditionDiscussionMessage


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExpeditionStatus(str, PyEnum):
    """Lifecycle states of an expedition.

    DRAFT      — created but not yet visible to other community members.
    PUBLISHED  — visible, open for join requests.
    ACTIVE     — start_date reached, expedition is underway.
    COMPLETED  — end_date passed, reviews can now be submitted.
    CANCELLED  — organiser cancelled before or during the expedition.
    ARCHIVED   — soft-closed, retained for history.
    """
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class ExpeditionVisibility(str, PyEnum):
    """Controls who can discover and join the expedition.

    PUBLIC  — any community member can join directly.
    PRIVATE — community members must submit a join request; organiser approves.
    """
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class Expedition(Base, AuditMixin, SoftDeleteMixin):
    """Root aggregate for an expedition/trip.

    AuditMixin provides: created_at, updated_at, created_by, updated_by
    SoftDeleteMixin provides: is_deleted, deleted_at, deleted_by
    """

    __tablename__ = "expeditions"

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
    # External service references (UUIDs only, no SQL foreign keys)
    # community_id → Community Service (community_db) — not a FK
    #               nullable: personal trips have no community
    # organizer_id → User/Auth Service (user_db / auth_db) — not a FK
    # ------------------------------------------------------------------
    community_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID reference to community_db.communities. NOT a SQL FK. NULL for personal trips.",
    )
    organizer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="UUID reference to user_db.user_profiles. NOT a SQL FK.",
    )

    # ------------------------------------------------------------------
    # Core expedition details
    # ------------------------------------------------------------------
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    destination: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    meeting_point: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="Physical meeting location description.",
    )

    # ------------------------------------------------------------------
    # Dates and capacity
    # ------------------------------------------------------------------
    start_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Planned departure date (UTC date).",
    )
    end_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Planned return date (UTC date).",
    )
    max_participants: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        comment="Maximum number of participants including the organiser.",
    )

    # ------------------------------------------------------------------
    # Budget
    # ------------------------------------------------------------------
    budget: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Estimated budget per person in the organiser's chosen currency.",
    )

    # ------------------------------------------------------------------
    # Status and visibility
    # ------------------------------------------------------------------
    status: Mapped[ExpeditionStatus] = mapped_column(
        SAEnum(ExpeditionStatus, name="expedition_status_enum", create_type=True),
        nullable=False,
        default=ExpeditionStatus.DRAFT,
    )
    visibility: Mapped[ExpeditionVisibility] = mapped_column(
        SAEnum(ExpeditionVisibility, name="expedition_visibility_enum", create_type=True),
        nullable=False,
        default=ExpeditionVisibility.PUBLIC,
    )

    # ------------------------------------------------------------------
    # Media (object URL stored; binary lives in MinIO)
    # ------------------------------------------------------------------
    cover_image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="MinIO object URL for the expedition cover image.",
    )

    # ------------------------------------------------------------------
    # Relationships (all one-to-many, all cascade delete-orphan)
    # ------------------------------------------------------------------
    participants: Mapped[List["ExpeditionParticipant"]] = relationship(
        "ExpeditionParticipant",
        back_populates="expedition",
        cascade="all, delete-orphan",
        lazy="select",
    )
    join_requests: Mapped[List["ExpeditionJoinRequest"]] = relationship(
        "ExpeditionJoinRequest",
        back_populates="expedition",
        cascade="all, delete-orphan",
        lazy="select",
    )
    itinerary: Mapped[List["ExpeditionItinerary"]] = relationship(
        "ExpeditionItinerary",
        back_populates="expedition",
        cascade="all, delete-orphan",
        order_by="ExpeditionItinerary.day_number",
        lazy="select",
    )
    gallery: Mapped[List["ExpeditionGallery"]] = relationship(
        "ExpeditionGallery",
        back_populates="expedition",
        cascade="all, delete-orphan",
        order_by="ExpeditionGallery.display_order",
        lazy="select",
    )
    gear_items: Mapped[List["GearItem"]] = relationship(
        "GearItem",
        back_populates="expedition",
        cascade="all, delete-orphan",
        lazy="select",
    )
    reviews: Mapped[List["ExpeditionReview"]] = relationship(
        "ExpeditionReview",
        back_populates="expedition",
        cascade="all, delete-orphan",
        lazy="select",
    )
    discussion_messages: Mapped[List["ExpeditionDiscussionMessage"]] = relationship(
        "ExpeditionDiscussionMessage",
        back_populates="expedition",
        cascade="all, delete-orphan",
        order_by="ExpeditionDiscussionMessage.created_at",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # Most common listing queries: filter by community, order by date
        Index("ix_expeditions_community_id", "community_id"),
        # Filter by organiser (My Trips)
        Index("ix_expeditions_organizer_id", "organizer_id"),
        # Filter by lifecycle state
        Index("ix_expeditions_status", "status"),
        # Exclude soft-deleted rows efficiently
        Index("ix_expeditions_is_deleted", "is_deleted"),
        # Compound: community feed ordered by start date
        Index("ix_expeditions_community_start", "community_id", "start_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<Expedition id={self.id} title={self.title!r} "
            f"status={self.status} organizer={self.organizer_id}>"
        )
