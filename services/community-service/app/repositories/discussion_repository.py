"""
Community Service — Discussion Repository

Async repository for Discussion and DiscussionComment entities.
Handles thread creation, listing, soft-delete, and flat comment management.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select, update, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Discussion, DiscussionComment


class DiscussionRepository:
    """Repository for Discussion and DiscussionComment entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # Discussion — reads
    # -------------------------------------------------------------------------

    async def get_discussion_by_id(
        self,
        discussion_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[Discussion]:
        """Get a discussion by primary key."""
        query = select(Discussion).where(Discussion.id == discussion_id)
        if not include_deleted:
            query = query.where(Discussion.is_deleted == False)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_discussions(
        self,
        community_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Discussion], int]:
        """List non-deleted discussions for a community, newest first."""
        base_filter = and_(
            Discussion.community_id == community_id,
            Discussion.is_deleted == False,
        )

        query = (
            select(Discussion)
            .where(base_filter)
            .order_by(desc(Discussion.created_at))
            .limit(limit)
            .offset(offset)
        )
        count_query = select(func.count(Discussion.id)).where(base_filter)

        discussions_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        return discussions_result.scalars().all(), count_result.scalar()

    # -------------------------------------------------------------------------
    # Discussion — writes
    # -------------------------------------------------------------------------

    async def create_discussion(
        self,
        community_id: uuid.UUID,
        author_id: uuid.UUID,
        title: str,
        content: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> Discussion:
        """Create a new discussion thread."""
        discussion = Discussion(
            community_id=community_id,
            author_id=author_id,
            title=title.strip(),
            content=content,
            comment_count=0,
            created_by=created_by,
            updated_by=created_by,
        )
        self.session.add(discussion)
        await self.session.flush()
        await self.session.refresh(discussion)
        return discussion

    async def update_discussion(
        self,
        discussion_id: uuid.UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        updated_by: Optional[uuid.UUID] = None,
    ) -> Optional[Discussion]:
        """Update a discussion's title and/or content."""
        values: dict = {"updated_at": datetime.now(timezone.utc)}
        if title is not None:
            values["title"] = title.strip()
        if content is not None:
            values["content"] = content
        if updated_by is not None:
            values["updated_by"] = updated_by

        if len(values) == 1:  # only updated_at
            return await self.get_discussion_by_id(discussion_id)

        await self.session.execute(
            update(Discussion)
            .where(
                and_(
                    Discussion.id == discussion_id,
                    Discussion.is_deleted == False,
                )
            )
            .values(**values)
        )
        return await self.get_discussion_by_id(discussion_id)

    async def soft_delete_discussion(
        self,
        discussion_id: uuid.UUID,
        deleted_by: Optional[uuid.UUID] = None,
    ) -> bool:
        """Soft delete a discussion (preserves comments)."""
        result = await self.session.execute(
            update(Discussion)
            .where(
                and_(
                    Discussion.id == discussion_id,
                    Discussion.is_deleted == False,
                )
            )
            .values(
                is_deleted=True,
                deleted_at=datetime.now(timezone.utc),
                deleted_by=deleted_by,
            )
        )
        return result.rowcount > 0

    async def increment_comment_count(self, discussion_id: uuid.UUID) -> None:
        """Increment the denormalized comment count by 1."""
        await self.session.execute(
            update(Discussion)
            .where(Discussion.id == discussion_id)
            .values(comment_count=Discussion.comment_count + 1)
        )

    async def decrement_comment_count(self, discussion_id: uuid.UUID) -> None:
        """Decrement the denormalized comment count by 1 (floor at 0)."""
        await self.session.execute(
            update(Discussion)
            .where(
                and_(
                    Discussion.id == discussion_id,
                    Discussion.comment_count > 0,
                )
            )
            .values(comment_count=Discussion.comment_count - 1)
        )

    # -------------------------------------------------------------------------
    # DiscussionComment — reads
    # -------------------------------------------------------------------------

    async def get_comment_by_id(
        self,
        comment_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[DiscussionComment]:
        """Get a discussion comment by primary key."""
        query = select(DiscussionComment).where(DiscussionComment.id == comment_id)
        if not include_deleted:
            query = query.where(DiscussionComment.is_deleted == False)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_comments(
        self,
        discussion_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[DiscussionComment], int]:
        """List non-deleted comments for a discussion, oldest first."""
        base_filter = and_(
            DiscussionComment.discussion_id == discussion_id,
            DiscussionComment.is_deleted == False,
        )

        query = (
            select(DiscussionComment)
            .where(base_filter)
            .order_by(DiscussionComment.created_at)
            .limit(limit)
            .offset(offset)
        )
        count_query = select(func.count(DiscussionComment.id)).where(base_filter)

        comments_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        return comments_result.scalars().all(), count_result.scalar()

    # -------------------------------------------------------------------------
    # DiscussionComment — writes
    # -------------------------------------------------------------------------

    async def create_comment(
        self,
        discussion_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str,
    ) -> DiscussionComment:
        """Create a new flat comment on a discussion."""
        comment = DiscussionComment(
            discussion_id=discussion_id,
            author_id=author_id,
            content=content.strip(),
        )
        self.session.add(comment)
        await self.session.flush()
        await self.session.refresh(comment)
        return comment

    async def update_comment(
        self,
        comment_id: uuid.UUID,
        content: str,
    ) -> Optional[DiscussionComment]:
        """Update a comment's content."""
        await self.session.execute(
            update(DiscussionComment)
            .where(
                and_(
                    DiscussionComment.id == comment_id,
                    DiscussionComment.is_deleted == False,
                )
            )
            .values(
                content=content.strip(),
                updated_at=datetime.now(timezone.utc),
            )
        )
        return await self.get_comment_by_id(comment_id)

    async def soft_delete_comment(
        self,
        comment_id: uuid.UUID,
        deleted_by: Optional[uuid.UUID] = None,
    ) -> bool:
        """Soft delete a discussion comment."""
        result = await self.session.execute(
            update(DiscussionComment)
            .where(
                and_(
                    DiscussionComment.id == comment_id,
                    DiscussionComment.is_deleted == False,
                )
            )
            .values(
                is_deleted=True,
                deleted_at=datetime.now(timezone.utc),
                deleted_by=deleted_by,
            )
        )
        return result.rowcount > 0
