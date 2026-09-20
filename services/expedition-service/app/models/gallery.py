"""
ExpeditionGallery model.

Represents a single uploaded photo in an expedition's gallery.
The actual binary image is stored in MinIO under the `expeditions` bucket.
Only the object URL is stored in this table.

Gallery path convention (MinIO):
    expeditions/gallery/{expedition_id}/{photo_id}.jpg

Database: trip_db
Table:    expedition_gallery
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.expedition import Expedition


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class ExpeditionGallery(Base, TimestampMixin):
    """A single photo in an expedition's gallery.

    TimestampMixin provides: created_at, updated_at

    Key design decisions:
    - image_url stores the full MinIO object URL (or CDN URL). Binary data
      never lives in PostgreSQL.
    - uploaded_by stores the UUID of the participant who uploaded the photo.
      It is NOT a SQL FK because we don't own user_db.
    - display_order allows the organiser or uploader to control gallery
      ordering. Defaults to the insertion order (0-indexed).
    - caption is optional: participants may or may not add a caption.
    - No soft delete: photo deletion removes the row and the organiser /
      uploader is responsible for triggering the MinIO object deletion
      through the service layer.
    """

    __tablename__ = "expedition_gallery"

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
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="UUID of the participant who uploaded this photo. NOT a SQL FK.",
    )

    # ------------------------------------------------------------------
    # Photo content
    # ------------------------------------------------------------------
    image_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Full MinIO/CDN object URL for the photo.",
    )
    caption: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional caption provided by the uploader.",
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Display ordering index for the gallery view (ascending).",
    )

    # ------------------------------------------------------------------
    # Relationship back to the expedition aggregate
    # ------------------------------------------------------------------
    expedition: Mapped["Expedition"] = relationship(
        "Expedition",
        back_populates="gallery",
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # Fetch all photos for an expedition (gallery view)
        Index("ix_gallery_expedition_id", "expedition_id"),
        # Filter photos uploaded by a specific participant
        Index("ix_gallery_uploaded_by", "uploaded_by"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExpeditionGallery id={self.id} expedition={self.expedition_id} "
            f"order={self.display_order}>"
        )
