"""
Community Service — Community CRUD API Endpoints

Routes under /api/v1/communities for community lifecycle management.
"""

import uuid
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import CommunityService
from app.schemas.community import (
    CommunityCreateRequest,
    CommunityUpdateRequest,
    CommunitySchema,
    CommunityListResponse,
    CommunityQueryParams,
    CommunityRuleCreateRequest,
    CommunityRuleUpdateRequest,
    CommunityRuleSchema,
    CommunityRuleListResponse,
)
from shared.dependencies import get_current_user, optional_current_user, get_db
from shared.exceptions import NotFoundError, ForbiddenError, ValidationError, ConflictError

router = APIRouter(tags=["Communities"])


def _user_id(payload: Dict[str, Any]) -> uuid.UUID:
    """Extract user UUID from JWT payload sub claim."""
    return uuid.UUID(payload["sub"])


# ---------------------------------------------------------------------------
# Community CRUD
# ---------------------------------------------------------------------------

@router.post("/", response_model=CommunitySchema, status_code=status.HTTP_201_CREATED)
async def create_community(
    request: CommunityCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new community. The authenticated user becomes the OWNER."""
    service = CommunityService(db)
    try:
        return await service.create_community(request, _user_id(current_user))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=CommunityListResponse)
async def list_communities(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, max_length=100),
    location: Optional[str] = Query(None),
    visibility: Optional[str] = Query(None),
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List communities with optional search, location, and visibility filters."""
    from shared.constants.status import CommunityVisibility
    vis = CommunityVisibility(visibility) if visibility else None

    params = CommunityQueryParams(
        limit=limit,
        offset=offset,
        search=search,
        location=location,
        visibility=vis,
    )
    service = CommunityService(db)
    user_id = _user_id(current_user) if current_user else None
    return await service.list_communities(params, user_id)


@router.get("/{community_id}", response_model=CommunitySchema)
async def get_community(
    community_id: uuid.UUID,
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a community by ID."""
    service = CommunityService(db)
    try:
        user_id = _user_id(current_user) if current_user else None
        return await service.get_community(community_id, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/{community_id}", response_model=CommunitySchema)
async def update_community(
    community_id: uuid.UUID,
    request: CommunityUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a community — OWNER only."""
    service = CommunityService(db)
    try:
        return await service.update_community(community_id, request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{community_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_community(
    community_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a community — OWNER only."""
    service = CommunityService(db)
    try:
        success = await service.delete_community(community_id, _user_id(current_user))
        if not success:
            raise HTTPException(status_code=404, detail="Community not found")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------------------------------------------------------------------------
# Community Rules  (nested under /communities/{community_id}/rules)
# ---------------------------------------------------------------------------

@router.get("/{community_id}/rules", response_model=CommunityRuleListResponse)
async def list_rules(
    community_id: uuid.UUID,
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List rules for a community."""
    from app.repositories import CommunityRepository
    repo = CommunityRepository(db)
    community = await repo.get_by_id(community_id)
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    rules = community.rules or []
    return CommunityRuleListResponse(
        rules=[CommunityRuleSchema.model_validate(r) for r in rules],
        total=len(rules),
    )


@router.post(
    "/{community_id}/rules",
    response_model=CommunityRuleSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_rule(
    community_id: uuid.UUID,
    request: CommunityRuleCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a rule to a community — MOD or OWNER only."""
    from app.repositories import CommunityRepository, MembershipRepository
    from shared.constants.status import MemberRole
    from app.models import CommunityRule

    community_repo = CommunityRepository(db)
    membership_repo = MembershipRepository(db)

    community = await community_repo.get_by_id(community_id)
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")

    member = await membership_repo.get_active_member(community_id, _user_id(current_user))
    if not member or member.role not in (MemberRole.OWNER, MemberRole.MODERATOR):
        raise HTTPException(status_code=403, detail="Only moderators or owner can add rules")

    rule = CommunityRule(
        community_id=community_id,
        title=request.title,
        description=request.description,
        order_index=request.order_index,
        created_by=_user_id(current_user),
        updated_by=_user_id(current_user),
    )
    db.add(rule)
    await db.flush()
    await db.commit()
    await db.refresh(rule)
    return CommunityRuleSchema.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=CommunityRuleSchema)
async def update_rule(
    rule_id: uuid.UUID,
    request: CommunityRuleUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a community rule — MOD or OWNER only."""
    from sqlalchemy import select, update as sa_update
    from app.models import CommunityRule
    from app.repositories import MembershipRepository
    from shared.constants.status import MemberRole
    from datetime import datetime, timezone

    result = await db.execute(select(CommunityRule).where(CommunityRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    membership_repo = MembershipRepository(db)
    member = await membership_repo.get_active_member(rule.community_id, _user_id(current_user))
    if not member or member.role not in (MemberRole.OWNER, MemberRole.MODERATOR):
        raise HTTPException(status_code=403, detail="Only moderators or owner can edit rules")

    updates = {k: v for k, v in request.model_dump(exclude_unset=True).items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc)
    updates["updated_by"] = _user_id(current_user)

    await db.execute(
        sa_update(CommunityRule).where(CommunityRule.id == rule_id).values(**updates)
    )
    await db.commit()

    result = await db.execute(select(CommunityRule).where(CommunityRule.id == rule_id))
    updated_rule = result.scalar_one()
    return CommunityRuleSchema.model_validate(updated_rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a community rule — MOD or OWNER only."""
    from sqlalchemy import select, delete as sa_delete
    from app.models import CommunityRule
    from app.repositories import MembershipRepository
    from shared.constants.status import MemberRole

    result = await db.execute(select(CommunityRule).where(CommunityRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    membership_repo = MembershipRepository(db)
    member = await membership_repo.get_active_member(rule.community_id, _user_id(current_user))
    if not member or member.role not in (MemberRole.OWNER, MemberRole.MODERATOR):
        raise HTTPException(status_code=403, detail="Only moderators or owner can delete rules")

    await db.execute(sa_delete(CommunityRule).where(CommunityRule.id == rule_id))
    await db.commit()
