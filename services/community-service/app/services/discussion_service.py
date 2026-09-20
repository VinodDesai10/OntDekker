"""
Community Service — Discussion Business Logic

Service class that orchestrates discussion thread and comment operations.
Enforces membership-based permissions and manages denormalized comment counts.
"""

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import CommunityRepository, MembershipRepository, DiscussionRepository
from app.schemas.community import (
    DiscussionCreateRequest,
    DiscussionUpdateRequest,
    DiscussionSchema,
    DiscussionSummarySchema,
    DiscussionListResponse,
    DiscussionCommentCreateRequest,
    DiscussionCommentUpdateRequest,
    DiscussionCommentSchema,
    DiscussionCommentListResponse,
    DiscussionQueryParams,
    CommentQueryParams,
)
from shared.constants.status import CommunityVisibility, MemberRole
from shared.exceptions import NotFoundError, ForbiddenError


class DiscussionService:
    """Business logic for community discussions and comments."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.community_repo = CommunityRepository(session)
        self.membership_repo = MembershipRepository(session)
        self.discussion_repo = DiscussionRepository(session)

    # -------------------------------------------------------------------------
    # Discussion CRUD
    # -------------------------------------------------------------------------

    async def create_discussion(
        self,
        community_id: uuid.UUID,
        request: DiscussionCreateRequest,
        current_user_id: uuid.UUID,
    ) -> DiscussionSchema:
        """Create a discussion — authenticated members only."""
        await self._require_active_member(community_id, current_user_id)

        discussion = await self.discussion_repo.create_discussion(
            community_id=community_id,
            author_id=current_user_id,
            title=request.title,
            content=request.content,
            created_by=current_user_id,
        )
        await self.session.commit()
        return DiscussionSchema.model_validate(discussion)

    async def get_discussion(
        self,
        discussion_id: uuid.UUID,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> DiscussionSchema:
        """Get a discussion by ID. Checks community visibility."""
        discussion = await self.discussion_repo.get_discussion_by_id(discussion_id)
        if not discussion:
            raise NotFoundError(f"Discussion {discussion_id} not found")

        await self._check_community_visibility(discussion.community_id, current_user_id)
        return DiscussionSchema.model_validate(discussion)

    async def list_discussions(
        self,
        community_id: uuid.UUID,
        params: DiscussionQueryParams,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> DiscussionListResponse:
        """List discussions for a community."""
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise NotFoundError(f"Community {community_id} not found")

        await self._check_community_visibility(community_id, current_user_id)

        discussions, total = await self.discussion_repo.list_discussions(
            community_id=community_id,
            limit=params.limit,
            offset=params.offset,
        )

        return DiscussionListResponse(
            discussions=[DiscussionSummarySchema.model_validate(d) for d in discussions],
            total=total,
            limit=params.limit,
            offset=params.offset,
            has_more=len(discussions) == params.limit
            and params.offset + len(discussions) < total,
        )

    async def update_discussion(
        self,
        discussion_id: uuid.UUID,
        request: DiscussionUpdateRequest,
        current_user_id: uuid.UUID,
    ) -> DiscussionSchema:
        """Update a discussion — author, moderator, or owner."""
        discussion = await self.discussion_repo.get_discussion_by_id(discussion_id)
        if not discussion:
            raise NotFoundError(f"Discussion {discussion_id} not found")

        await self._require_discussion_edit_permission(discussion, current_user_id)

        updated = await self.discussion_repo.update_discussion(
            discussion_id=discussion_id,
            title=request.title,
            content=request.content,
            updated_by=current_user_id,
        )
        await self.session.commit()
        return DiscussionSchema.model_validate(updated)

    async def delete_discussion(
        self,
        discussion_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> bool:
        """Soft-delete a discussion — author, moderator, or owner."""
        discussion = await self.discussion_repo.get_discussion_by_id(discussion_id)
        if not discussion:
            raise NotFoundError(f"Discussion {discussion_id} not found")

        await self._require_discussion_edit_permission(discussion, current_user_id)

        result = await self.discussion_repo.soft_delete_discussion(
            discussion_id, deleted_by=current_user_id
        )
        await self.session.commit()
        return result

    # -------------------------------------------------------------------------
    # Comment CRUD
    # -------------------------------------------------------------------------

    async def create_comment(
        self,
        discussion_id: uuid.UUID,
        request: DiscussionCommentCreateRequest,
        current_user_id: uuid.UUID,
    ) -> DiscussionCommentSchema:
        """Add a flat comment to a discussion — active members only."""
        discussion = await self.discussion_repo.get_discussion_by_id(discussion_id)
        if not discussion:
            raise NotFoundError(f"Discussion {discussion_id} not found")

        await self._require_active_member(discussion.community_id, current_user_id)

        comment = await self.discussion_repo.create_comment(
            discussion_id=discussion_id,
            author_id=current_user_id,
            content=request.content,
        )
        await self.discussion_repo.increment_comment_count(discussion_id)
        await self.session.commit()
        return DiscussionCommentSchema.model_validate(comment)

    async def list_comments(
        self,
        discussion_id: uuid.UUID,
        params: CommentQueryParams,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> DiscussionCommentListResponse:
        """List comments for a discussion."""
        discussion = await self.discussion_repo.get_discussion_by_id(discussion_id)
        if not discussion:
            raise NotFoundError(f"Discussion {discussion_id} not found")

        await self._check_community_visibility(discussion.community_id, current_user_id)

        comments, total = await self.discussion_repo.list_comments(
            discussion_id=discussion_id,
            limit=params.limit,
            offset=params.offset,
        )

        return DiscussionCommentListResponse(
            comments=[DiscussionCommentSchema.model_validate(c) for c in comments],
            total=total,
            limit=params.limit,
            offset=params.offset,
            has_more=len(comments) == params.limit and params.offset + len(comments) < total,
        )

    async def update_comment(
        self,
        comment_id: uuid.UUID,
        request: DiscussionCommentUpdateRequest,
        current_user_id: uuid.UUID,
    ) -> DiscussionCommentSchema:
        """Update a comment — author, moderator, or owner."""
        comment = await self.discussion_repo.get_comment_by_id(comment_id)
        if not comment:
            raise NotFoundError(f"Comment {comment_id} not found")

        await self._require_comment_edit_permission(comment, current_user_id)

        updated = await self.discussion_repo.update_comment(comment_id, request.content)
        await self.session.commit()
        return DiscussionCommentSchema.model_validate(updated)

    async def delete_comment(
        self,
        comment_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> bool:
        """Soft-delete a comment — author, moderator, or owner."""
        comment = await self.discussion_repo.get_comment_by_id(comment_id)
        if not comment:
            raise NotFoundError(f"Comment {comment_id} not found")

        await self._require_comment_edit_permission(comment, current_user_id)

        result = await self.discussion_repo.soft_delete_comment(
            comment_id, deleted_by=current_user_id
        )
        if result:
            await self.discussion_repo.decrement_comment_count(comment.discussion_id)
        await self.session.commit()
        return result

    # -------------------------------------------------------------------------
    # Permission helpers
    # -------------------------------------------------------------------------

    async def _check_community_visibility(
        self,
        community_id: uuid.UUID,
        current_user_id: Optional[uuid.UUID],
    ) -> None:
        """Raise if the community is private and the user is not a member."""
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise NotFoundError(f"Community {community_id} not found")

        if community.visibility == CommunityVisibility.PRIVATE:
            if not current_user_id:
                raise ForbiddenError("This community is private")
            member = await self.membership_repo.get_active_member(community_id, current_user_id)
            if not member:
                raise ForbiddenError("You must be a member to view this community")

    async def _require_active_member(
        self,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        member = await self.membership_repo.get_active_member(community_id, user_id)
        if not member:
            raise ForbiddenError("You must be an active member to perform this action")

    async def _require_discussion_edit_permission(self, discussion, user_id: uuid.UUID) -> None:
        """Author can edit own discussion; MOD/OWNER can edit or delete any."""
        if discussion.author_id == user_id:
            return
        member = await self.membership_repo.get_active_member(discussion.community_id, user_id)
        if not member or member.role not in (MemberRole.OWNER, MemberRole.MODERATOR):
            raise ForbiddenError(
                "You can only edit or delete your own discussions, "
                "unless you are a moderator or owner"
            )

    async def _require_comment_edit_permission(self, comment, user_id: uuid.UUID) -> None:
        """Author can edit own comment; MOD/OWNER can delete any."""
        if comment.author_id == user_id:
            return
        # We need the community_id from the discussion
        discussion = await self.discussion_repo.get_discussion_by_id(
            comment.discussion_id, include_deleted=True
        )
        if not discussion:
            raise NotFoundError("Parent discussion not found")
        member = await self.membership_repo.get_active_member(discussion.community_id, user_id)
        if not member or member.role not in (MemberRole.OWNER, MemberRole.MODERATOR):
            raise ForbiddenError(
                "You can only edit or delete your own comments, "
                "unless you are a moderator or owner"
            )
