"""
GearItem model — the backend of the Pack Weight Optimizer.

Each row represents one gear item in an expedition's packing list.
The service layer aggregates all gear items for an expedition to compute:
  - total weight
  - weight per category
  - overall pack weight classification (Ultralight / Lightweight / Standard / Heavy)

Weight Classification Thresholds (stored as service-layer constants,
NOT as database values — they are a business rule, not data):
  Ultralight     < 5,000 g  (5 kg base pack)
  Lightweight    < 9,000 g  (9 kg base pack)
  Standard       < 18,000 g (18 kg)
  Heavy          ≥ 18,000 g

Gear Categories (per PRD):
  BASE_PACK    — shelter, sleeping system, load-bearing equipment
  CONSUMABLES  — food, water, fuel
  WORN_GEAR    — clothing worn on the body (typically excluded from pack weight)

Database: trip_db
Table:    gear_items
"""

import uuid
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
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

class GearCategory(str, PyEnum):
    """Packing category for a gear item.

    BASE_PACK   — items carried in the pack (shelter, sleeping, equipment).
    CONSUMABLES — food, water, fuel — weight that decreases during the trip.
    WORN_GEAR   — clothing and items worn on the body; often excluded from
                  base pack weight calculations in ultralight methodology.
    """
    BASE_PACK = "BASE_PACK"
    CONSUMABLES = "CONSUMABLES"
    WORN_GEAR = "WORN_GEAR"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class GearItem(Base, TimestampMixin):
    """A single item in an expedition's packing list.

    TimestampMixin provides: created_at, updated_at

    Key design decisions:
    - weight_grams uses INTEGER (not NUMERIC) because weights are always
      recorded in whole grams — this avoids floating-point precision issues
      during aggregation.
    - A CheckConstraint ensures weight_grams >= 0 (zero is valid for
      massless digital items like maps/apps a user may want to track).
    - quantity defaults to 1; allows representing multiple identical items
      without duplication rows.
    - is_packed is the checkbox state — stored server-side so it persists
      across sessions (required for offline-first sync in Phase 2).
    - added_by is the participant UUID who added the item (for future
      shared-packing-ledger functionality per PRD Future Scope).
    - No soft delete: gear items are replaced or hard-deleted during
      packing list management.
    """

    __tablename__ = "gear_items"

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
    added_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="UUID of the participant who added this item. NOT a SQL FK.",
    )

    # ------------------------------------------------------------------
    # Gear item details
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Descriptive item name (e.g., 'Sleeping Bag', 'Stove').",
    )
    category: Mapped[GearCategory] = mapped_column(
        SAEnum(GearCategory, name="gear_category_enum", create_type=True),
        nullable=False,
        default=GearCategory.BASE_PACK,
    )
    weight_grams: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Item weight in grams. Zero is valid (e.g., for tracking purposes).",
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Number of this item being carried.",
    )

    # ------------------------------------------------------------------
    # Packing status
    # ------------------------------------------------------------------
    is_packed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the item has been physically packed. Supports offline checklist.",
    )

    # ------------------------------------------------------------------
    # Relationship back to the expedition aggregate
    # ------------------------------------------------------------------
    expedition: Mapped["Expedition"] = relationship(
        "Expedition",
        back_populates="gear_items",
    )

    # ------------------------------------------------------------------
    # Constraints and indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # Weight must be non-negative
        CheckConstraint("weight_grams >= 0", name="ck_gear_weight_non_negative"),
        # Quantity must be at least 1
        CheckConstraint("quantity >= 1", name="ck_gear_quantity_positive"),
        # Fetch all gear for an expedition (Packing tab)
        Index("ix_gear_items_expedition_id", "expedition_id"),
        # Filter by category (weight breakdown per category)
        Index("ix_gear_items_category", "category"),
        # Compound: fetch gear for expedition grouped by category
        Index("ix_gear_items_expedition_category", "expedition_id", "category"),
    )

    def __repr__(self) -> str:
        return (
            f"<GearItem id={self.id} expedition={self.expedition_id} "
            f"name={self.name!r} weight={self.weight_grams}g "
            f"category={self.category} packed={self.is_packed}>"
        )
