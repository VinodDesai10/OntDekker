"""
Reviews router — sub-resource under /api/v1/expeditions/{expedition_id}
"""

from __future__ import annotations

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from shared.dependencies import get_current_user

from app.dependencies.expedition_deps import get_review_service
from app.schemas.review import ReviewCreate, ReviewListResponse, ReviewResponse, ReviewSummary
from app.services.review_service import ReviewService

router = APIRouter(
    prefix="/api/v1/expeditions",
    tags=["Reviews"],
)


@router.post(
    "/{expedition_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a post-expedition review",
    description=(
        "Submits a peer review for another participant. "
        "Only available after the expedition is COMPLETED. "
        "One review per reviewer-reviewee pair per expedition."
    ),
)
async def submit_review(
    expedition_id: UUID,
    payload: ReviewCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    current_user_id = UUID(current_user["sub"])
    return await service.submit_review(expedition_id, payload, current_user_id)


@router.get(
    "/{expedition_id}/reviews",
    response_model=ReviewListResponse,
    status_code=status.HTTP_200_OK,
    summary="List reviews for an expedition",
)
async def list_reviews(
    expedition_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: ReviewService = Depends(get_review_service),
) -> ReviewListResponse:
    return await service.list_reviews(expedition_id, page=page, page_size=page_size)


@router.get(
    "/{expedition_id}/reviews/{reviewee_id}/summary",
    response_model=ReviewSummary,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated review summary for a participant",
    description=(
        "Returns the average rating across all dimensions and the "
        "'would travel again' percentage for a specific participant in this expedition."
    ),
)
async def get_review_summary(
    expedition_id: UUID,
    reviewee_id: UUID,
    service: ReviewService = Depends(get_review_service),
) -> ReviewSummary:
    return await service.get_review_summary(expedition_id, reviewee_id)
