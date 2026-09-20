"""
Feed Service — Main API Router

Combines all API routers and provides the main FastAPI router for the service.
"""

from fastapi import APIRouter
from .posts import router as posts_router
from .interactions import router as interactions_router  
from .comments import router as comments_router
from .media import router as media_router

# Create main router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(posts_router)
api_router.include_router(interactions_router)
api_router.include_router(comments_router)
api_router.include_router(media_router)

__all__ = ["api_router"]