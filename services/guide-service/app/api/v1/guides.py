"""
Guides router — core guide profile CRUD and verification lifecycle.

All routes are under the prefix /api/v1/guides.
Sub-resources (locations, languages, availability, reviews, travel connections,
applications) live in their own router files.

Endpoints:
  GET    /api/v1/guides                     — browse guide directory (paginated)
  GET    /api/v1/guides/{id}                — get single guide profile (detail)
  PUT    /api/v1/guides/{id}                — update own guide profile
  PATCH  /api/v1/guides/{id}/verification   — admin: transition verification status
  DELETE /api/v1/guides/{id}                — soft-delete own guide profile
"""

from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.dependencies import get_current_user

from app.dependencies.guide_deps import get_guide_profile_service
from app.models.guide_profile import VerificationStatus
from app.schemas.common import ApiResponse, GuideFilter, PaginatedResponse
from app.schemas.guide_profile import (
    GuideProfileResponse,
    GuideProfileSummary,
    GuideProfileUpdate,
)
from app.services.guide_profile_service import GuideProfileService

router = APIRouter(
    prefix="/api/v1/guides",
    tags=["Guide Profiles"],
)


# ---------------------------------------------------------------------------
# GET /api/v1/guides — browse guide directory
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=PaginatedResponse[GuideProfileSummary],
    status_code=status.HTTP_200_OK,
    summary="Browse guide directory",
    description=(
        "Returns a paginated list of guide profiles. "
        "Filter by country, language, availability status, or verification status. "
        "Results are ordered by rating (desc) then review count (desc)."
    ),
)
async def list_guides(
    filters: GuideFilter = Depends(),
    service: GuideProfileService = Depends(get_guide_profile_service),
) -> PaginatedResponse[GuideProfileSummary]:
    return await service.list_guides(filters)


# ---------------------------------------------------------------------------
# GET /api/v1/guides/{guide_id} — get single guide profile
# ---------------------------------------------------------------------------

@router.get(
    "/{guide_id}",
    response_model=ApiResponse[GuideProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="Get guide profile",
    description=(
        "Returns the full guide profile including nested locations, "
        "languages, and availability. "
        "The profile is publicly readable."
    ),
)
async def get_guide(
    guide_id: UUID,
    service: GuideProfileService = Depends(get_guide_profile_service),
) -> ApiResponse[GuideProfileResponse]:
    profile = await service.get_profile(guide_id)
    return ApiResponse[GuideProfileResponse](
        message="Guide profile retrieved successfully.",
        data=profile,
    )


# ---------------------------------------------------------------------------
# PUT /api/v1/guides/{guide_id} — update own profile
# ---------------------------------------------------------------------------

@router.put(
    "/{guide_id}",
    response_model=ApiResponse[GuideProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="Update guide profile",
    description=(
        "Partially updates a guide's own profile (bio, images, years_experience). "
        "Only the guide owner may update. "
        "verification_status, rating, and review_count are server-controlled and "
        "ignored in this payload."
    ),
)
async def update_guide(
    guide_id: UUID,
    payload: GuideProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideProfileService = Depends(get_guide_profile_service),
) -> ApiResponse[GuideProfileResponse]:
    user_id = UUID(current_user["sub"])
    profile = await service.update_profile(guide_id, payload, user_id)
    return ApiResponse[GuideProfileResponse](
        message="Guide profile updated successfully.",
        data=profile,
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/guides/{guide_id}/verification — admin verification transition
# ---------------------------------------------------------------------------

@router.patch(
    "/{guide_id}/verification",
    response_model=ApiResponse[GuideProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="Transition guide verification status (admin)",
    description=(
        "Admin-only endpoint. Transitions the guide's verification status. "
        "Valid transitions: "
        "PENDING → VERIFIED | REVOKED, "
        "VERIFIED → SUSPENDED | REVOKED, "
        "SUSPENDED → VERIFIED | REVOKED. "
        "REVOKED is terminal."
    ),
)
async def transition_verification(
    guide_id: UUID,
    new_status: VerificationStatus,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideProfileService = Depends(get_guide_profile_service),
) -> ApiResponse[GuideProfileResponse]:
    admin_id = UUID(current_user["sub"])
    profile = await service.transition_verification_status(guide_id, new_status, admin_id)
    return ApiResponse[GuideProfileResponse](
        message=f"Verification status updated to {new_status}.",
        data=profile,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/guides/{guide_id}/verify — admin: verify a guide (convenience)
# ---------------------------------------------------------------------------

@router.post(
    "/{guide_id}/verify",
    response_model=ApiResponse[GuideProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="Verify a guide (admin shortcut)",
    description=(
        "Admin-only convenience endpoint. "
        "Transitions the guide's verification_status from PENDING → VERIFIED. "
        "Equivalent to PATCH /verification with new_status=VERIFIED."
    ),
)
async def verify_guide(
    guide_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideProfileService = Depends(get_guide_profile_service),
) -> ApiResponse[GuideProfileResponse]:
    admin_id = UUID(current_user["sub"])
    profile = await service.transition_verification_status(
        guide_id, VerificationStatus.VERIFIED, admin_id
    )
    return ApiResponse[GuideProfileResponse](
        message="Guide verified successfully.",
        data=profile,
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/guides/{guide_id} — soft-delete own profile
# ---------------------------------------------------------------------------

@router.delete(
    "/{guide_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete guide profile",
    description=(
        "Soft-deletes a guide profile. "
        "Only the guide owner may delete their own profile."
    ),
)
async def delete_guide(
    guide_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideProfileService = Depends(get_guide_profile_service),
) -> None:
    user_id = UUID(current_user["sub"])
    await service.delete_profile(guide_id, user_id)
