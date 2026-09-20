"""
Community Service — Community Repository

Async repository for the Community entity with CRUD and query operations.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Any

from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Community, CommunityMember
from app.schemas.community import CommunityQueryParams
from shared.constants.status import CommunityStatus, CommunityVisibility, MemberRole, MembershipStatus


def _slugify(name: str) -> str:
    """Convert a community name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug


class CommunityRepository:
    """Repository for Community entity CRUD and query operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    async def create(
        self,
        creator_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        visibility: CommunityVisibility = CommunityVisibility.PUBLIC,
        requires_approval: bool = False,
        created_by: Optional[uuid.UUID] = None,
    ) -> Community:
        """Create a new community and add the creator as OWNER member."""

        # Generate unique slug
        base_slug = _slugify(name)
        slug = await self._unique_slug(base_slug)

        community = Community(
            creator_id=creator_id,
            name=name.strip(),
            slug=slug,
            description=description,
            location=location,
            visibility=visibility,
            requires_approval=requires_approval,
            member_count=1,  # creator counts
            created_by=created_by,
            updated_by=created_by,
        )

        self.session.add(community)
        await self.session.flush()  # Get the ID

        # Add creator as OWNER member
        owner_member = CommunityMember(
            community_id=community.id,
            user_id=creator_id,
            role=MemberRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        self.session.add(owner_member)

        await self.session.commit()
        await self.session.refresh(community, ["rules"])
        return community

    async def get_by_id(
        self,
        community_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[Community]:
        """Get community by ID with rules loaded."""
        query = (
            select(Community)
            .options(selectinload(Community.rules))
            .where(Community.id == community_id)
        )
        if not include_deleted:
            query = query.where(Community.is_deleted == False)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Community]:
        """Get community by URL slug."""
        query = (
            select(Community)
            .options(selectinload(Community.rules))
            .where(
                and_(
                    Community.slug == slug,
                    Community.is_deleted == False,
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update(
        self,
        community_id: uuid.UUID,
        **updates: Any,
    ) -> Optional[Community]:
        """Update community fields."""
        if not updates:
            return await self.get_by_id(community_id)

        updates["updated_at"] = datetime.now(timezone.utc)

        query = (
            update(Community)
            .where(
                and_(
                    Community.id == community_id,
                    Community.is_deleted == False,
                )
            )
            .values(**updates)
        )
        result = await self.session.execute(query)
        if result.rowcount == 0:
            return None

        await self.session.commit()
        return await self.get_by_id(community_id)

    async def soft_delete(
        self,
        community_id: uuid.UUID,
        deleted_by: Optional[uuid.UUID] = None,
    ) -> bool:
        """Soft delete a community."""
        query = (
            update(Community)
            .where(
                and_(
                    Community.id == community_id,
                    Community.is_deleted == False,
                )
            )
            .values(
                is_deleted=True,
                deleted_at=datetime.now(timezone.utc),
                deleted_by=deleted_by,
                status=CommunityStatus.DELETED,
            )
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0

    async def update_member_count(
        self,
        community_id: uuid.UUID,
        delta: int,
    ) -> None:
        """Increment or decrement the denormalized member_count."""
        from sqlalchemy import text

        await self.session.execute(
            update(Community)
            .where(Community.id == community_id)
            .values(member_count=Community.member_count + delta)
        )

    # -------------------------------------------------------------------------
    # Listing & Search
    # -------------------------------------------------------------------------

    async def list_communities(
        self,
        params: CommunityQueryParams,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> Tuple[List[Community], int]:
        """List communities with filtering and pagination."""

        # Only show active, non-deleted communities
        base_filter = and_(
            Community.is_deleted == False,
            Community.status == CommunityStatus.ACTIVE,
        )

        # Unauthenticated users see only PUBLIC communities
        if not current_user_id:
            base_filter = and_(
                base_filter,
                Community.visibility == CommunityVisibility.PUBLIC,
            )

        query = select(Community).where(base_filter)
        count_query = select(func.count(Community.id)).where(base_filter)

        # Optional filters
        if params.location:
            f = Community.location.ilike(f"%{params.location}%")
            query = query.where(f)
            count_query = count_query.where(f)

        if params.visibility:
            f = Community.visibility == params.visibility
            query = query.where(f)
            count_query = count_query.where(f)

        if params.search:
            f = or_(
                Community.name.ilike(f"%{params.search}%"),
                Community.description.ilike(f"%{params.search}%"),
            )
            query = query.where(f)
            count_query = count_query.where(f)

        # Ordering
        query = query.order_by(desc(Community.created_at))

        # Pagination
        query = query.limit(params.limit).offset(params.offset)

        communities_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)

        return communities_result.scalars().all(), count_result.scalar()

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    async def _unique_slug(self, base_slug: str) -> str:
        """Return a unique slug, appending a numeric suffix if needed."""
        slug = base_slug
        suffix = 1
        while True:
            existing = await self.session.execute(
                select(Community.id).where(Community.slug == slug)
            )
            if existing.scalar_one_or_none() is None:
                return slug
            slug = f"{base_slug}-{suffix}"
            suffix += 1

    async def update_logo(
        self,
        community_id: uuid.UUID,
        logo_url: str,
        logo_object_key: str,
        updated_by: Optional[uuid.UUID] = None,
    ) -> Optional[Community]:
        return await self.update(
            community_id,
            logo_url=logo_url,
            logo_object_key=logo_object_key,
            updated_by=updated_by,
        )

    async def update_banner(
        self,
        community_id: uuid.UUID,
        banner_url: str,
        banner_object_key: str,
        updated_by: Optional[uuid.UUID] = None,
    ) -> Optional[Community]:
        return await self.update(
            community_id,
            banner_url=banner_url,
            banner_object_key=banner_object_key,
            updated_by=updated_by,
        )
