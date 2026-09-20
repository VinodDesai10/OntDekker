"""
Gallery Pydantic schemas.

Covers request/response shapes for:
  POST   /api/v1/expeditions/{id}/gallery          — register uploaded photo
  GET    /api/v1/expeditions/{id}/gallery          — list all photos
  PATCH  /api/v1/expeditions/{id}/gallery/{photo_id} — update caption/order
  DELETE /api/v1/expeditions/{id}/gallery/{photo_id} — remove photo

The binary image is uploaded directly to MinIO by the client using a
pre-signed URL (a separate endpoint provides the URL). Once the upload
succeeds, the client calls POST /gallery with the returned object URL.
This service never handles raw binary data.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GalleryPhotoCreate(BaseModel):
    """Body for POST /api/v1/expeditions/{id}/gallery.

    Called after the client has successfully uploaded an image to MinIO.
    The uploaded_by field is resolved server-side from the JWT.
    """

    image_url: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Full MinIO/CDN object URL returned after successful upload.",
        examples=["https://cdn.ontdekker.com/expeditions/gallery/uuid/photo.jpg"],
    )
    caption: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional caption for this photo (max 500 chars).",
    )
    display_order: int = Field(
        default=0,
        ge=0,
        description="Display ordering index (ascending). Defaults to 0.",
    )

    @field_validator("image_url")
    @classmethod
    def url_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("image_url must not be blank.")
        return v


class GalleryPhotoUpdate(BaseModel):
    """Partial update for caption or display order.

    image_url cannot be changed — delete and re-upload instead.
    uploaded_by cannot be changed.
    """

    caption: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Updated caption (max 500 chars). Pass null to remove caption.",
    )
    display_order: Optional[int] = Field(
        default=None,
        ge=0,
        description="Updated display order index.",
    )


class GalleryPhotoResponse(BaseModel):
    """Single gallery photo record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    expedition_id: UUID
    uploaded_by: UUID
    image_url: str
    caption: Optional[str]
    display_order: int
    created_at: datetime
    updated_at: datetime


class GalleryResponse(BaseModel):
    """Full gallery for an expedition — list of photos ordered by display_order."""

    expedition_id: UUID
    photos: List[GalleryPhotoResponse] = Field(
        default_factory=list,
        description="Photos ordered ascending by display_order.",
    )
    total_photos: int = Field(ge=0)
