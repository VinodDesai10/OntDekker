"""
Guide Reviews router — reviews sub-resource.

Routes: /api/v1/guides/{guide_id}/reviews

Endpoints:
  POST /api/v1/guides/{guide_id}/reviews         — submit a review
  GET  /api/v1/guides/{guide_id}/reviews         — list reviews (paginated)
  GET  /api/v1/guides/{guide_id}/reviews/summary — aggregated rating summary
"""

from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from shared.dependencies import get_current_user

from app.dependencies.guide_deps import get_guide_review_service
from app.schemas.guide_review import (
    GuideRatingSummary,
    GuideReviewCreate,
    GuideReviewListResponse,
    GuideReviewResponse,
)
from app.services.guide_review_service import GuideReviewService

router = APIRouter(
    prefix="/api/v1/guides",
    tags=["Guide Reviews"],
)


@router.post(
    "/{guide_id}/reviews",
    response_model=GuideReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a guide review",
    description=(
        "Submits a review for a guide. "
        "The guide must be VERIFIED. One review per reviewer per guide. "
        "expedition_id is optional — omit for guides met outside expeditions."
    ),
)
async def submit_review(
    guide_id: UUID,
    payload: GuideReviewCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideReviewService = Depends(get_guide_review_service),
) -> GuideReviewResponse:
    reviewer_id = UUID(current_user["sub"])
    return await service.submit_review(guide_id, payload, reviewer_id)


@router.get(
    "/{guide_id}/reviews",
    response_model=GuideReviewListResponse,
    status_code=status.HTTP_200_OK,
    summary="List guide reviews",
    description="Returns a paginated list of reviews for a guide. Publicly readable.",
)
async def list_reviews(
    guide_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: GuideReviewService = Depends(get_guide_review_service),
) -> GuideReviewListResponse:
    return await service.list_reviews(guide_id, page=page, page_size=page_size)


@router.get(
    "/{guide_id}/reviews/summary",
    response_model=GuideRatingSummary,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated rating summary",
    description=(
        "Returns the computed average ratings across all dimensions "
        "and the would-recommend percentage. Publicly readable."
    ),
)
async def get_rating_summary(
    guide_id: UUID,
    service: GuideReviewService = Depends(get_guide_review_service),
) -> GuideRatingSummary:
    return await service.get_rating_summary(guide_id)
