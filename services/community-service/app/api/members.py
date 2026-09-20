"""
Community Service — Membership API Endpoints

Routes for join, leave, member management, and join-request handling.
All paths are prefixed by /api/v1/communities in routes.py.
"""

import uuid
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import MembershipService
from app.schemas.community import (
    JoinCommunityRequest,
    JoinRequestActionRequest,
    MemberRoleUpdateRequest,
    MemberListResponse,
    JoinRequestListResponse,
    MemberQueryParams,
)
from shared.dependencies import get_current_user, optional_current_user, get_db
from shared.exceptions import NotFoundError, ForbiddenError, ValidationError, ConflictError

router = APIRouter(tags=["Members"])


def _user_id(payload: Dict[str, Any]) -> uuid.UUID:
    return uuid.UUID(payload["sub"])


# ---------------------------------------------------------------------------
# Join / Leave
# ---------------------------------------------------------------------------

@router.post("/{community_id}/join", status_code=status.HTTP_200_OK)
async def join_community(
    community_id: uuid.UUID,
    request: JoinCommunityRequest = JoinCommunityRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Join a community.

    - Public (no approval required): returns `{"joined": true}`
    - Private or approval required: returns `{"requested": true, "request_id": "..."}`
    """
    service = MembershipService(db)
    try:
        return await service.join_community(community_id, request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{community_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_community(
    community_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Leave a community. The owner cannot leave without transferring ownership."""
    service = MembershipService(db)
    try:
        await service.leave_community(community_id, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Member listing and management
# ---------------------------------------------------------------------------

@router.get("/{community_id}/members", response_model=MemberListResponse)
async def list_members(
    community_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    role: Optional[str] = Query(None),
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active members of a community."""
    from shared.constants.status import MemberRole
    role_filter = MemberRole(role) if role else None

    params = MemberQueryParams(limit=limit, offset=offset, role=role_filter)
    service = MembershipService(db)
    try:
        user_id = _user_id(current_user) if current_user else None
        return await service.list_members(community_id, params, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{community_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    community_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the community — MOD or OWNER only."""
    service = MembershipService(db)
    try:
        await service.remove_member(community_id, user_id, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/{community_id}/members/{user_id}/role")
async def update_member_role(
    community_id: uuid.UUID,
    user_id: uuid.UUID,
    request: MemberRoleUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a member's role — OWNER only."""
    service = MembershipService(db)
    try:
        return await service.update_member_role(
            community_id, user_id, request, _user_id(current_user)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Join Requests
# ---------------------------------------------------------------------------

@router.get("/{community_id}/join-requests", response_model=JoinRequestListResponse)
async def list_join_requests(
    community_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List pending join requests — MOD or OWNER only."""
    service = MembershipService(db)
    try:
        return await service.list_join_requests(
            community_id, _user_id(current_user), limit, offset
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/join-requests/{request_id}")
async def action_join_request(
    request_id: uuid.UUID,
    request: JoinRequestActionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a join request — MOD or OWNER only."""
    service = MembershipService(db)
    try:
        return await service.action_join_request(request_id, request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/join-requests/{request_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_join_request(
    request_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel your own pending join request.
    Only the original requester can cancel.  Returns 204 on success.
    """
    service = MembershipService(db)
    try:
        await service.cancel_join_request(request_id, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
