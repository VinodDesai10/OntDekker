"""
Guide Languages router — spoken languages sub-resource.

Routes: /api/v1/guides/{guide_id}/languages

Endpoints:
  GET    /api/v1/guides/{guide_id}/languages               — list all languages
  POST   /api/v1/guides/{guide_id}/languages               — add a language
  DELETE /api/v1/guides/{guide_id}/languages/{language_id} — remove a language
"""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from shared.dependencies import get_current_user

from app.dependencies.guide_deps import get_guide_language_service
from app.schemas.guide_language import GuideLanguageCreate, GuideLanguageResponse
from app.services.guide_language_service import GuideLanguageService

router = APIRouter(
    prefix="/api/v1/guides",
    tags=["Guide Languages"],
)


# ---------------------------------------------------------------------------
# GET /api/v1/guides/{guide_id}/languages
# ---------------------------------------------------------------------------

@router.get(
    "/{guide_id}/languages",
    response_model=List[GuideLanguageResponse],
    status_code=status.HTTP_200_OK,
    summary="List guide languages",
    description="Returns all languages spoken by a guide. Publicly readable.",
)
async def list_languages(
    guide_id: UUID,
    service: GuideLanguageService = Depends(get_guide_language_service),
) -> List[GuideLanguageResponse]:
    return await service.list_languages(guide_id)


# ---------------------------------------------------------------------------
# POST /api/v1/guides/{guide_id}/languages
# ---------------------------------------------------------------------------

@router.post(
    "/{guide_id}/languages",
    response_model=GuideLanguageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a language",
    description=(
        "Adds a spoken language to the guide's profile. "
        "Language name is normalised to title-case (e.g. 'hindi' → 'Hindi'). "
        "Guide owner only."
    ),
)
async def add_language(
    guide_id: UUID,
    payload: GuideLanguageCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideLanguageService = Depends(get_guide_language_service),
) -> GuideLanguageResponse:
    user_id = UUID(current_user["sub"])
    return await service.add_language(guide_id, payload, user_id)


# ---------------------------------------------------------------------------
# DELETE /api/v1/guides/{guide_id}/languages/{language_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{guide_id}/languages/{language_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a language",
    description="Removes a language from the guide's profile. Guide owner only.",
)
async def delete_language(
    guide_id: UUID,
    language_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: GuideLanguageService = Depends(get_guide_language_service),
) -> None:
    user_id = UUID(current_user["sub"])
    await service.delete_language(guide_id, language_id, user_id)
