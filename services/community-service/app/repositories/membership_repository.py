"""
Community Service — Membership Repository

Async repository for CommunityMember and JoinRequest entities.
Handles all membership state transitions and join request lifecycle.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CommunityMember, JoinRequest
from shared.constants.status import (
    MemberRole,
    MembershipStatus,
    JoinRequestStatus,
)


class MembershipRepository:
    """Repository for CommunityMember and JoinRequest entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # CommunityMember — reads
    # -------------------------------------------------------------------------

    async def get_member(
        self,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[CommunityMember]:
        """Get the membership record for a user in a community (any status)."""
        result = await self.session.execute(
            select(CommunityMember).where(
                and_(
                    CommunityMember.community_id == community_id,
                    CommunityMember.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_active_member(
        self,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[CommunityMember]:
        """Get the membership record only if the user has ACTIVE status."""
        result = await self.session.execute(
            select(CommunityMember).where(
                and_(
                    CommunityMember.community_id == community_id,
                    CommunityMember.user_id == user_id,
                    CommunityMember.status == MembershipStatus.ACTIVE,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_members(
        self,
        community_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        role: Optional[MemberRole] = None,
    ) -> Tuple[List[CommunityMember], int]:
        """List active members of a community with optional role filter."""
        base_filter = and_(
            CommunityMember.community_id == community_id,
            CommunityMember.status == MembershipStatus.ACTIVE,
        )

        if role:
            base_filter = and_(base_filter, CommunityMember.role == role)

        query = (
            select(CommunityMember)
            .where(base_filter)
            .order_by(CommunityMember.created_at)
            .limit(limit)
            .offset(offset)
        )
        count_query = select(func.count(CommunityMember.id)).where(base_filter)

        members_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        return members_result.scalars().all(), count_result.scalar()

    # -------------------------------------------------------------------------
    # CommunityMember — writes
    # -------------------------------------------------------------------------

    async def add_member(
        self,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
        role: MemberRole = MemberRole.MEMBER,
        status: MembershipStatus = MembershipStatus.ACTIVE,
    ) -> CommunityMember:
        """Add a new member record.  Caller must handle uniqueness check first."""
        member = CommunityMember(
            community_id=community_id,
            user_id=user_id,
            role=role,
            status=status,
        )
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def update_member_role(
        self,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
        role: MemberRole,
    ) -> Optional[CommunityMember]:
        """Update a member's role."""
        await self.session.execute(
            update(CommunityMember)
            .where(
                and_(
                    CommunityMember.community_id == community_id,
                    CommunityMember.user_id == user_id,
                )
            )
            .values(
                role=role,
                updated_at=datetime.now(timezone.utc),
            )
        )
        return await self.get_member(community_id, user_id)

    async def update_member_status(
        self,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
        status: MembershipStatus,
        role: Optional[MemberRole] = None,
    ) -> Optional[CommunityMember]:
        """Update a member's status (and optionally role, e.g., on ban)."""
        values: dict = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if role is not None:
            values["role"] = role

        await self.session.execute(
            update(CommunityMember)
            .where(
                and_(
                    CommunityMember.community_id == community_id,
                    CommunityMember.user_id == user_id,
                )
            )
            .values(**values)
        )
        return await self.get_member(community_id, user_id)

    # -------------------------------------------------------------------------
    # JoinRequest — reads
    # -------------------------------------------------------------------------

    async def get_pending_join_request(
        self,
        community_id: uuid.UUID,
        requester_id: uuid.UUID,
    ) -> Optional[JoinRequest]:
        """Get a user's PENDING join request for a community, if any."""
        result = await self.session.execute(
            select(JoinRequest).where(
                and_(
                    JoinRequest.community_id == community_id,
                    JoinRequest.requester_id == requester_id,
                    JoinRequest.status == JoinRequestStatus.PENDING,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_join_request_by_id(
        self,
        request_id: uuid.UUID,
    ) -> Optional[JoinRequest]:
        """Get a join request by its primary key."""
        result = await self.session.execute(
            select(JoinRequest).where(JoinRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def list_join_requests(
        self,
        community_id: uuid.UUID,
        status: JoinRequestStatus = JoinRequestStatus.PENDING,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[JoinRequest], int]:
        """List join requests for a community, defaulting to PENDING."""
        base_filter = and_(
            JoinRequest.community_id == community_id,
            JoinRequest.status == status,
        )

        query = (
            select(JoinRequest)
            .where(base_filter)
            .order_by(JoinRequest.created_at)
            .limit(limit)
            .offset(offset)
        )
        count_query = select(func.count(JoinRequest.id)).where(base_filter)

        reqs_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        return reqs_result.scalars().all(), count_result.scalar()

    # -------------------------------------------------------------------------
    # JoinRequest — writes
    # -------------------------------------------------------------------------

    async def create_join_request(
        self,
        community_id: uuid.UUID,
        requester_id: uuid.UUID,
        message: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> JoinRequest:
        """Create a new PENDING join request."""
        join_request = JoinRequest(
            community_id=community_id,
            requester_id=requester_id,
            message=message,
            status=JoinRequestStatus.PENDING,
            created_by=created_by,
            updated_by=created_by,
        )
        self.session.add(join_request)
        await self.session.flush()
        await self.session.refresh(join_request)
        return join_request

    async def update_join_request_status(
        self,
        request_id: uuid.UUID,
        status: JoinRequestStatus,
        reviewed_by: Optional[uuid.UUID] = None,
    ) -> Optional[JoinRequest]:
        """Update the status of a join request (approve / reject / cancel)."""
        values: dict = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if reviewed_by is not None:
            values["reviewed_by"] = reviewed_by

        await self.session.execute(
            update(JoinRequest)
            .where(JoinRequest.id == request_id)
            .values(**values)
        )
        return await self.get_join_request_by_id(request_id)
