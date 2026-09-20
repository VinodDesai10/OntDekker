"""
Feed Service — Post Repository

Async repository for Post entity with CRUD operations and custom queries.
Handles database interactions for posts, media, and tags.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import (
    select, 
    update, 
    delete, 
    func, 
    and_, 
    or_, 
    desc,
    asc,
    text
)
from sqlalchemy.dialects.postgresql import insert

from app.models import Post, PostMedia, PostTag
from app.schemas.feed import PostQueryParams
from shared.constants.status import PostStatus, PostVisibility


class PostRepository:
    """Repository for Post entity and related data"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # -------------------------------------------------------------------------
    # Basic CRUD Operations
    # -------------------------------------------------------------------------
    
    async def create(
        self, 
        author_id: uuid.UUID,
        title: str,
        content: Optional[str] = None,
        location: Optional[str] = None,
        community_id: Optional[uuid.UUID] = None,
        expedition_id: Optional[uuid.UUID] = None,
        status: PostStatus = PostStatus.PUBLISHED,
        visibility: PostVisibility = PostVisibility.PUBLIC,
        tags: Optional[List[str]] = None,
        created_by: Optional[uuid.UUID] = None
    ) -> Post:
        """Create a new post with optional tags"""
        
        # Create the post
        post = Post(
            author_id=author_id,
            title=title,
            content=content,
            location=location,
            community_id=community_id,
            expedition_id=expedition_id,
            status=status,
            visibility=visibility,
            created_by=created_by,
            updated_by=created_by
        )
        
        self.session.add(post)
        await self.session.flush()  # Get the ID
        
        # Add tags if provided
        if tags:
            tag_objects = [
                PostTag(post_id=post.id, tag=tag.strip().lower())
                for tag in tags
                if tag.strip()
            ]
            self.session.add_all(tag_objects)
        
        await self.session.commit()
        await self.session.refresh(post, ['media', 'tags'])
        return post
    
    async def get_by_id(
        self, 
        post_id: uuid.UUID, 
        include_deleted: bool = False
    ) -> Optional[Post]:
        """Get post by ID with all relationships loaded"""
        
        query = select(Post).options(
            selectinload(Post.media),
            selectinload(Post.tags)
        ).where(Post.id == post_id)
        
        if not include_deleted:
            query = query.where(Post.is_deleted == False)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_many(
        self,
        post_ids: List[uuid.UUID],
        include_deleted: bool = False
    ) -> List[Post]:
        """Get multiple posts by IDs"""
        
        query = select(Post).options(
            selectinload(Post.media),
            selectinload(Post.tags)
        ).where(Post.id.in_(post_ids))
        
        if not include_deleted:
            query = query.where(Post.is_deleted == False)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update(
        self,
        post_id: uuid.UUID,
        **updates: Any
    ) -> Optional[Post]:
        """Update post fields"""
        
        if not updates:
            return await self.get_by_id(post_id)
        
        # Handle tags separately
        tags = updates.pop('tags', None)
        
        # Add audit fields
        updates['updated_at'] = datetime.utcnow()
        if 'updated_by' not in updates:
            updates['updated_by'] = updates.get('updated_by')
        
        # Update the post
        query = update(Post).where(
            and_(Post.id == post_id, Post.is_deleted == False)
        ).values(**updates)
        
        result = await self.session.execute(query)
        if result.rowcount == 0:
            return None
        
        # Handle tags update if provided
        if tags is not None:
            await self._update_tags(post_id, tags)
        
        await self.session.commit()
        return await self.get_by_id(post_id)
    
    async def soft_delete(
        self,
        post_id: uuid.UUID,
        deleted_by: Optional[uuid.UUID] = None
    ) -> bool:
        """Soft delete a post"""
        
        query = update(Post).where(
            and_(Post.id == post_id, Post.is_deleted == False)
        ).values(
            is_deleted=True,
            deleted_at=datetime.utcnow(),
            deleted_by=deleted_by
        )
        
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    async def hard_delete(self, post_id: uuid.UUID) -> bool:
        """Permanently delete a post (cascades to media and tags)"""
        
        query = delete(Post).where(Post.id == post_id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    # -------------------------------------------------------------------------
    # Query Operations
    # -------------------------------------------------------------------------
    
    async def list_posts(
        self,
        params: PostQueryParams,
        current_user_id: Optional[uuid.UUID] = None,
        user_community_ids: Optional[List[uuid.UUID]] = None,
    ) -> Tuple[List[Post], int]:
        """
        List posts with filtering, pagination, and total count.
        Returns (posts, total_count) tuple.

        Args:
            params: Query parameters (filters, pagination).
            current_user_id: The authenticated user's ID, used for visibility rules.
            user_community_ids: List of community IDs the current user belongs to.
                Used to enforce community-post visibility — only posts from those
                communities are returned.  If None, community membership is not
                enforced (anonymous feed shows PUBLIC posts only).
        """
        
        # Base query
        query = select(Post).options(
            selectinload(Post.media),
            selectinload(Post.tags)
        ).where(Post.is_deleted == False)
        
        # Count query (without relationships)
        count_query = select(func.count(Post.id)).where(Post.is_deleted == False)
        
        # Apply filters
        query, count_query = self._apply_filters(
            query, count_query, params, current_user_id, user_community_ids
        )
        
        # Apply ordering (chronological by default)
        query = query.order_by(desc(Post.created_at))
        
        # Apply pagination
        query = query.limit(params.limit).offset(params.offset)
        
        # Execute both queries
        posts_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        
        posts = posts_result.scalars().all()
        total = count_result.scalar()
        
        return posts, total
    
    async def get_posts_by_author(
        self,
        author_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        current_user_id: Optional[uuid.UUID] = None
    ) -> Tuple[List[Post], int]:
        """Get posts by a specific author"""
        
        # Visibility logic: if viewing own posts, show all; otherwise only public/community
        if current_user_id == author_id:
            visibility_filter = Post.status == PostStatus.PUBLISHED
        else:
            visibility_filter = and_(
                Post.status == PostStatus.PUBLISHED,
                or_(
                    Post.visibility == PostVisibility.PUBLIC,
                    Post.visibility == PostVisibility.COMMUNITY
                )
            )
        
        query = select(Post).options(
            selectinload(Post.media),
            selectinload(Post.tags)
        ).where(
            and_(
                Post.author_id == author_id,
                Post.is_deleted == False,
                visibility_filter
            )
        ).order_by(desc(Post.created_at)).limit(limit).offset(offset)
        
        count_query = select(func.count(Post.id)).where(
            and_(
                Post.author_id == author_id,
                Post.is_deleted == False,
                visibility_filter
            )
        )
        
        posts_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        
        return posts_result.scalars().all(), count_result.scalar()
    
    async def get_posts_by_community(
        self,
        community_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Post], int]:
        """Get posts in a specific community"""
        
        query = select(Post).options(
            selectinload(Post.media),
            selectinload(Post.tags)
        ).where(
            and_(
                Post.community_id == community_id,
                Post.is_deleted == False,
                Post.status == PostStatus.PUBLISHED,
                or_(
                    Post.visibility == PostVisibility.PUBLIC,
                    Post.visibility == PostVisibility.COMMUNITY
                )
            )
        ).order_by(desc(Post.created_at)).limit(limit).offset(offset)
        
        count_query = select(func.count(Post.id)).where(
            and_(
                Post.community_id == community_id,
                Post.is_deleted == False,
                Post.status == PostStatus.PUBLISHED,
                or_(
                    Post.visibility == PostVisibility.PUBLIC,
                    Post.visibility == PostVisibility.COMMUNITY
                )
            )
        )
        
        posts_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        
        return posts_result.scalars().all(), count_result.scalar()
    
    async def search_posts_by_tags(
        self,
        tags: List[str],
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Post], int]:
        """Search posts by tags (OR logic)"""
        
        tag_filter = select(PostTag.post_id).where(
            PostTag.tag.in_([tag.lower().strip() for tag in tags])
        )
        
        query = select(Post).options(
            selectinload(Post.media),
            selectinload(Post.tags)
        ).where(
            and_(
                Post.id.in_(tag_filter),
                Post.is_deleted == False,
                Post.status == PostStatus.PUBLISHED,
                Post.visibility == PostVisibility.PUBLIC
            )
        ).order_by(desc(Post.created_at)).limit(limit).offset(offset)
        
        count_query = select(func.count(Post.id)).where(
            and_(
                Post.id.in_(tag_filter),
                Post.is_deleted == False,
                Post.status == PostStatus.PUBLISHED,
                Post.visibility == PostVisibility.PUBLIC
            )
        )
        
        posts_result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        
        return posts_result.scalars().all(), count_result.scalar()
    
    # -------------------------------------------------------------------------
    # Media Operations
    # -------------------------------------------------------------------------
    
    async def add_media(
        self,
        post_id: uuid.UUID,
        media_url: str,
        object_key: str,
        display_order: int = 0,
        alt_text: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None
    ) -> Optional[PostMedia]:
        """Add media to a post"""
        
        # Verify post exists
        post = await self.get_by_id(post_id)
        if not post:
            return None
        
        media = PostMedia(
            post_id=post_id,
            media_url=media_url,
            object_key=object_key,
            display_order=display_order,
            alt_text=alt_text,
            created_by=created_by,
            updated_by=created_by
        )
        
        self.session.add(media)
        await self.session.commit()
        await self.session.refresh(media)
        return media
    
    async def remove_media(
        self,
        post_id: uuid.UUID,
        media_id: uuid.UUID
    ) -> bool:
        """Remove media from a post"""
        
        query = delete(PostMedia).where(
            and_(
                PostMedia.id == media_id,
                PostMedia.post_id == post_id
            )
        )
        
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    async def _update_tags(self, post_id: uuid.UUID, tags: List[str]) -> None:
        """Replace all tags for a post"""
        
        # Delete existing tags
        await self.session.execute(
            delete(PostTag).where(PostTag.post_id == post_id)
        )
        
        # Add new tags
        if tags:
            clean_tags = [tag.strip().lower() for tag in tags if tag.strip()]
            tag_objects = [
                PostTag(post_id=post_id, tag=tag) for tag in clean_tags
            ]
            self.session.add_all(tag_objects)
    
    def _apply_filters(
        self, 
        query, 
        count_query, 
        params: PostQueryParams,
        current_user_id: Optional[uuid.UUID] = None,
        user_community_ids: Optional[List[uuid.UUID]] = None,
    ) -> Tuple[Any, Any]:
        """Apply filtering logic to both main and count queries.

        Visibility enforcement (applied when no explicit visibility filter given):
          - Anonymous (current_user_id=None):
              Only PUBLIC posts are visible.
          - Authenticated (current_user_id set) — main feed mode:
              PUBLIC posts from other authors are visible.
              COMMUNITY posts from communities the user belongs to are visible.
              Own COMMUNITY posts are excluded by the exclude_author_id filter.
              PRIVATE posts are never returned in the general feed (only via
              get_post() or get_posts_by_author() which have their own logic).

        The explicit ``params.visibility`` filter can narrow this further (e.g.,
        community_id + COMMUNITY for a community-scoped feed request).
        """

        # ── Own-post exclusion (exclude_author_id) ──────────────────────────
        # Applied first so it's always enforced regardless of other filters.
        # This ensures the JWT-derived current_user_id can never be overridden
        # by the caller passing a different exclude_author_id.
        if params.exclude_author_id:
            filter_cond = Post.author_id != params.exclude_author_id
            query = query.where(filter_cond)
            count_query = count_query.where(filter_cond)

        # ── Author filter ────────────────────────────────────────────────────
        if params.author_id:
            filter_cond = Post.author_id == params.author_id
            query = query.where(filter_cond)
            count_query = count_query.where(filter_cond)
        
        # ── Community filter ─────────────────────────────────────────────────
        if params.community_id:
            filter_cond = Post.community_id == params.community_id
            query = query.where(filter_cond)
            count_query = count_query.where(filter_cond)
        
        # ── Expedition filter ────────────────────────────────────────────────
        if params.expedition_id:
            filter_cond = Post.expedition_id == params.expedition_id
            query = query.where(filter_cond)
            count_query = count_query.where(filter_cond)
        
        # ── Status filter ────────────────────────────────────────────────────
        if params.status:
            filter_cond = Post.status == params.status
            query = query.where(filter_cond)
            count_query = count_query.where(filter_cond)
        
        # ── Visibility filter ────────────────────────────────────────────────
        # If an explicit visibility is requested, apply it directly.
        # Otherwise, enforce the feed visibility rules based on auth state.
        if params.visibility:
            filter_cond = Post.visibility == params.visibility
            query = query.where(filter_cond)
            count_query = count_query.where(filter_cond)
        elif params.community_id:
            # Scoped community feed (params.community_id explicitly set).
            # The caller has already filtered by a specific community; the
            # community-detail page validates membership separately before
            # rendering this feed.  We only enforce PUBLISHED status here —
            # not the main-feed membership-based visibility rules — so that
            # community posts are visible to the scoped caller.
            published_cond = Post.status == PostStatus.PUBLISHED
            query = query.where(published_cond)
            count_query = count_query.where(published_cond)
        else:
            # Default main-feed visibility enforcement:
            # - Always show only PUBLISHED posts
            # - Anonymous: only PUBLIC posts
            # - Authenticated: PUBLIC posts + COMMUNITY posts from joined communities
            published_cond = Post.status == PostStatus.PUBLISHED

            if current_user_id is None:
                # Anonymous users: only see PUBLIC posts
                vis_cond = and_(
                    published_cond,
                    Post.visibility == PostVisibility.PUBLIC,
                )
            else:
                # Authenticated users: PUBLIC posts always visible.
                # COMMUNITY posts: only if user_community_ids is provided and
                # the post's community_id is in that set.
                # PRIVATE posts: never in the general feed.
                if user_community_ids:
                    vis_cond = and_(
                        published_cond,
                        or_(
                            Post.visibility == PostVisibility.PUBLIC,
                            and_(
                                Post.visibility == PostVisibility.COMMUNITY,
                                Post.community_id.in_(user_community_ids),
                            ),
                        ),
                    )
                else:
                    # Authenticated but no community memberships (or membership
                    # fetch was skipped) — show PUBLIC posts only.
                    vis_cond = and_(
                        published_cond,
                        Post.visibility == PostVisibility.PUBLIC,
                    )

            query = query.where(vis_cond)
            count_query = count_query.where(vis_cond)
        
        # ── Location filter (partial match) ──────────────────────────────────
        if params.location:
            filter_cond = Post.location.ilike(f'%{params.location}%')
            query = query.where(filter_cond)
            count_query = count_query.where(filter_cond)
        
        # ── Date range filters ────────────────────────────────────────────────
        if params.since:
            filter_cond = Post.created_at >= params.since
            query = query.where(filter_cond)
            count_query = count_query.where(filter_cond)
        
        if params.until:
            filter_cond = Post.created_at <= params.until
            query = query.where(filter_cond)
            count_query = count_query.where(filter_cond)
        
        # ── Tags filter ───────────────────────────────────────────────────────
        if params.tags:
            tag_list = [tag.strip().lower() for tag in params.tags.split(',') if tag.strip()]
            if tag_list:
                tag_subquery = select(PostTag.post_id).where(
                    PostTag.tag.in_(tag_list)
                )
                filter_cond = Post.id.in_(tag_subquery)
                query = query.where(filter_cond)
                count_query = count_query.where(filter_cond)
        
        return query, count_query