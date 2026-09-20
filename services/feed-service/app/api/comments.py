"""
Feed Service — Comment API Routes

Comment endpoints have been consolidated into posts.py for route co-location.
This module is kept for structural consistency and future comment-only endpoints.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/feed", tags=["Comments"])
