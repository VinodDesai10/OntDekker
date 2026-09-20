"""
API package — aggregates all versioned routers into a single router
that main.py includes on the FastAPI app.

Every sub-router uses prefix="/api/v1/expeditions" so all expedition
endpoints are grouped under that prefix in Swagger UI.
"""

from fastapi import APIRouter

from app.api.v1.expeditions import router as expeditions_router
from app.api.v1.participants import router as participants_router
from app.api.v1.join_requests import router as join_requests_router
from app.api.v1.itinerary import router as itinerary_router
from app.api.v1.gallery import router as gallery_router
from app.api.v1.gear import router as gear_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.trips import router as trips_router  # MCP-1: trip-centric endpoints
from app.api.v1.discussion import router as discussion_router  # CP-TRIP-3A: discussion

# Single router that main.py includes — keeps main.py clean
router = APIRouter()

router.include_router(expeditions_router)
router.include_router(participants_router)
router.include_router(join_requests_router)
router.include_router(itinerary_router)
router.include_router(gallery_router)
router.include_router(gear_router)
router.include_router(reviews_router)
router.include_router(trips_router)
router.include_router(discussion_router)
