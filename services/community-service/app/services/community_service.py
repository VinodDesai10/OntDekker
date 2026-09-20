"""
Community Service — Community Business Logic

Service class that orchestrates community lifecycle operations:
create, get, update, archive, soft-delete, and list.
"""

import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Community
from app.repositories import CommunityRepository, MembershipRepository
from app.schemas.community import (
    CommunityCreateRequest,
    CommunityUpdateRequest,
    CommunitySchema,
    CommunitySummarySchema,
    CommunityListResponse,
    CommunityQueryParams,
)
from shared.constants.status import (
    CommunityStatus,
    CommunityVisibility,
    MemberRole,
    MembershipStatus,
)
from shared.exceptions import NotFoundError, ForbiddenError, ValidationError, ConflictError


class CommunityService:
    """Business logic for community lifecycle management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.community_repo = CommunityRepository(session)
        self.membership_repo = MembershipRepository(session)

    # -------------------------------------------------------------------------
    # Create
    # -------------------------------------------------------------------------

    async def create_community(
        self,
        request: CommunityCreateRequest,
        creator_id: uuid.UUID,
    ) -> CommunitySchema:
        """Create a new community and automatically add the creator as OWNER."""
        community = await self.community_repo.create(
            creator_id=creator_id,
            name=request.name,
            description=request.description,
            location=request.location,
            visibility=request.visibility,
            requires_approval=request.requires_approval,
            created_by=creator_id,
        )
        # NOTE: community_repo.create() already calls session.commit() internally.
        # Do NOT call session.commit() here — a second commit on a closed
        # transaction raises sqlalchemy.exc.InvalidRequestError → HTTP 500.
        return await self._to_schema(community, creator_id)

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    async def get_community(
        self,
        community_id: uuid.UUID,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> CommunitySchema:
        """Get a community by ID with viewer context enrichment."""
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise NotFoundError(f"Community {community_id} not found")

        # Private communities are only visible to members
        if community.visibility == CommunityVisibility.PRIVATE:
            if not current_user_id:
                raise ForbiddenError("This community is private")
            member = await self.membership_repo.get_active_member(community_id, current_user_id)
            if not member:
                raise ForbiddenError("You must be a member to view this community")

        return await self._to_schema(community, current_user_id)

    async def get_community_by_slug(
        self,
        slug: str,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> CommunitySchema:
        """Get a community by slug with viewer context enrichment."""
        community = await self.community_repo.get_by_slug(slug)
        if not community:
            raise NotFoundError(f"Community '{slug}' not found")

        if community.visibility == CommunityVisibility.PRIVATE:
            if not current_user_id:
                raise ForbiddenError("This community is private")
            member = await self.membership_repo.get_active_member(community.id, current_user_id)
            if not member:
                raise ForbiddenError("You must be a member to view this community")

        return await self._to_schema(community, current_user_id)

    async def list_communities(
        self,
        params: CommunityQueryParams,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> CommunityListResponse:
        """List communities with filtering and pagination."""
        communities, total = await self.community_repo.list_communities(params, current_user_id)

        summaries = []
        for community in communities:
            is_member = False
            if current_user_id:
                member = await self.membership_repo.get_active_member(community.id, current_user_id)
                is_member = member is not None
            summaries.append(CommunitySummarySchema(
                id=community.id,
                creator_id=community.creator_id,
                name=community.name,
                slug=community.slug,
                description=community.description,
                location=community.location,
                logo_url=community.logo_url,
                status=community.status,
                visibility=community.visibility,
                requires_approval=community.requires_approval,
                member_count=community.member_count,
                is_member=is_member,
                created_at=community.created_at,
                updated_at=community.updated_at,
            ))

        return CommunityListResponse(
            communities=summaries,
            total=total,
            limit=params.limit,
            offset=params.offset,
            has_more=len(summaries) == params.limit and params.offset + len(summaries) < total,
        )

    # -------------------------------------------------------------------------
    # Update
    # -------------------------------------------------------------------------

    async def update_community(
        self,
        community_id: uuid.UUID,
        request: CommunityUpdateRequest,
        current_user_id: uuid.UUID,
    ) -> CommunitySchema:
        """Update a community — OWNER only."""
        community = await self._get_or_404(community_id)
        await self._require_owner(community_id, current_user_id)

        updates = {k: v for k, v in request.model_dump(exclude_unset=True).items() if v is not None}
        updates["updated_by"] = current_user_id

        if not updates:
            return await self._to_schema(community, current_user_id)

        updated = await self.community_repo.update(community_id, **updates)
        await self.session.commit()
        return await self._to_schema(updated, current_user_id)

    # -------------------------------------------------------------------------
    # Delete / Archive
    # -------------------------------------------------------------------------

    async def delete_community(
        self,
        community_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> bool:
        """Soft delete a community — OWNER only."""
        await self._get_or_404(community_id)
        await self._require_owner(community_id, current_user_id)

        result = await self.community_repo.soft_delete(community_id, deleted_by=current_user_id)
        await self.session.commit()
        return result

    async def archive_community(
        self,
        community_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> CommunitySchema:
        """Archive a community (status=ARCHIVED) — OWNER only."""
        await self._get_or_404(community_id)
        await self._require_owner(community_id, current_user_id)

        updated = await self.community_repo.update(
            community_id,
            status=CommunityStatus.ARCHIVED,
            updated_by=current_user_id,
        )
        await self.session.commit()
        return await self._to_schema(updated, current_user_id)

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    async def _get_or_404(self, community_id: uuid.UUID) -> Community:
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise NotFoundError(f"Community {community_id} not found")
        return community

    async def _require_owner(
        self,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        member = await self.membership_repo.get_active_member(community_id, user_id)
        if not member or member.role != MemberRole.OWNER:
            raise ForbiddenError("Only the community owner can perform this action")

    async def _to_schema(
        self,
        community: Community,
        current_user_id: Optional[uuid.UUID],
    ) -> CommunitySchema:
        """Convert Community ORM model to CommunitySchema with viewer context."""
        from app.schemas.community import CommunityRuleSchema, MembershipViewStatus
        from shared.constants.status import JoinRequestStatus

        current_user_role = None
        is_member = False
        membership_status = MembershipViewStatus.NOT_MEMBER

        if current_user_id:
            member = await self.membership_repo.get_active_member(community.id, current_user_id)
            if member:
                is_member = True
                current_user_role = member.role
                if member.role == MemberRole.OWNER:
                    membership_status = MembershipViewStatus.HEAD
                elif member.role == MemberRole.MODERATOR:
                    membership_status = MembershipViewStatus.CO_HEAD
                else:
                    membership_status = MembershipViewStatus.MEMBER
            else:
                # Check for a pending join request
                pending = await self.membership_repo.get_pending_join_request(
                    community.id, current_user_id
                )
                if pending:
                    membership_status = MembershipViewStatus.PENDING

        rules = [
            CommunityRuleSchema.model_validate(rule)
            for rule in (community.rules or [])
        ]

        return CommunitySchema(
            id=community.id,
            creator_id=community.creator_id,
            name=community.name,
            slug=community.slug,
            description=community.description,
            location=community.location,
            logo_url=community.logo_url,
            banner_url=community.banner_url,
            status=community.status,
            visibility=community.visibility,
            requires_approval=community.requires_approval,
            member_count=community.member_count,
            is_deleted=community.is_deleted,
            rules=rules,
            current_user_role=current_user_role,
            is_member=is_member,
            membership_status=membership_status,
            created_at=community.created_at,
            updated_at=community.updated_at,
            created_by=community.created_by,
            updated_by=community.updated_by,
        )
