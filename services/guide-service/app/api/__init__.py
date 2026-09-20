"""
API package — aggregates all versioned routers into a single router
that main.py includes on the FastAPI app.

Router order matters for path matching:
  - /my-connections and /apply must be included before /{guide_id}
    to prevent FastAPI treating them as UUID path parameters.
"""

from fastapi import APIRouter

from app.api.v1.travel_connections import router as travel_connections_router
from app.api.v1.guide_applications import router as guide_applications_router
from app.api.v1.guides import router as guides_router
from app.api.v1.guide_locations import router as guide_locations_router
from app.api.v1.guide_languages import router as guide_languages_router
from app.api.v1.guide_availability import router as guide_availability_router
from app.api.v1.guide_reviews import router as guide_reviews_router
from app.api.v1.guide_specializations import router as guide_specializations_router

# Single router that main.py includes — keeps main.py clean
router = APIRouter()

# Fixed-path routers first, then parameterised ones
router.include_router(travel_connections_router)
router.include_router(guide_applications_router)
router.include_router(guides_router)
router.include_router(guide_locations_router)
router.include_router(guide_languages_router)
router.include_router(guide_availability_router)
router.include_router(guide_reviews_router)
router.include_router(guide_specializations_router)
