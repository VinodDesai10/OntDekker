"""
Feed Service — Comment Repository

Async repository for Comment entity with support for nested replies.
Handles CRUD operations and hierarchical comment retrieval.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import (
    select, 
    update, 
    delete, 
    func, 
    and_, 
    desc,
    asc
)

from app.models import Comment, Post


class CommentRepository:
    """Repository for Comment entity with nested replies support"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # -------------------------------------------------------------------------
    # Basic CRUD Operations
    # -------------------------------------------------------------------------
    
    async def create(
        self,
        post_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str,
        parent_comment_id: Optional[uuid.UUID] = None
    ) -> Optional[Comment]:
        """Create a new comment or reply"""
        
        # Verify the post exists and is not deleted
        post_query = select(Post).where(
            and_(
                Post.id == post_id,
                Post.is_deleted == False
            )
        )
        post_result = await self.session.execute(post_query)
        if not post_result.scalar_one_or_none():
            return None
        
        # If it's a reply, verify the parent comment exists
        if parent_comment_id:
            parent_query = select(Comment).where(
                and_(
                    Comment.id == parent_comment_id,
                    Comment.post_id == post_id,  # Must be on the same post
                    Comment.is_deleted == False,
                    Comment.parent_comment_id.is_(None)  # Only allow one level nesting
                )
            )
            parent_result = await self.session.execute(parent_query)
            if not parent_result.scalar_one_or_none():
                return None  # Invalid parent comment
        
        # Create the comment
        comment = Comment(
            post_id=post_id,
            author_id=author_id,
            content=content.strip(),
            parent_comment_id=parent_comment_id
        )
        
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        
        return comment
    
    async def get_by_id(
        self,
        comment_id: uuid.UUID,
        include_deleted: bool = False
    ) -> Optional[Comment]:
        """Get comment by ID with replies loaded"""
        
        query = select(Comment).options(
            selectinload(Comment.replies)
        ).where(Comment.id == comment_id)
        
        if not include_deleted:
            query = query.where(Comment.is_deleted == False)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update(
        self,
        comment_id: uuid.UUID,
        content: str
    ) -> Optional[Comment]:
        """Update comment content"""
        
        query = update(Comment).where(
            and_(
                Comment.id == comment_id,
                Comment.is_deleted == False
            )
        ).values(
            content=content.strip(),
            updated_at=datetime.utcnow()
        )
        
        result = await self.session.execute(query)
        
        if result.rowcount == 0:
            return None
        
        await self.session.commit()
        return await self.get_by_id(comment_id)
    
    async def soft_delete(
        self,
        comment_id: uuid.UUID,
        deleted_by: Optional[uuid.UUID] = None
    ) -> bool:
        """Soft delete a comment"""
        
        query = update(Comment).where(
            and_(
                Comment.id == comment_id,
                Comment.is_deleted == False
            )
        ).values(
            is_deleted=True,
            deleted_at=datetime.utcnow(),
            deleted_by=deleted_by,
            content="[deleted]"  # Replace content for privacy
        )
        
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    async def hard_delete(self, comment_id: uuid.UUID) -> bool:
        """Permanently delete a comment (cascades to replies)"""
        
        query = delete(Comment).where(Comment.id == comment_id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    # -------------------------------------------------------------------------
    # Query Operations
    # -------------------------------------------------------------------------
    
    async def get_comments_for_post(
        self,
        post_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        include_replies: bool = True
    ) -> Tuple[List[Comment], int]:
        """
        Get comments for a post with optional replies.
        Returns top-level comments with nested replies if include_replies=True.
        """
        
        # Base query for top-level comments (no parent)
        query = select(Comment).where(
            and_(
                Comment.post_id == post_id,
                Comment.parent_comment_id.is_(None),
                Comment.is_deleted == False
            )
        )
        
        if include_replies:
            query = query.options(selectinload(Comment.replies))
        
        # Order by creation time (oldest first for better readability)
        query = query.order_by(asc(Comment.created_at)).limit(limit).offset(offset)
        
        # Count query for top-level comments
        count_query = select(func.count(Comment.id)).where(
            and_(
                Comment.post_id == post_id,
                Comment.parent_comment_id.is_(None),
                Comment.is_deleted == False
            )
        )
        
        # Execute queries
        comments_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        
        comments = comments_result.scalars().all()
        total = count_result.scalar()
        
        return comments, total
    
    async def get_replies_for_comment(
        self,
        parent_comment_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Comment], int]:
        """Get replies for a specific comment"""
        
        query = select(Comment).where(
            and_(
                Comment.parent_comment_id == parent_comment_id,
                Comment.is_deleted == False
            )
        ).order_by(asc(Comment.created_at)).limit(limit).offset(offset)
        
        count_query = select(func.count(Comment.id)).where(
            and_(
                Comment.parent_comment_id == parent_comment_id,
                Comment.is_deleted == False
            )
        )
        
        replies_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        
        replies = replies_result.scalars().all()
        total = count_result.scalar()
        
        return replies, total
    
    async def get_comments_by_author(
        self,
        author_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Comment], int]:
        """Get all comments by a specific author (for moderation/profile views)"""
        
        query = select(Comment).where(
            and_(
                Comment.author_id == author_id,
                Comment.is_deleted == False
            )
        ).order_by(desc(Comment.created_at)).limit(limit).offset(offset)
        
        count_query = select(func.count(Comment.id)).where(
            and_(
                Comment.author_id == author_id,
                Comment.is_deleted == False
            )
        )
        
        comments_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        
        comments = comments_result.scalars().all()
        total = count_result.scalar()
        
        return comments, total
    
    # -------------------------------------------------------------------------
    # Statistics Operations
    # -------------------------------------------------------------------------
    
    async def get_comment_count_for_post(self, post_id: uuid.UUID) -> int:
        """Get total comment count for a post (including replies)"""
        
        query = select(func.count(Comment.id)).where(
            and_(
                Comment.post_id == post_id,
                Comment.is_deleted == False
            )
        )
        
        result = await self.session.execute(query)
        return result.scalar()
    
    async def get_comment_counts_for_posts(
        self,
        post_ids: List[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        """Get comment counts for multiple posts"""
        
        if not post_ids:
            return {}
        
        query = select(
            Comment.post_id,
            func.count(Comment.id).label('count')
        ).where(
            and_(
                Comment.post_id.in_(post_ids),
                Comment.is_deleted == False
            )
        ).group_by(Comment.post_id)
        
        result = await self.session.execute(query)
        
        # Initialize all post_ids with 0
        counts = {post_id: 0 for post_id in post_ids}
        
        # Update with actual counts
        for row in result.fetchall():
            if row.post_id in counts:
                counts[row.post_id] = row.count
        
        return counts
    
    async def get_recent_comments_for_posts(
        self,
        post_ids: List[uuid.UUID],
        limit_per_post: int = 3
    ) -> dict[uuid.UUID, List[Comment]]:
        """
        Get a few recent comments for multiple posts (useful for previews).
        Returns dict mapping post_id to list of recent comments.
        """
        
        if not post_ids:
            return {}
        
        # This is a more complex query - we want the top N comments per post
        # Using a window function approach
        from sqlalchemy import text
        
        query = text("""
            SELECT c.* FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY post_id 
                           ORDER BY created_at DESC
                       ) as rn
                FROM comments 
                WHERE post_id = ANY(:post_ids) 
                  AND is_deleted = false
                  AND parent_comment_id IS NULL
            ) c 
            WHERE c.rn <= :limit_per_post
            ORDER BY c.post_id, c.created_at DESC
        """)
        
        result = await self.session.execute(
            query, 
            {
                'post_ids': list(post_ids), 
                'limit_per_post': limit_per_post
            }
        )
        
        # Group comments by post_id
        comments_by_post = {post_id: [] for post_id in post_ids}
        
        for row in result.fetchall():
            post_id = uuid.UUID(str(row.post_id))
            if post_id in comments_by_post:
                # Convert row to Comment object
                comment = Comment(
                    id=uuid.UUID(str(row.id)),
                    post_id=post_id,
                    author_id=uuid.UUID(str(row.author_id)),
                    content=row.content,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    is_deleted=row.is_deleted
                )
                comments_by_post[post_id].append(comment)
        
        return comments_by_post
    
    # -------------------------------------------------------------------------
    # Validation Helpers
    # -------------------------------------------------------------------------
    
    async def can_user_modify_comment(
        self,
        comment_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Check if a user can modify (edit/delete) a comment"""
        
        query = select(Comment.author_id).where(
            and_(
                Comment.id == comment_id,
                Comment.is_deleted == False
            )
        )
        
        result = await self.session.execute(query)
        author_id = result.scalar_one_or_none()
        
        return author_id == user_id if author_id else False