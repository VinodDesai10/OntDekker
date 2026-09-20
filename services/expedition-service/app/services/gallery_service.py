"""
GalleryService — business logic for expedition photo gallery.

Rules enforced:
  - Only ACTIVE participants can upload photos
  - Expedition must be PUBLISHED, ACTIVE, or COMPLETED for gallery access
  - Only the uploader or an organiser can delete a photo
  - Binary files are never handled here — only MinIO object URLs
"""

from __future__ import annotations

from uuid import UUID

from shared import ForbiddenException, NotFoundException, ValidationException

from app.models.expedition import ExpeditionStatus
from app.models.participant import ParticipantRole, ParticipantStatus
from app.repositories.expedition_repository import ExpeditionRepository
from app.repositories.gallery_repository import GalleryRepository
from app.repositories.participant_repository import ParticipantRepository
from app.schemas.gallery import (
    GalleryPhotoCreate,
    GalleryPhotoResponse,
    GalleryPhotoUpdate,
    GalleryResponse,
)

_GALLERY_VIEWABLE_STATUSES = {
    ExpeditionStatus.PUBLISHED,
    ExpeditionStatus.ACTIVE,
    ExpeditionStatus.COMPLETED,
    ExpeditionStatus.ARCHIVED,
}


class GalleryService:

    def __init__(
        self,
        expedition_repo: ExpeditionRepository,
        gallery_repo: GalleryRepository,
        participant_repo: ParticipantRepository,
    ) -> None:
        self._expedition_repo = expedition_repo
        self._gallery_repo = gallery_repo
        self._participant_repo = participant_repo

    async def get_gallery(
        self, expedition_id: UUID, current_user_id: UUID
    ) -> GalleryResponse:
        """Return all gallery photos. User must be an active participant."""
        await self._require_participant(expedition_id, current_user_id)
        photos = await self._gallery_repo.list_by_expedition(expedition_id)
        return GalleryResponse(
            expedition_id=expedition_id,
            photos=[GalleryPhotoResponse.model_validate(p) for p in photos],
            total_photos=len(photos),
        )

    async def add_photo(
        self,
        expedition_id: UUID,
        payload: GalleryPhotoCreate,
        current_user_id: UUID,
    ) -> GalleryPhotoResponse:
        """Register a new photo URL. The caller must be an active participant."""
        expedition = await self._expedition_repo.get_by_id(expedition_id)
        if not expedition:
            raise NotFoundException(
                f"Expedition {expedition_id} not found.",
                error_code="EXPEDITION_NOT_FOUND",
            )
        if expedition.status not in _GALLERY_VIEWABLE_STATUSES:
            raise ValidationException(
                f"Cannot upload photos to an expedition with status '{expedition.status}'.",
                error_code="GALLERY_NOT_AVAILABLE",
            )
        await self._require_participant(expedition_id, current_user_id)
        photo = await self._gallery_repo.add_photo(
            expedition_id=expedition_id,
            uploaded_by=current_user_id,
            image_url=payload.image_url,
            caption=payload.caption,
            display_order=payload.display_order,
        )
        return GalleryPhotoResponse.model_validate(photo)

    async def update_photo(
        self,
        expedition_id: UUID,
        photo_id: UUID,
        payload: GalleryPhotoUpdate,
        current_user_id: UUID,
    ) -> GalleryPhotoResponse:
        """Update photo caption or display_order. Uploader or organiser only."""
        photo = await self._gallery_repo.get_by_id(photo_id)
        if not photo or photo.expedition_id != expedition_id:
            raise NotFoundException(
                "Photo not found.", error_code="PHOTO_NOT_FOUND"
            )
        await self._require_uploader_or_organiser(expedition_id, photo.uploaded_by, current_user_id)
        updated = await self._gallery_repo.update_photo(
            photo_id,
            caption=payload.caption,
            display_order=payload.display_order,
        )
        return GalleryPhotoResponse.model_validate(updated)

    async def delete_photo(
        self,
        expedition_id: UUID,
        photo_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Delete a photo row. Uploader or organiser/co-organiser only."""
        photo = await self._gallery_repo.get_by_id(photo_id)
        if not photo or photo.expedition_id != expedition_id:
            raise NotFoundException(
                "Photo not found.", error_code="PHOTO_NOT_FOUND"
            )
        await self._require_uploader_or_organiser(expedition_id, photo.uploaded_by, current_user_id)
        await self._gallery_repo.delete_photo(photo_id)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    async def _require_participant(self, expedition_id: UUID, user_id: UUID) -> None:
        is_member = await self._participant_repo.is_participant(expedition_id, user_id)
        if not is_member:
            raise ForbiddenException(
                "Only expedition participants can access the gallery.",
                error_code="NOT_PARTICIPANT",
            )

    async def _require_uploader_or_organiser(
        self, expedition_id: UUID, uploader_id: UUID, current_user_id: UUID
    ) -> None:
        if current_user_id == uploader_id:
            return
        participant = await self._participant_repo.get_by_expedition_and_user(
            expedition_id, current_user_id
        )
        if not participant or participant.role not in (
            ParticipantRole.ORGANIZER,
            ParticipantRole.CO_ORGANIZER,
        ):
            raise ForbiddenException(
                "Only the photo uploader or expedition organiser can modify this photo.",
                error_code="NOT_PHOTO_OWNER",
            )
