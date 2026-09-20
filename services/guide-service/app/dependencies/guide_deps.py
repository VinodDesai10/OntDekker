"""
Guide Service — FastAPI dependency injection factories.

Every service class is constructed here using FastAPI's `Depends` system.
Routers never instantiate repositories or services directly — they declare
them as function parameters using `Depends(get_xxx_service)`.

This keeps routers thin and makes services trivially testable:
override the dependency in tests to inject mocks.

Pattern:
  1. get_db (from shared) → AsyncSession
  2. get_xxx_repository(session) → XxxRepository
  3. get_xxx_service(repo_a, repo_b) → XxxService
  4. Router parameter: service = Depends(get_xxx_service)
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.dependencies import get_db

from app.repositories.guide_profile_repository import GuideProfileRepository
from app.repositories.guide_application_repository import GuideApplicationRepository
from app.repositories.guide_location_repository import GuideLocationRepository
from app.repositories.guide_language_repository import GuideLanguageRepository
from app.repositories.guide_availability_repository import GuideAvailabilityRepository
from app.repositories.guide_review_repository import GuideReviewRepository
from app.repositories.travel_connection_repository import TravelConnectionRepository

from app.services.guide_profile_service import GuideProfileService
from app.services.guide_application_service import GuideApplicationService
from app.services.guide_location_service import GuideLocationService
from app.services.guide_language_service import GuideLanguageService
from app.services.guide_availability_service import GuideAvailabilityService
from app.services.guide_review_service import GuideReviewService
from app.services.travel_connection_service import TravelConnectionService


# ---------------------------------------------------------------------------
# Repository factories
# ---------------------------------------------------------------------------

def get_guide_profile_repository(
    session: AsyncSession = Depends(get_db),
) -> GuideProfileRepository:
    return GuideProfileRepository(session)


def get_guide_application_repository(
    session: AsyncSession = Depends(get_db),
) -> GuideApplicationRepository:
    return GuideApplicationRepository(session)


def get_guide_location_repository(
    session: AsyncSession = Depends(get_db),
) -> GuideLocationRepository:
    return GuideLocationRepository(session)


def get_guide_language_repository(
    session: AsyncSession = Depends(get_db),
) -> GuideLanguageRepository:
    return GuideLanguageRepository(session)


def get_guide_availability_repository(
    session: AsyncSession = Depends(get_db),
) -> GuideAvailabilityRepository:
    return GuideAvailabilityRepository(session)


def get_guide_review_repository(
    session: AsyncSession = Depends(get_db),
) -> GuideReviewRepository:
    return GuideReviewRepository(session)


def get_travel_connection_repository(
    session: AsyncSession = Depends(get_db),
) -> TravelConnectionRepository:
    return TravelConnectionRepository(session)


# ---------------------------------------------------------------------------
# Service factories
# ---------------------------------------------------------------------------

def get_guide_profile_service(
    profile_repo: GuideProfileRepository = Depends(get_guide_profile_repository),
) -> GuideProfileService:
    return GuideProfileService(profile_repo)


def get_guide_application_service(
    application_repo: GuideApplicationRepository = Depends(get_guide_application_repository),
    profile_repo: GuideProfileRepository = Depends(get_guide_profile_repository),
) -> GuideApplicationService:
    return GuideApplicationService(application_repo, profile_repo)


def get_guide_location_service(
    profile_repo: GuideProfileRepository = Depends(get_guide_profile_repository),
    location_repo: GuideLocationRepository = Depends(get_guide_location_repository),
) -> GuideLocationService:
    return GuideLocationService(profile_repo, location_repo)


def get_guide_language_service(
    profile_repo: GuideProfileRepository = Depends(get_guide_profile_repository),
    language_repo: GuideLanguageRepository = Depends(get_guide_language_repository),
) -> GuideLanguageService:
    return GuideLanguageService(profile_repo, language_repo)


def get_guide_availability_service(
    profile_repo: GuideProfileRepository = Depends(get_guide_profile_repository),
    availability_repo: GuideAvailabilityRepository = Depends(get_guide_availability_repository),
) -> GuideAvailabilityService:
    return GuideAvailabilityService(profile_repo, availability_repo)


def get_guide_review_service(
    profile_repo: GuideProfileRepository = Depends(get_guide_profile_repository),
    review_repo: GuideReviewRepository = Depends(get_guide_review_repository),
) -> GuideReviewService:
    return GuideReviewService(profile_repo, review_repo)


def get_travel_connection_service(
    profile_repo: GuideProfileRepository = Depends(get_guide_profile_repository),
    connection_repo: TravelConnectionRepository = Depends(get_travel_connection_repository),
) -> TravelConnectionService:
    return TravelConnectionService(profile_repo, connection_repo)
