"""
Community Service — Membership Business Logic

Service class that orchestrates all membership state transitions:
join (immediate or via join-request flow), leave, remove, ban,
role updates, and join-request approval/rejection.
"""

import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import CommunityRepository, MembershipRepository
from app.schemas.community import (
    JoinCommunityRequest,
    JoinRequestActionRequest,
    MemberRoleUpdateRequest,
    MemberSchema,
    MemberListResponse,
    JoinRequestSchema,
    JoinRequestListResponse,
    MemberQueryParams,
)
from shared.constants.status import (
    CommunityVisibility,
    JoinRequestStatus,
    MemberRole,
    MembershipStatus,
)
from shared.exceptions import NotFoundError, ForbiddenError, ConflictError, ValidationError


class MembershipService:
    """Business logic for community membership management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.community_repo = CommunityRepository(session)
        self.membership_repo = MembershipRepository(session)

    # -------------------------------------------------------------------------
    # Join flow
    # -------------------------------------------------------------------------

    async def join_community(
        self,
        community_id: uuid.UUID,
        request: JoinCommunityRequest,
        current_user_id: uuid.UUID,
    ) -> dict:
        """
        Join a community.

        - PUBLIC + requires_approval=False → immediate ACTIVE membership
        - PRIVATE or requires_approval=True → JoinRequest (PENDING)

        Returns a dict describing what happened: {"joined": True} or
        {"requested": True, "request_id": UUID}
        """
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise NotFoundError(f"Community {community_id} not found")

        # Check if already an active member
        existing = await self.membership_repo.get_member(community_id, current_user_id)
        if existing and existing.status == MembershipStatus.ACTIVE:
            raise ConflictError("You are already a member of this community")
        if existing and existing.status == MembershipStatus.BANNED:
            raise ForbiddenError("You are banned from this community")

        needs_approval = (
            community.visibility == CommunityVisibility.PRIVATE
            or community.requires_approval
        )

        if needs_approval:
            # Check for an existing pending request
            pending = await self.membership_repo.get_pending_join_request(
                community_id, current_user_id
            )
            if pending:
                raise ConflictError("You already have a pending join request for this community")

            join_request = await self.membership_repo.create_join_request(
                community_id=community_id,
                requester_id=current_user_id,
                message=request.message,
                created_by=current_user_id,
            )
            await self.session.commit()
            return {"requested": True, "request_id": join_request.id}
        else:
            # Immediate join
            if existing:
                # Re-joining after leaving/being removed — update the existing record
                await self.membership_repo.update_member_status(
                    community_id, current_user_id, MembershipStatus.ACTIVE
                )
            else:
                await self.membership_repo.add_member(
                    community_id=community_id,
                    user_id=current_user_id,
                    role=MemberRole.MEMBER,
                    status=MembershipStatus.ACTIVE,
                )
            await self.community_repo.update_member_count(community_id, delta=1)
            await self.session.commit()
            return {"joined": True}

    # -------------------------------------------------------------------------
    # Leave
    # -------------------------------------------------------------------------

    async def leave_community(
        self,
        community_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> bool:
        """Leave a community. OWNERs cannot leave — they must transfer ownership first."""
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise NotFoundError(f"Community {community_id} not found")

        member = await self.membership_repo.get_active_member(community_id, current_user_id)
        if not member:
            raise NotFoundError("You are not a member of this community")

        if member.role == MemberRole.OWNER:
            raise ValidationError(
                "The owner cannot leave the community. Transfer ownership first."
            )

        await self.membership_repo.update_member_status(
            community_id, current_user_id, MembershipStatus.LEFT
        )
        await self.community_repo.update_member_count(community_id, delta=-1)
        await self.session.commit()
        return True

    # -------------------------------------------------------------------------
    # Member listing
    # -------------------------------------------------------------------------

    async def list_members(
        self,
        community_id: uuid.UUID,
        params: MemberQueryParams,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> MemberListResponse:
        """List active members of a community."""
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise NotFoundError(f"Community {community_id} not found")

        # Private community: only members can see the member list
        if community.visibility == CommunityVisibility.PRIVATE:
            if not current_user_id:
                raise ForbiddenError("This community is private")
            member = await self.membership_repo.get_active_member(community_id, current_user_id)
            if not member:
                raise ForbiddenError("You must be a member to view the member list")

        members, total = await self.membership_repo.list_members(
            community_id=community_id,
            limit=params.limit,
            offset=params.offset,
            role=params.role,
        )

        return MemberListResponse(
            members=[MemberSchema.model_validate(m) for m in members],
            total=total,
            limit=params.limit,
            offset=params.offset,
            has_more=len(members) == params.limit and params.offset + len(members) < total,
        )

    # -------------------------------------------------------------------------
    # Moderator / Owner actions
    # -------------------------------------------------------------------------

    async def remove_member(
        self,
        community_id: uuid.UUID,
        target_user_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> bool:
        """Remove a member — MOD or OWNER can do this."""
        await self._require_moderator_or_owner(community_id, current_user_id)

        target = await self.membership_repo.get_active_member(community_id, target_user_id)
        if not target:
            raise NotFoundError(f"User {target_user_id} is not an active member")

        # Moderators cannot remove Owners or other Moderators
        actor = await self.membership_repo.get_active_member(community_id, current_user_id)
        if actor.role == MemberRole.MODERATOR and target.role in (
            MemberRole.OWNER,
            MemberRole.MODERATOR,
        ):
            raise ForbiddenError("Moderators can only remove regular members")

        await self.membership_repo.update_member_status(
            community_id, target_user_id, MembershipStatus.REMOVED
        )
        await self.community_repo.update_member_count(community_id, delta=-1)
        await self.session.commit()
        return True

    async def ban_member(
        self,
        community_id: uuid.UUID,
        target_user_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> bool:
        """Ban a member — MOD or OWNER can do this."""
        await self._require_moderator_or_owner(community_id, current_user_id)

        target = await self.membership_repo.get_active_member(community_id, target_user_id)
        if not target:
            raise NotFoundError(f"User {target_user_id} is not an active member")

        actor = await self.membership_repo.get_active_member(community_id, current_user_id)
        if actor.role == MemberRole.MODERATOR and target.role in (
            MemberRole.OWNER,
            MemberRole.MODERATOR,
        ):
            raise ForbiddenError("Moderators can only ban regular members")

        await self.membership_repo.update_member_status(
            community_id,
            target_user_id,
            MembershipStatus.BANNED,
            role=MemberRole.BANNED,
        )
        await self.community_repo.update_member_count(community_id, delta=-1)
        await self.session.commit()
        return True

    async def update_member_role(
        self,
        community_id: uuid.UUID,
        target_user_id: uuid.UUID,
        request: MemberRoleUpdateRequest,
        current_user_id: uuid.UUID,
    ) -> MemberSchema:
        """Update a member's role — OWNER only."""
        await self._require_owner(community_id, current_user_id)

        target = await self.membership_repo.get_active_member(community_id, target_user_id)
        if not target:
            raise NotFoundError(f"User {target_user_id} is not an active member")

        updated = await self.membership_repo.update_member_role(
            community_id, target_user_id, request.role
        )
        await self.session.commit()
        return MemberSchema.model_validate(updated)

    # -------------------------------------------------------------------------
    # Join request management
    # -------------------------------------------------------------------------

    async def list_join_requests(
        self,
        community_id: uuid.UUID,
        current_user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> JoinRequestListResponse:
        """List pending join requests — MOD or OWNER only."""
        await self._require_moderator_or_owner(community_id, current_user_id)

        requests, total = await self.membership_repo.list_join_requests(
            community_id=community_id,
            status=JoinRequestStatus.PENDING,
            limit=limit,
            offset=offset,
        )

        return JoinRequestListResponse(
            requests=[JoinRequestSchema.model_validate(r) for r in requests],
            total=total,
            limit=limit,
            offset=offset,
            has_more=len(requests) == limit and offset + len(requests) < total,
        )

    async def cancel_join_request(
        self,
        request_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> None:
        """
        Cancel the requester's own pending join request.
        Only the original requester can cancel.
        """
        join_request = await self.membership_repo.get_join_request_by_id(request_id)
        if not join_request:
            raise NotFoundError(f"Join request {request_id} not found")

        if join_request.requester_id != current_user_id:
            raise ForbiddenError("You can only cancel your own join request")

        if join_request.status != JoinRequestStatus.PENDING:
            raise ValidationError("Only pending join requests can be cancelled")

        await self.membership_repo.update_join_request_status(
            request_id=request_id,
            status=JoinRequestStatus.CANCELLED,
            reviewed_by=None,
        )
        await self.session.commit()

    async def action_join_request(
        self,
        request_id: uuid.UUID,
        action_request: JoinRequestActionRequest,
        current_user_id: uuid.UUID,
    ) -> JoinRequestSchema:
        join_request = await self.membership_repo.get_join_request_by_id(request_id)
        if not join_request:
            raise NotFoundError(f"Join request {request_id} not found")

        if join_request.status != JoinRequestStatus.PENDING:
            raise ValidationError("This join request has already been actioned")

        await self._require_moderator_or_owner(join_request.community_id, current_user_id)

        action = action_request.action  # "approve" or "reject"

        if action == "approve":
            new_status = JoinRequestStatus.APPROVED
            # Create the membership
            existing = await self.membership_repo.get_member(
                join_request.community_id, join_request.requester_id
            )
            if existing:
                await self.membership_repo.update_member_status(
                    join_request.community_id,
                    join_request.requester_id,
                    MembershipStatus.ACTIVE,
                )
            else:
                await self.membership_repo.add_member(
                    community_id=join_request.community_id,
                    user_id=join_request.requester_id,
                    role=MemberRole.MEMBER,
                    status=MembershipStatus.ACTIVE,
                )
            await self.community_repo.update_member_count(
                join_request.community_id, delta=1
            )
        else:
            new_status = JoinRequestStatus.REJECTED

        updated = await self.membership_repo.update_join_request_status(
            request_id=request_id,
            status=new_status,
            reviewed_by=current_user_id,
        )
        await self.session.commit()
        return JoinRequestSchema.model_validate(updated)

    # -------------------------------------------------------------------------
    # Permission helpers
    # -------------------------------------------------------------------------

    async def _require_owner(self, community_id: uuid.UUID, user_id: uuid.UUID) -> None:
        member = await self.membership_repo.get_active_member(community_id, user_id)
        if not member or member.role != MemberRole.OWNER:
            raise ForbiddenError("Only the community owner can perform this action")

    async def _require_moderator_or_owner(
        self, community_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        member = await self.membership_repo.get_active_member(community_id, user_id)
        if not member or member.role not in (MemberRole.OWNER, MemberRole.MODERATOR):
            raise ForbiddenError("Only moderators or the owner can perform this action")
