"""User Service — FastAPI dependency injection."""

from typing import Any, Dict, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user import UserService
from shared.dependencies import get_current_user, get_optional_current_user, get_db


async def get_user_service(
    session: AsyncSession = Depends(get_db),
) -> UserService:
    return UserService(session=session)


async def get_current_user_payload(
    payload: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    return payload


async def get_optional_current_user_payload(
    payload: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
) -> Optional[Dict[str, Any]]:
    """
    Optional JWT dependency for public endpoints.

    Returns the validated JWT payload when the caller is authenticated,
    or None when the request is unauthenticated or carries an invalid token.
    Never raises — preserves public endpoint accessibility.
    """
    return payload
