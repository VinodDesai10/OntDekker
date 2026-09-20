"""
Feed Service — Interaction Repository

Async repository for user interactions: likes, bookmarks, shares.
Handles idempotent operations and interaction counts.
"""

import uuid
from typing import List, Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import (
    select, 
    delete, 
    func, 
    and_,
    desc
)
from sqlalchemy.dialects.postgresql import insert

from app.models import Like, Bookmark, Share, Post
from app.schemas.feed import PostQueryParams


class InteractionRepository:
    """Repository for user interactions with posts"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # -------------------------------------------------------------------------
    # Like Operations
    # -------------------------------------------------------------------------
    
    async def like_post(self, post_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Like a post (idempotent operation).
        Returns True if like was created, False if already existed.
        """
        
        # Use PostgreSQL's INSERT ... ON CONFLICT to make it idempotent
        stmt = insert(Like).values(
            post_id=post_id,
            user_id=user_id
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=['post_id', 'user_id'])
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        # If rowcount > 0, a new like was created
        return result.rowcount > 0
    
    async def unlike_post(self, post_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Unlike a post.
        Returns True if like was removed, False if it didn't exist.
        """
        
        stmt = delete(Like).where(
            and_(
                Like.post_id == post_id,
                Like.user_id == user_id
            )
        )
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def is_post_liked_by_user(self, post_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if a user has liked a specific post"""
        
        query = select(func.count(Like.id)).where(
            and_(
                Like.post_id == post_id,
                Like.user_id == user_id
            )
        )
        
        result = await self.session.execute(query)
        return result.scalar() > 0
    
    async def get_post_like_count(self, post_id: uuid.UUID) -> int:
        """Get total number of likes for a post"""
        
        query = select(func.count(Like.id)).where(Like.post_id == post_id)
        result = await self.session.execute(query)
        return result.scalar()
    
    async def get_posts_liked_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[uuid.UUID], int]:
        """
        Get post IDs liked by a user (most recent first).
        Returns (post_ids, total_count).
        """
        
        query = select(Like.post_id).where(
            Like.user_id == user_id
        ).order_by(desc(Like.created_at)).limit(limit).offset(offset)
        
        count_query = select(func.count(Like.id)).where(Like.user_id == user_id)
        
        posts_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        
        post_ids = posts_result.scalars().all()
        total = count_result.scalar()
        
        return post_ids, total
    
    # -------------------------------------------------------------------------
    # Bookmark Operations
    # -------------------------------------------------------------------------
    
    async def bookmark_post(self, post_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Bookmark a post (idempotent operation).
        Returns True if bookmark was created, False if already existed.
        """
        
        stmt = insert(Bookmark).values(
            post_id=post_id,
            user_id=user_id
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=['post_id', 'user_id'])
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def unbookmark_post(self, post_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Remove bookmark from a post.
        Returns True if bookmark was removed, False if it didn't exist.
        """
        
        stmt = delete(Bookmark).where(
            and_(
                Bookmark.post_id == post_id,
                Bookmark.user_id == user_id
            )
        )
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def is_post_bookmarked_by_user(self, post_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if a user has bookmarked a specific post"""
        
        query = select(func.count(Bookmark.id)).where(
            and_(
                Bookmark.post_id == post_id,
                Bookmark.user_id == user_id
            )
        )
        
        result = await self.session.execute(query)
        return result.scalar() > 0
    
    async def get_bookmarked_posts_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[uuid.UUID], int]:
        """
        Get post IDs bookmarked by a user (most recent first).
        Returns (post_ids, total_count).
        """
        
        query = select(Bookmark.post_id).where(
            Bookmark.user_id == user_id
        ).order_by(desc(Bookmark.created_at)).limit(limit).offset(offset)
        
        count_query = select(func.count(Bookmark.id)).where(Bookmark.user_id == user_id)
        
        posts_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        
        post_ids = posts_result.scalars().all()
        total = count_result.scalar()
        
        return post_ids, total
    
    # -------------------------------------------------------------------------
    # Share Operations
    # -------------------------------------------------------------------------
    
    async def share_post(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
        share_channel: Optional[str] = None
    ) -> Share:
        """
        Record a post share (not idempotent - each share is a separate event).
        Returns the created Share record.
        """
        
        share = Share(
            post_id=post_id,
            user_id=user_id,
            share_channel=share_channel
        )
        
        self.session.add(share)
        await self.session.commit()
        await self.session.refresh(share)
        
        return share
    
    async def get_post_share_count(self, post_id: uuid.UUID) -> int:
        """Get total number of shares for a post"""
        
        query = select(func.count(Share.id)).where(Share.post_id == post_id)
        result = await self.session.execute(query)
        return result.scalar()
    
    async def get_shares_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Share], int]:
        """
        Get shares made by a user (most recent first).
        Returns (shares, total_count).
        """
        
        query = select(Share).where(
            Share.user_id == user_id
        ).order_by(desc(Share.created_at)).limit(limit).offset(offset)
        
        count_query = select(func.count(Share.id)).where(Share.user_id == user_id)
        
        shares_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        
        shares = shares_result.scalars().all()
        total = count_result.scalar()
        
        return shares, total
    
    # -------------------------------------------------------------------------
    # Bulk Operations
    # -------------------------------------------------------------------------
    
    async def get_interaction_counts_for_posts(
        self,
        post_ids: List[uuid.UUID]
    ) -> Dict[uuid.UUID, Dict[str, int]]:
        """
        Get like, bookmark, and share counts for multiple posts.
        Returns dict: {post_id: {'likes': count, 'shares': count}}.
        Note: bookmark counts are not included as they're private.
        """
        
        if not post_ids:
            return {}
        
        # Get like counts
        like_query = select(
            Like.post_id,
            func.count(Like.id).label('count')
        ).where(
            Like.post_id.in_(post_ids)
        ).group_by(Like.post_id)
        
        # Get share counts
        share_query = select(
            Share.post_id,
            func.count(Share.id).label('count')
        ).where(
            Share.post_id.in_(post_ids)
        ).group_by(Share.post_id)
        
        # Execute queries
        like_result = await self.session.execute(like_query)
        share_result = await self.session.execute(share_query)
        
        # Build results dict
        results = {}
        for post_id in post_ids:
            results[post_id] = {'likes': 0, 'shares': 0}
        
        # Populate like counts
        for row in like_result.fetchall():
            if row.post_id in results:
                results[row.post_id]['likes'] = row.count
        
        # Populate share counts
        for row in share_result.fetchall():
            if row.post_id in results:
                results[row.post_id]['shares'] = row.count
        
        return results
    
    async def get_user_interactions_for_posts(
        self,
        post_ids: List[uuid.UUID],
        user_id: uuid.UUID
    ) -> Dict[uuid.UUID, Dict[str, bool]]:
        """
        Check which posts a user has liked/bookmarked.
        Returns dict: {post_id: {'is_liked': bool, 'is_bookmarked': bool}}.
        """
        
        if not post_ids:
            return {}
        
        # Get user's likes
        like_query = select(Like.post_id).where(
            and_(
                Like.post_id.in_(post_ids),
                Like.user_id == user_id
            )
        )
        
        # Get user's bookmarks
        bookmark_query = select(Bookmark.post_id).where(
            and_(
                Bookmark.post_id.in_(post_ids),
                Bookmark.user_id == user_id
            )
        )
        
        # Execute queries
        liked_result = await self.session.execute(like_query)
        bookmarked_result = await self.session.execute(bookmark_query)
        
        liked_posts = set(liked_result.scalars().all())
        bookmarked_posts = set(bookmarked_result.scalars().all())
        
        # Build results dict
        results = {}
        for post_id in post_ids:
            results[post_id] = {
                'is_liked': post_id in liked_posts,
                'is_bookmarked': post_id in bookmarked_posts
            }
        
        return results
    
    # -------------------------------------------------------------------------
    # Comment Count Helper (used by post service)
    # -------------------------------------------------------------------------
    
    async def get_comment_counts_for_posts(
        self,
        post_ids: List[uuid.UUID]
    ) -> Dict[uuid.UUID, int]:
        """Get comment counts for multiple posts"""
        
        if not post_ids:
            return {}
        
        from app.models import Comment  # Import here to avoid circular imports
        
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
        
        counts = {}
        for post_id in post_ids:
            counts[post_id] = 0
        
        for row in result.fetchall():
            if row.post_id in counts:
                counts[row.post_id] = row.count
        
        return counts