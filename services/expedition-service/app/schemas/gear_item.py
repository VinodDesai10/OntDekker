"""
Gear Item Pydantic schemas — Pack Weight Optimizer.

Covers request/response shapes for:
  GET    /api/v1/expeditions/{id}/gear          — full packing list + summary
  POST   /api/v1/expeditions/{id}/gear          — add gear item
  PATCH  /api/v1/expeditions/{id}/gear/{item_id} — update item (weight, qty, packed)
  DELETE /api/v1/expeditions/{id}/gear/{item_id} — remove item

The PackWeightSummary is the computed aggregate returned alongside the
gear list — it provides the total weight, per-category breakdown, and
the overall weight classification (Ultralight / Lightweight / Standard / Heavy).

Weight classification thresholds (service-layer constants, NOT stored in DB):
  ULTRALIGHT  : base pack < 5,000 g
  LIGHTWEIGHT : base pack < 9,000 g
  STANDARD    : base pack < 18,000 g
  HEAVY       : base pack >= 18,000 g
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.gear_item import GearCategory


# ---------------------------------------------------------------------------
# Weight classification enum (returned in PackWeightSummary)
# ---------------------------------------------------------------------------

class PackWeightClassification(str, Enum):
    """Overall pack weight category based on base-pack total weight."""
    ULTRALIGHT  = "ULTRALIGHT"
    LIGHTWEIGHT = "LIGHTWEIGHT"
    STANDARD    = "STANDARD"
    HEAVY       = "HEAVY"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class GearItemCreate(BaseModel):
    """Body for POST /api/v1/expeditions/{id}/gear.

    added_by is set server-side from the authenticated participant's JWT.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Descriptive item name (e.g., 'Sleeping Bag -20°C').",
        examples=["Sleeping Bag -20°C"],
    )
    category: GearCategory = Field(
        default=GearCategory.BASE_PACK,
        description="Packing category: BASE_PACK, CONSUMABLES, or WORN_GEAR.",
    )
    weight_grams: int = Field(
        default=0,
        ge=0,
        le=50_000,
        description=(
            "Item weight in grams (0–50,000). "
            "Zero is valid for digital/massless tracking items."
        ),
        examples=[1200],
    )
    quantity: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Number of this item being carried (1–100).",
    )
    is_packed: bool = Field(
        default=False,
        description="Packed/unpacked checkbox state.",
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Gear item name must not be blank.")
        return v.strip()


class GearItemUpdate(BaseModel):
    """Partial update for a gear item.

    All fields optional — only provided fields are updated.
    expedition_id and added_by cannot be changed.
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    category: Optional[GearCategory] = Field(default=None)
    weight_grams: Optional[int] = Field(
        default=None,
        ge=0,
        le=50_000,
    )
    quantity: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
    )
    is_packed: Optional[bool] = Field(
        default=None,
        description="Toggle packed/unpacked state.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class GearItemResponse(BaseModel):
    """Single gear item record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    expedition_id: UUID
    added_by: UUID
    name: str
    category: GearCategory
    weight_grams: int
    quantity: int
    is_packed: bool
    created_at: datetime
    updated_at: datetime

    @property
    def total_weight_grams(self) -> int:
        """Computed: weight_grams * quantity."""
        return self.weight_grams * self.quantity


class PackWeightSummary(BaseModel):
    """Aggregated weight summary for the Pack Weight Optimizer UI.

    Computed by the service layer from all gear items — never stored in DB.

    Fields:
      total_weight_grams    — sum of (weight_grams * quantity) for all items
      base_pack_grams       — total for BASE_PACK category only
      consumables_grams     — total for CONSUMABLES category only
      worn_gear_grams       — total for WORN_GEAR category only
      packed_items_count    — number of items with is_packed = True
      total_items_count     — total number of gear items
      classification        — overall weight class based on base_pack_grams
    """

    total_weight_grams: int = Field(ge=0)
    base_pack_grams: int = Field(ge=0)
    consumables_grams: int = Field(ge=0)
    worn_gear_grams: int = Field(ge=0)
    packed_items_count: int = Field(ge=0)
    total_items_count: int = Field(ge=0)
    classification: PackWeightClassification


class GearListResponse(BaseModel):
    """Full packing list for an expedition — items + weight summary."""

    expedition_id: UUID
    items: List[GearItemResponse] = Field(default_factory=list)
    summary: PackWeightSummary
