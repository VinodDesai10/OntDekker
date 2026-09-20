# schemas package — exports all Guide Service Pydantic schemas

from app.schemas.common import (
    PaginationMeta,
    PaginatedResponse,
    ApiResponse,
    GuideFilter,
)

from app.schemas.guide_profile import (
    GuideProfileUpdate,
    GuideProfileResponse,
    GuideProfileSummary,
)

from app.schemas.guide_application import (
    GuideApplicationCreate,
    GuideApplicationUpdate,
    GuideApplicationResponse,
)

from app.schemas.guide_location import (
    GuideLocationCreate,
    GuideLocationResponse,
)

from app.schemas.guide_language import (
    GuideLanguageCreate,
    GuideLanguageResponse,
)

from app.schemas.guide_availability import (
    GuideAvailabilityUpdate,
    GuideAvailabilityResponse,
)

from app.schemas.guide_review import (
    GuideReviewCreate,
    GuideReviewResponse,
    GuideRatingSummary,
    GuideReviewListResponse,
)

from app.schemas.travel_connection import (
    TravelConnectionResponse,
    TravelConnectionListResponse,
)

from app.schemas.guide_specialization import (
    GuideSpecializationCreate,
    GuideSpecializationResponse,
)

__all__ = [
    # Common
    "PaginationMeta",
    "PaginatedResponse",
    "ApiResponse",
    "GuideFilter",

    # Guide profile
    "GuideProfileUpdate",
    "GuideProfileResponse",
    "GuideProfileSummary",

    # Application
    "GuideApplicationCreate",
    "GuideApplicationUpdate",
    "GuideApplicationResponse",

    # Location
    "GuideLocationCreate",
    "GuideLocationResponse",

    # Language
    "GuideLanguageCreate",
    "GuideLanguageResponse",

    # Availability
    "GuideAvailabilityUpdate",
    "GuideAvailabilityResponse",

    # Reviews
    "GuideReviewCreate",
    "GuideReviewResponse",
    "GuideRatingSummary",
    "GuideReviewListResponse",

    # Travel connections
    "TravelConnectionResponse",
    "TravelConnectionListResponse",

    # Specializations
    "GuideSpecializationCreate",
    "GuideSpecializationResponse",
]
