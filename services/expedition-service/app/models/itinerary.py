"""
ExpeditionItinerary model.

Represents a single day in the expedition's itinerary plan.
Each expedition can have multiple itinerary entries — one per planned day.
They are ordered by day_number and displayed in the "Itinerary" tab of
the Expedition Workspace.

Database: trip_db
Table:    expedition_itinerary
"""

import uuid
from datetime import time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
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

class ExpeditionItinerary(Base, TimestampMixin):
    """A single day entry in an expedition's itinerary.

    TimestampMixin provides: created_at, updated_at

    Key design decisions:
    - day_number is the sort key (Day 1, Day 2, ...).
    - UniqueConstraint on (expedition_id, day_number) prevents two entries
      for the same day on the same expedition.
    - activity_time is optional — some days may not have a fixed start time.
    - location is optional — some days may be in transit without a fixed point.
    - notes is a free-text field for extra organiser instructions.
    - No soft delete here: itinerary days are typically replaced wholesale
      (PUT /expeditions/{id}/itinerary replaces all days). If needed in
      future the parent expedition's soft delete is sufficient.
    """

    __tablename__ = "expedition_itinerary"

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
    # Day identification
    # ------------------------------------------------------------------
    day_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Ordinal day number in the expedition (1-indexed).",
    )

    # ------------------------------------------------------------------
    # Day content
    # ------------------------------------------------------------------
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Short title for the day's plan (e.g., 'Base Camp to Summit').",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of the day's activities.",
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        comment="Name or description of the day's primary location.",
    )
    activity_time: Mapped[Optional[time]] = mapped_column(
        Time,
        nullable=True,
        comment="Planned start time for the day's main activity (local time).",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text organiser notes or special instructions for this day.",
    )

    # ------------------------------------------------------------------
    # Relationship back to the expedition aggregate
    # ------------------------------------------------------------------
    expedition: Mapped["Expedition"] = relationship(
        "Expedition",
        back_populates="itinerary",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # Each expedition can have only one entry per day number
        UniqueConstraint(
            "expedition_id", "day_number",
            name="uq_itinerary_expedition_day",
        ),
        # Fetch all itinerary days for an expedition (most frequent query)
        Index("ix_itinerary_expedition_id", "expedition_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExpeditionItinerary expedition={self.expedition_id} "
            f"day={self.day_number} title={self.title!r}>"
        )
