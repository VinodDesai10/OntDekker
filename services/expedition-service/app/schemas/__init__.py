# schemas package — centralised exports
#
# Import everything here so routers and services can do:
#     from app.schemas import ExpeditionCreate, ExpeditionResponse, ...
# instead of importing from individual submodules.
#
# Import order: common first (no deps), then domain schemas alphabetically.

# ---------------------------------------------------------------------------
# Common / shared
# ---------------------------------------------------------------------------
from app.schemas.common import (
    ApiResponse,
    ExpeditionFilter,
    PaginatedResponse,
    PaginationMeta,
)

# ---------------------------------------------------------------------------
# Expedition
# ---------------------------------------------------------------------------
from app.schemas.expedition import (
    ExpeditionBase,
    ExpeditionCreate,
    ExpeditionResponse,
    ExpeditionSummary,
    ExpeditionUpdate,
)

# ---------------------------------------------------------------------------
# Participant
# ---------------------------------------------------------------------------
from app.schemas.participant import (
    ParticipantResponse,
    ParticipantRoleUpdate,
)

# ---------------------------------------------------------------------------
# Join request
# ---------------------------------------------------------------------------
from app.schemas.join_request import (
    JoinRequestCreate,
    JoinRequestDecision,
    JoinRequestResponse,
)

# ---------------------------------------------------------------------------
# Itinerary
# ---------------------------------------------------------------------------
from app.schemas.itinerary import (
    ItineraryBulkUpdate,
    ItineraryDayCreate,
    ItineraryDayResponse,
    ItineraryDayUpdate,
    ItineraryResponse,
)

# ---------------------------------------------------------------------------
# Gallery
# ---------------------------------------------------------------------------
from app.schemas.gallery import (
    GalleryPhotoCreate,
    GalleryPhotoResponse,
    GalleryPhotoUpdate,
    GalleryResponse,
)

# ---------------------------------------------------------------------------
# Gear / Pack Weight Optimizer
# ---------------------------------------------------------------------------
from app.schemas.gear_item import (
    GearItemCreate,
    GearItemResponse,
    GearItemUpdate,
    GearListResponse,
    PackWeightClassification,
    PackWeightSummary,
)

# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------
from app.schemas.review import (
    ReviewCreate,
    ReviewListResponse,
    ReviewResponse,
    ReviewSummary,
)

# ---------------------------------------------------------------------------
# Discussion
# ---------------------------------------------------------------------------
from app.schemas.discussion import (
    DiscussionMessageCreate,
    DiscussionMessageResponse,
    DiscussionListResponse,
)

__all__ = [
    # Common
    "ApiResponse",
    "ExpeditionFilter",
    "PaginatedResponse",
    "PaginationMeta",
    # Expedition
    "ExpeditionBase",
    "ExpeditionCreate",
    "ExpeditionResponse",
    "ExpeditionSummary",
    "ExpeditionUpdate",
    # Participant
    "ParticipantResponse",
    "ParticipantRoleUpdate",
    # Join request
    "JoinRequestCreate",
    "JoinRequestDecision",
    "JoinRequestResponse",
    # Itinerary
    "ItineraryBulkUpdate",
    "ItineraryDayCreate",
    "ItineraryDayResponse",
    "ItineraryDayUpdate",
    "ItineraryResponse",
    # Gallery
    "GalleryPhotoCreate",
    "GalleryPhotoResponse",
    "GalleryPhotoUpdate",
    "GalleryResponse",
    # Gear
    "GearItemCreate",
    "GearItemResponse",
    "GearItemUpdate",
    "GearListResponse",
    "PackWeightClassification",
    "PackWeightSummary",
    # Reviews
    "ReviewCreate",
    "ReviewListResponse",
    "ReviewResponse",
    "ReviewSummary",
    # Discussion
    "DiscussionMessageCreate",
    "DiscussionMessageResponse",
    "DiscussionListResponse",
]
