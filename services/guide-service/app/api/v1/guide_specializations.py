"""
Guide Specializations router.

All routes are under the prefix /api/v1/guides/{guide_id}/specializations.

Endpoints:
  GET    /api/v1/guides/{guide_id}/specializations         — list guide's specializations
  POST   /api/v1/guides/{guide_id}/specializations         — add a specialization
  DELETE /api/v1/guides/{guide_id}/specializations/{id}   — remove a specialization
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.dependencies import get_current_user, get_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.guide_specialization import (
    GuideSpecializationCreate,
    GuideSpecializationResponse,
)
from app.schemas.common import ApiResponse
from app.models.guide_specialization import GuideSpecialization
from app.models.guide_profile import GuideProfile
from shared.exceptions import NotFoundException, ForbiddenException, ConflictException
from sqlalchemy import select, delete

router = APIRouter(
    prefix="/api/v1/guides",
    tags=["Guide Specializations"],
)


# ---------------------------------------------------------------------------
# GET /api/v1/guides/{guide_id}/specializations
# ---------------------------------------------------------------------------

@router.get(
    "/{guide_id}/specializations",
    response_model=List[GuideSpecializationResponse],
    status_code=status.HTTP_200_OK,
    summary="List guide specializations",
)
async def list_specializations(
    guide_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[GuideSpecializationResponse]:
    result = await db.execute(
        select(GuideSpecialization)
        .where(GuideSpecialization.guide_id == guide_id)
        .order_by(GuideSpecialization.category)
    )
    rows = result.scalars().all()
    return [GuideSpecializationResponse.model_validate(r) for r in rows]


# ---------------------------------------------------------------------------
# POST /api/v1/guides/{guide_id}/specializations
# ---------------------------------------------------------------------------

@router.post(
    "/{guide_id}/specializations",
    response_model=GuideSpecializationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add guide specialization",
    description="Only the guide owner may add specializations.",
)
async def add_specialization(
    guide_id: UUID,
    payload: GuideSpecializationCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GuideSpecializationResponse:
    user_id = UUID(current_user["sub"])

    # Verify guide exists and belongs to current user
    profile_result = await db.execute(
        select(GuideProfile)
        .where(GuideProfile.id == guide_id)
        .where(GuideProfile.is_deleted.is_(False))
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise NotFoundException(
            f"Guide profile {guide_id} not found.",
            error_code="GUIDE_PROFILE_NOT_FOUND",
        )
    if profile.user_id != user_id:
        raise ForbiddenException(
            "Only the guide owner can add specializations.",
            error_code="NOT_PROFILE_OWNER",
        )

    # Check for duplicate
    existing = await db.execute(
        select(GuideSpecialization)
        .where(GuideSpecialization.guide_id == guide_id)
        .where(GuideSpecialization.category == payload.category)
    )
    if existing.scalar_one_or_none():
        raise ConflictException(
            f"Specialization '{payload.category}' already exists for this guide.",
            error_code="SPECIALIZATION_ALREADY_EXISTS",
        )

    spec = GuideSpecialization(
        id=uuid.uuid4(),
        guide_id=guide_id,
        category=payload.category,
    )
    db.add(spec)
    await db.flush()
    await db.refresh(spec)
    return GuideSpecializationResponse.model_validate(spec)


# ---------------------------------------------------------------------------
# DELETE /api/v1/guides/{guide_id}/specializations/{spec_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{guide_id}/specializations/{spec_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove guide specialization",
    description="Only the guide owner may remove specializations.",
)
async def remove_specialization(
    guide_id: UUID,
    spec_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    user_id = UUID(current_user["sub"])

    # Verify guide exists and belongs to current user
    profile_result = await db.execute(
        select(GuideProfile)
        .where(GuideProfile.id == guide_id)
        .where(GuideProfile.is_deleted.is_(False))
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise NotFoundException(
            f"Guide profile {guide_id} not found.",
            error_code="GUIDE_PROFILE_NOT_FOUND",
        )
    if profile.user_id != user_id:
        raise ForbiddenException(
            "Only the guide owner can remove specializations.",
            error_code="NOT_PROFILE_OWNER",
        )

    result = await db.execute(
        delete(GuideSpecialization)
        .where(GuideSpecialization.id == spec_id)
        .where(GuideSpecialization.guide_id == guide_id)
    )
    if result.rowcount == 0:
        raise NotFoundException(
            f"Specialization {spec_id} not found.",
            error_code="SPECIALIZATION_NOT_FOUND",
        )
