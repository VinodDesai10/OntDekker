"""
Community Service — API Router Aggregation

Combines all community sub-routers into a single APIRouter that main.py
includes under the canonical prefix /api/v1/communities.
"""

from fastapi import APIRouter

from .communities import router as community_router
from .members import router as members_router
from .discussions import router as discussions_router
from .media import router as media_router

# Aggregate router — main.py includes this with prefix=/api/v1/communities
api_router = APIRouter()

api_router.include_router(community_router)
api_router.include_router(members_router)
api_router.include_router(discussions_router)
api_router.include_router(media_router)

__all__ = ["api_router"]
