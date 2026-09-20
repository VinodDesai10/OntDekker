"""
Guide Applications router — application workflow for becoming a guide.

All routes are under the prefix /api/v1/guides/apply.

Endpoints:
  POST   /api/v1/guides/apply              — create application (DRAFT)
  GET    /api/v1/guides/apply              — get own application
  PATCH  /api/v1/guides/apply/{id}         — update DRAFT application
  POST   /api/v1/guides/apply/{id}/submit  — submit DRAFT → SUBMITTED
  POST   /api/v1/guides/apply/{id}/review  — admin: transition status
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, status

from shared.dependencies import get_current_user

from app.dependencies.guide_deps import get_guide_application_service
from app.models.guide_application import ApplicationStatus
from app.schemas.guide_application import (
    GuideApplicationCreate,
    GuideApplicationResponse,
    GuideApplicationUpdate,
)
from app.services.guide_application_service import GuideApplicationService

router = APIRouter(
    prefix="/api/v1/guides/apply",
    tags=["Guide Applications"],
)


# ---------------------------------------------------------------------------
# POST /api/v1/guides/apply — create a new application (DRAFT)
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=GuideApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create guide application",
    description=(
        "Creates a new guide application in DRAFT status for the authenticated user. "
        "A user may only have one application at a time. "
        "Submit it with POST /apply/{id}/submit when ready."
    ),
)
async def create_application(
    payload: GuideApplicationCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideApplicationService = Depends(get_guide_application_service),
) -> GuideApplicationResponse:
    user_id = UUID(current_user["sub"])
    return await service.create_application(payload, user_id)


# ---------------------------------------------------------------------------
# GET /api/v1/guides/apply — get the current user's application
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=GuideApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get own guide application",
    description="Returns the authenticated user's guide application. 404 if none exists.",
)
async def get_my_application(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideApplicationService = Depends(get_guide_application_service),
) -> GuideApplicationResponse:
    user_id = UUID(current_user["sub"])
    return await service.get_my_application(user_id)


# ---------------------------------------------------------------------------
# PATCH /api/v1/guides/apply/{application_id} — update DRAFT application
# ---------------------------------------------------------------------------

@router.patch(
    "/{application_id}",
    response_model=GuideApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update DRAFT application",
    description=(
        "Updates a DRAFT application. Only allowed while status is DRAFT. "
        "The owner may update biography, areas, languages, experience, "
        "certifications, and identity_document_url."
    ),
)
async def update_application(
    application_id: UUID,
    payload: GuideApplicationUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideApplicationService = Depends(get_guide_application_service),
) -> GuideApplicationResponse:
    user_id = UUID(current_user["sub"])
    return await service.update_application(application_id, payload, user_id)


# ---------------------------------------------------------------------------
# POST /api/v1/guides/apply/{application_id}/submit — submit DRAFT → SUBMITTED
# ---------------------------------------------------------------------------

@router.post(
    "/{application_id}/submit",
    response_model=GuideApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit application for review",
    description=(
        "Transitions the application from DRAFT to SUBMITTED. "
        "Once submitted, the application is queued for admin review "
        "and can no longer be edited."
    ),
)
async def submit_application(
    application_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideApplicationService = Depends(get_guide_application_service),
) -> GuideApplicationResponse:
    user_id = UUID(current_user["sub"])
    return await service.submit_application(application_id, user_id)


# ---------------------------------------------------------------------------
# POST /api/v1/guides/apply/{application_id}/review — admin status transition
# ---------------------------------------------------------------------------

@router.post(
    "/{application_id}/review",
    response_model=GuideApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin: review an application",
    description=(
        "Admin-only. Transitions an application to UNDER_REVIEW, APPROVED, or REJECTED. "
        "On APPROVED a GuideProfile is automatically created for the applicant. "
        "review_notes is optional but recommended when rejecting."
    ),
)
async def admin_review_application(
    application_id: UUID,
    new_status: ApplicationStatus,
    review_notes: Optional[str] = Body(default=None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideApplicationService = Depends(get_guide_application_service),
) -> GuideApplicationResponse:
    admin_id = UUID(current_user["sub"])
    return await service.admin_transition_status(
        application_id, new_status, admin_id, review_notes
    )
