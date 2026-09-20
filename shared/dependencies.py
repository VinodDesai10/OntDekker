from fastapi import Request, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from typing import AsyncGenerator, Optional, Dict, Any
import uuid

from shared.exceptions import (
    OntDekkerException,
    UnauthorizedException,
    ForbiddenException,
)
from shared.utils.security import decode_jwt_token
from shared.logging import request_id_ctx, correlation_id_ctx
from shared.config import get_common_settings


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        raise RuntimeError("Database sessionmaker is not configured on app state.")

    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except OntDekkerException:
            await session.commit()
            raise
        except Exception:
            await session.rollback()
            raise


async def get_request_id(
    x_request_id: Optional[str] = Header(None),
    x_correlation_id: Optional[str] = Header(None),
) -> None:
    req_id = x_request_id or str(uuid.uuid4())
    corr_id = x_correlation_id or req_id

    request_id_ctx.set(req_id)
    correlation_id_ctx.set(corr_id)


async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException("Missing or invalid authorization header.")

    token = authorization.split(" ")[1]
    settings = get_common_settings()
    try:
        payload = decode_jwt_token(token, settings.JWT_SECRET, settings.JWT_ALGORITHM)
        return payload
    except JWTError:
        raise UnauthorizedException("Invalid or expired authentication token.")


async def get_optional_current_user(
    authorization: Optional[str] = Header(None),
) -> Optional[Dict[str, Any]]:
    """
    Returns the JWT payload if a valid Bearer token is present, None otherwise.
    Does NOT raise — safe to use on endpoints that work for both authenticated
    and anonymous users.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ")[1]
    settings = get_common_settings()
    try:
        payload = decode_jwt_token(token, settings.JWT_SECRET, settings.JWT_ALGORITHM)
        return payload
    except JWTError:
        return None


# Alias for backward compatibility across services
optional_current_user = get_optional_current_user


def require_role(required_role: str):
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_roles = current_user.get("roles", [])
        if required_role not in user_roles:
            raise ForbiddenException("Insufficient permissions to access this resource.")
        return current_user

    return role_checker
