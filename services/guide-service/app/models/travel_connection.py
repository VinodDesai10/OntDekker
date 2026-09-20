"""
TravelConnection model.

One of OntDekker's signature features — stores the long-term relationship
between a guide and a traveler across multiple expeditions and interactions.

guide_id FK → guide_profiles (same database, CASCADE delete).
traveler_id is a plain UUID — no SQL FK (cross-service boundary).

Database: guide_db
Table:    travel_connections
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UUID,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.guide_profile import GuideProfile


class TravelConnection(Base, TimestampMixin):
    """Tracks the long-term relationship between a guide and a traveler.

    Counters (expeditions_together, conversation_count, photos_shared) are
    incremented by service-layer events — not computed on the fly — so they
    survive even if the originating expedition or chat record is deleted.

    FK → guide_profiles.id with CASCADE delete.
    traveler_id → User Service (no SQL FK — cross-service).

    TimestampMixin provides: created_at, updated_at
    """

    __tablename__ = "travel_connections"

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
    # External reference — no SQL FK to user_db
    # ------------------------------------------------------------------
    traveler_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="UUID reference to user_db.user_profiles. NOT a SQL FK.",
    )

    # ------------------------------------------------------------------
    # Relationship timeline
    # ------------------------------------------------------------------
    first_met: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the first expedition or interaction together.",
    )
    last_interaction: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the most recent interaction.",
    )

    # ------------------------------------------------------------------
    # Aggregate interaction counters (incremented by service layer)
    # ------------------------------------------------------------------
    expeditions_together: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of expeditions guide and traveler have shared.",
    )
    conversation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of chat conversations between guide and traveler.",
    )
    photos_shared: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of photos shared between guide and traveler.",
    )

    # ------------------------------------------------------------------
    # Traveler bookmarks this guide for easy reconnection
    # ------------------------------------------------------------------
    bookmarked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if the traveler has bookmarked this guide.",
    )

    # ------------------------------------------------------------------
    # Relationship back to parent
    # ------------------------------------------------------------------
    guide: Mapped["GuideProfile"] = relationship(
        "GuideProfile",
        back_populates="travel_connections",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # One connection record per guide–traveler pair
        UniqueConstraint(
            "guide_id", "traveler_id",
            name="uq_travel_connection_guide_traveler",
        ),
        # A guide cannot be connected to themselves
        CheckConstraint(
            "guide_id != traveler_id",
            name="ck_travel_connection_no_self_connection",
        ),
        # Non-negative counters
        CheckConstraint(
            "expeditions_together >= 0",
            name="ck_travel_connection_expeditions_non_negative",
        ),
        CheckConstraint(
            "conversation_count >= 0",
            name="ck_travel_connection_conversations_non_negative",
        ),
        CheckConstraint(
            "photos_shared >= 0",
            name="ck_travel_connection_photos_non_negative",
        ),
        # Indexes
        Index("ix_travel_connections_guide_id", "guide_id"),
        Index("ix_travel_connections_traveler_id", "traveler_id"),
        # Compound: traveler's "my guides" view
        Index("ix_travel_connections_traveler_guide", "traveler_id", "guide_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<TravelConnection guide_id={self.guide_id} "
            f"traveler_id={self.traveler_id} "
            f"expeditions={self.expeditions_together}>"
        )
