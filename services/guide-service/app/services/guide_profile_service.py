"""
GuideProfileService — business logic for guide profile CRUD,
soft delete, and admin-controlled verification status transitions.

Rules:
  - Only the guide owner (user_id matches JWT sub) may update their profile.
  - verification_status transitions are admin-only; this service exposes a
    separate method called only from admin endpoints.
  - rating and review_count are never accepted from the client — computed
    server-side by GuideReviewService after each review.
  - Soft delete is guarded: only the guide owner or an admin may delete.
  - A user can only have one active (non-deleted) guide profile.
"""

from __future__ import annotations

import math
from uuid import UUID

from shared import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from shared.logging import setup_logging

from app.models.guide_profile import VerificationStatus
from app.repositories.guide_profile_repository import GuideProfileRepository
from app.schemas.common import GuideFilter, PaginatedResponse, PaginationMeta
from app.schemas.guide_profile import (
    GuideProfileResponse,
    GuideProfileSummary,
    GuideProfileUpdate,
)

logger = setup_logging(service_name="guide-service", log_level="INFO")

# Valid verification status transitions (admin-controlled)
_VALID_VERIFICATION_TRANSITIONS: dict[VerificationStatus, set[VerificationStatus]] = {
    VerificationStatus.PENDING:   {VerificationStatus.VERIFIED, VerificationStatus.REVOKED},
    VerificationStatus.VERIFIED:  {VerificationStatus.SUSPENDED, VerificationStatus.REVOKED},
    VerificationStatus.SUSPENDED: {VerificationStatus.VERIFIED, VerificationStatus.REVOKED},
    VerificationStatus.REVOKED:   set(),
}


class GuideProfileService:
    """Coordinates business logic for guide profile operations."""

    def __init__(self, profile_repo: GuideProfileRepository) -> None:
        self._profile_repo = profile_repo

    # ------------------------------------------------------------------
    # READ — single
    # ------------------------------------------------------------------

    async def get_profile(self, profile_id: UUID) -> GuideProfileResponse:
        """Fetch a single guide profile by primary key. Raises 404 if not found."""
        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {profile_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )
        return GuideProfileResponse.model_validate(profile)

    async def get_profile_by_user(self, user_id: UUID) -> GuideProfileResponse:
        """Fetch the guide profile for a given user. Raises 404 if not found."""
        profile = await self._profile_repo.get_by_user_id(user_id)
        if not profile:
            raise NotFoundException(
                f"No guide profile found for user {user_id}.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )
        return GuideProfileResponse.model_validate(profile)

    # ------------------------------------------------------------------
    # READ — paginated directory listing
    # ------------------------------------------------------------------

    async def list_guides(
        self,
        filters: GuideFilter,
    ) -> PaginatedResponse[GuideProfileSummary]:
        """Return a filtered, paginated list of guide profiles."""
        items, total = await self._profile_repo.list_guides(filters)

        total_pages = max(1, math.ceil(total / filters.page_size))
        pagination = PaginationMeta(
            page=filters.page,
            page_size=filters.page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=filters.page < total_pages,
            has_previous=filters.page > 1,
        )
        return PaginatedResponse[GuideProfileSummary](
            items=[GuideProfileSummary.model_validate(p) for p in items],
            pagination=pagination,
        )

    # ------------------------------------------------------------------
    # UPDATE — guide owner updates their own profile
    # ------------------------------------------------------------------

    async def update_profile(
        self,
        profile_id: UUID,
        payload: GuideProfileUpdate,
        current_user_id: UUID,
    ) -> GuideProfileResponse:
        """Partially update a guide profile.

        Only the guide owner may update their own profile.
        Raises 404 if profile not found, 403 if caller is not the owner.
        """
        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {profile_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )

        if profile.user_id != current_user_id:
            raise ForbiddenException(
                "Only the guide owner can update this profile.",
                error_code="NOT_PROFILE_OWNER",
            )

        update_data = payload.model_dump(exclude_none=True)
        updated = await self._profile_repo.update(
            profile_id,
            updated_by=current_user_id,
            **update_data,
        )
        if not updated:
            raise NotFoundException(
                f"Guide profile {profile_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )
        return GuideProfileResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # UPDATE — admin verification status transition
    # ------------------------------------------------------------------

    async def transition_verification_status(
        self,
        profile_id: UUID,
        new_status: VerificationStatus,
        admin_user_id: UUID,
    ) -> GuideProfileResponse:
        """Transition a guide profile's verification status (admin only).

        Enforces the state machine defined in _VALID_VERIFICATION_TRANSITIONS.
        The caller is responsible for verifying admin role before calling this.
        """
        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {profile_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )

        allowed = _VALID_VERIFICATION_TRANSITIONS.get(profile.verification_status, set())
        if new_status not in allowed:
            from shared import ValidationException
            raise ValidationException(
                f"Cannot transition from '{profile.verification_status}' to '{new_status}'.",
                error_code="INVALID_VERIFICATION_TRANSITION",
            )

        updated = await self._profile_repo.update_verification_status(
            profile_id,
            new_status,
            updated_by=admin_user_id,
        )
        if not updated:
            raise NotFoundException(
                f"Guide profile {profile_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )
        return GuideProfileResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # SOFT DELETE
    # ------------------------------------------------------------------

    async def delete_profile(
        self,
        profile_id: UUID,
        current_user_id: UUID,
    ) -> None:
        """Soft-delete a guide profile. Only the owner may delete."""
        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {profile_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )

        if profile.user_id != current_user_id:
            raise ForbiddenException(
                "Only the guide owner can delete this profile.",
                error_code="NOT_PROFILE_OWNER",
            )

        deleted = await self._profile_repo.soft_delete(
            profile_id, deleted_by=current_user_id
        )
        if not deleted:
            raise NotFoundException(
                f"Guide profile {profile_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )
