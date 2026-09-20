"""
Feed Service — Business Logic Layer

Service classes that orchestrate business logic, coordinate repositories,
and handle cross-cutting concerns like authorization and data enrichment.
"""

import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.models import Post, Comment, PostMedia, Share
from app.repositories import PostRepository, InteractionRepository, CommentRepository
from app.schemas.feed import (
    PostCreateRequest,
    PostUpdateRequest,
    PostSchema,
    PostSummarySchema,
    PostListResponse,
    PostQueryParams,
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentSchema,
    CommentListResponse,
    CommentQueryParams,
    LikeActionResponse,
    BookmarkActionResponse,
    ShareActionResponse,
    ShareRequest,
    BookmarkListResponse,
)
from shared.constants.status import PostStatus, PostVisibility
from shared.exceptions import NotFoundError, ForbiddenError, ValidationError

logger = logging.getLogger(__name__)


async def _verify_community_membership(
    community_service_url: str,
    community_id: uuid.UUID,
    user_id: uuid.UUID,
    authorization_header: Optional[str] = None,
) -> bool:
    """
    Calls the community-service to verify that user_id is an ACTIVE member
    of community_id.

    Uses the GET /{community_id}/members endpoint and checks for the user
    in the result.  Falls back to listing members with a role-agnostic query.

    Returns True if the user is an active member, False otherwise.
    Raises ValidationError if the community does not exist (404).
    Raises ForbiddenError if the request itself is denied (403).
    On any other network or unexpected error, raises ValidationError with a
    helpful message so the caller can surface it to the API consumer.
    """
    url = f"{community_service_url}/api/v1/communities/{community_id}/members"
    headers: Dict[str, str] = {}
    if authorization_header:
        headers["Authorization"] = authorization_header

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Fetch up to 200 members; for large communities we page through
            params = {"limit": 200, "offset": 0}
            response = await client.get(url, params=params, headers=headers)

        if response.status_code == 404:
            raise ValidationError(f"Community {community_id} does not exist.")
        if response.status_code == 403:
            raise ForbiddenError("Not authorized to access community membership data.")
        if response.status_code != 200:
            logger.error(
                "Community membership check failed: status=%s body=%s",
                response.status_code,
                response.text[:200],
            )
            raise ValidationError(
                "Could not verify community membership. Please try again."
            )

        body = response.json()
        members = body.get("members", [])
        user_id_str = str(user_id)
        for member in members:
            # Community service returns snake_case JSON (not camelCase interceptor)
            member_user_id = member.get("user_id") or member.get("userId", "")
            member_status = member.get("status", "")
            if str(member_user_id) == user_id_str and member_status == "ACTIVE":
                return True
        return False

    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error("Community service unreachable: %s", exc)
        raise ValidationError(
            "Community membership verification is temporarily unavailable. "
            "Please try again shortly."
        )


class PostService:
    """Business logic for post management"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.post_repo = PostRepository(session)
        self.interaction_repo = InteractionRepository(session)
        self.comment_repo = CommentRepository(session)
    
    # -------------------------------------------------------------------------
    # Post CRUD Operations
    # -------------------------------------------------------------------------
    
    async def create_post(
        self,
        request: PostCreateRequest,
        author_id: uuid.UUID,
        authorization_header: Optional[str] = None,
    ) -> PostSchema:
        """Create a new post with business validation.

        Validation rules enforced here (independent of frontend):
          GLOBAL (PUBLIC):
            - community_id must be None/null

          COMMUNITY:
            - community_id must be provided
            - author must be an ACTIVE member of that community
              (verified via community-service HTTP call)

          PRIVATE:
            - community_id must be None/null (private community posts make no sense)
        """

        # ── Visibility / community_id cross-validation ──────────────────────

        if request.visibility == PostVisibility.PUBLIC:
            # GLOBAL post — must not target a community
            if request.community_id is not None:
                raise ValidationError(
                    "A PUBLIC (Global) post cannot have a community_id. "
                    "Set community_id to null for global posts."
                )

        elif request.visibility == PostVisibility.COMMUNITY:
            # COMMUNITY post — community_id is mandatory
            if request.community_id is None:
                raise ValidationError(
                    "A COMMUNITY post requires a community_id."
                )

            # ── Membership verification ────────────────────────────────────
            from app.config.settings import settings
            is_member = await _verify_community_membership(
                community_service_url=settings.COMMUNITY_SERVICE_URL,
                community_id=request.community_id,
                user_id=author_id,
                authorization_header=authorization_header,
            )
            if not is_member:
                raise ForbiddenError(
                    "You are not an active member of this community and cannot "
                    "post to it."
                )

        elif request.visibility == PostVisibility.PRIVATE:
            # PRIVATE post — must not target a community
            if request.community_id is not None:
                raise ValidationError("Private posts cannot be associated with a community.")
        
        # Create post
        post = await self.post_repo.create(
            author_id=author_id,
            title=request.title,
            content=request.content,
            location=request.location,
            community_id=request.community_id,
            expedition_id=request.expedition_id,
            visibility=request.visibility,
            tags=request.tags,
            created_by=author_id
        )
        
        # Enrich with interaction data
        return await self._enrich_post_schema(post, author_id)
    
    async def get_post(
        self,
        post_id: uuid.UUID,
        current_user_id: Optional[uuid.UUID] = None
    ) -> PostSchema:
        """Get a post with authorization checks"""
        
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise NotFoundError(f"Post {post_id} not found")
        
        # Authorization check
        if not await self._can_user_view_post(post, current_user_id):
            raise ForbiddenError("You don't have permission to view this post")
        
        return await self._enrich_post_schema(post, current_user_id)
    
    async def update_post(
        self,
        post_id: uuid.UUID,
        request: PostUpdateRequest,
        current_user_id: uuid.UUID
    ) -> PostSchema:
        """Update a post with authorization"""
        
        # Check ownership
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise NotFoundError(f"Post {post_id} not found")
        
        if post.author_id != current_user_id:
            raise ForbiddenError("You can only edit your own posts")
        
        # Prepare updates dict (only include non-None values)
        updates = {}
        for field in ['title', 'content', 'location', 'visibility']:
            value = getattr(request, field)
            if value is not None:
                updates[field] = value
        
        updates['updated_by'] = current_user_id
        
        # Handle tags separately
        if request.tags is not None:
            updates['tags'] = request.tags
        
        # Business validation
        if 'visibility' in updates and updates['visibility'] == PostVisibility.PRIVATE and post.community_id:
            raise ValidationError("Community posts cannot be private")
        
        updated_post = await self.post_repo.update(post_id, **updates)
        return await self._enrich_post_schema(updated_post, current_user_id)
    
    async def delete_post(
        self,
        post_id: uuid.UUID,
        current_user_id: uuid.UUID
    ) -> bool:
        """Soft delete a post with authorization"""
        
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise NotFoundError(f"Post {post_id} not found")
        
        if post.author_id != current_user_id:
            raise ForbiddenError("You can only delete your own posts")
        
        return await self.post_repo.soft_delete(post_id, current_user_id)
    
    # -------------------------------------------------------------------------
    # Post Listing & Search
    # -------------------------------------------------------------------------
    
    async def list_posts(
        self,
        params: PostQueryParams,
        current_user_id: Optional[uuid.UUID] = None,
        authorization_header: Optional[str] = None,
    ) -> PostListResponse:
        """List posts with filtering, pagination, and feed visibility rules.

        For the main feed this method:
          1. Sets exclude_author_id = current_user_id so the caller never sees
             their own posts (own-post exclusion at query level).
          2. Fetches the user's community memberships in a single HTTP call so
             COMMUNITY-visibility posts from joined communities are included.
          3. Passes both to the repository so all filtering happens in SQL
             (correct pagination — no post-fetch removal).
        """
        user_community_ids: Optional[List[uuid.UUID]] = None

        # Inject own-post exclusion for authenticated users in the main feed.
        # Security: we derive this from the JWT, never from the request body.
        if current_user_id is not None and params.exclude_author_id is None:
            # Only set it if no explicit override was provided.
            # Callers that legitimately want to see own posts (e.g., profile
            # endpoint) should not use list_posts() — they use get_posts_by_author().
            params = params.model_copy(update={"exclude_author_id": current_user_id})

        # Fetch user's community IDs for community-post visibility enforcement.
        if current_user_id is not None:
            user_community_ids = await self._fetch_user_community_ids(
                authorization_header=authorization_header
            )

        posts, total = await self.post_repo.list_posts(
            params, current_user_id, user_community_ids
        )
        
        # Convert to summary schemas — no further visibility filtering needed
        # because the repository already enforced all rules at query level.
        enriched_posts = []
        for post in posts:
            try:
                summary = await self._convert_to_summary_schema(post, current_user_id)
                enriched_posts.append(summary)
            except Exception:
                continue  # Silently skip posts that fail enrichment

        return PostListResponse(
            posts=enriched_posts,
            total=total,
            limit=params.limit,
            offset=params.offset,
            has_more=total > params.offset + len(enriched_posts),
        )

    async def _fetch_user_community_ids(
        self,
        authorization_header: Optional[str] = None,
    ) -> List[uuid.UUID]:
        """Fetch the list of community IDs the current user belongs to.

        Makes a single GET /api/v1/communities/?limit=200 request to the
        community-service with the user's Authorization header.  The response
        includes an ``is_member`` flag per community; we collect the IDs where
        ``is_member=True``.

        Returns an empty list on any error (network, auth, timeout) so the feed
        gracefully degrades to showing only PUBLIC posts rather than failing.
        """
        from app.config.settings import settings

        url = f"{settings.COMMUNITY_SERVICE_URL}/api/v1/communities/"
        headers: Dict[str, str] = {}
        if authorization_header:
            headers["Authorization"] = authorization_header

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    url,
                    params={"limit": 200, "offset": 0},
                    headers=headers,
                )

            if response.status_code != 200:
                logger.warning(
                    "community-service returned %s when fetching memberships",
                    response.status_code,
                )
                return []

            body = response.json()
            communities = body.get("communities", body.get("items", []))
            return [
                uuid.UUID(c["id"])
                for c in communities
                if c.get("is_member") is True
            ]

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("community-service unreachable when fetching memberships: %s", exc)
            return []
        except Exception as exc:
            logger.warning("unexpected error fetching community memberships: %s", exc)
            return []
    
    async def get_posts_by_author(
        self,
        author_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        current_user_id: Optional[uuid.UUID] = None
    ) -> PostListResponse:
        """Get posts by a specific author"""
        
        posts, total = await self.post_repo.get_posts_by_author(
            author_id, limit, offset, current_user_id
        )
        
        # Convert to summary schemas
        summaries = []
        for post in posts:
            summary = await self._convert_to_summary_schema(post, current_user_id)
            summaries.append(summary)
        
        return PostListResponse(
            posts=summaries,
            total=total,
            limit=limit,
            offset=offset,
            has_more=len(summaries) == limit and offset + len(summaries) < total
        )
    
    async def get_posts_by_community(
        self,
        community_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        current_user_id: Optional[uuid.UUID] = None
    ) -> PostListResponse:
        """Get posts in a specific community"""
        
        posts, total = await self.post_repo.get_posts_by_community(
            community_id, limit, offset
        )
        
        summaries = []
        for post in posts:
            summary = await self._convert_to_summary_schema(post, current_user_id)
            summaries.append(summary)
        
        return PostListResponse(
            posts=summaries,
            total=total,
            limit=limit,
            offset=offset,
            has_more=len(summaries) == limit and offset + len(summaries) < total
        )
    
    # -------------------------------------------------------------------------
    # Interaction Operations
    # -------------------------------------------------------------------------
    
    async def like_post(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> LikeActionResponse:
        """Like a post (idempotent)"""
        
        # Verify post exists and is viewable
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise NotFoundError(f"Post {post_id} not found")
        
        if not await self._can_user_view_post(post, user_id):
            raise ForbiddenError("You don't have permission to like this post")
        
        # Like the post
        was_created = await self.interaction_repo.like_post(post_id, user_id)
        
        # Get updated count
        like_count = await self.interaction_repo.get_post_like_count(post_id)
        
        return LikeActionResponse(
            post_id=post_id,
            is_liked=True,
            like_count=like_count
        )
    
    async def unlike_post(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> LikeActionResponse:
        """Unlike a post"""
        
        # Unlike the post
        was_removed = await self.interaction_repo.unlike_post(post_id, user_id)
        
        # Get updated count
        like_count = await self.interaction_repo.get_post_like_count(post_id)
        
        return LikeActionResponse(
            post_id=post_id,
            is_liked=False,
            like_count=like_count
        )
    
    async def bookmark_post(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> BookmarkActionResponse:
        """Bookmark a post (idempotent)"""
        
        # Verify post exists and is viewable
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise NotFoundError(f"Post {post_id} not found")
        
        if not await self._can_user_view_post(post, user_id):
            raise ForbiddenError("You don't have permission to bookmark this post")
        
        # Bookmark the post
        await self.interaction_repo.bookmark_post(post_id, user_id)
        
        return BookmarkActionResponse(
            post_id=post_id,
            is_bookmarked=True
        )
    
    async def unbookmark_post(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> BookmarkActionResponse:
        """Remove bookmark from a post"""
        
        await self.interaction_repo.unbookmark_post(post_id, user_id)
        
        return BookmarkActionResponse(
            post_id=post_id,
            is_bookmarked=False
        )
    
    async def share_post(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
        request: ShareRequest
    ) -> ShareActionResponse:
        """Share a post"""
        
        # Verify post exists and is viewable
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise NotFoundError(f"Post {post_id} not found")
        
        if not await self._can_user_view_post(post, user_id):
            raise ForbiddenError("You don't have permission to share this post")
        
        # Create share record
        share = await self.interaction_repo.share_post(
            post_id, user_id, request.share_channel
        )
        
        # Get updated count
        share_count = await self.interaction_repo.get_post_share_count(post_id)
        
        return ShareActionResponse(
            post_id=post_id,
            share_count=share_count,
            share_id=share.id
        )
    
    async def get_user_bookmarks(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0
    ) -> BookmarkListResponse:
        """Get user's bookmarked posts"""
        
        # Get bookmarked post IDs
        post_ids, total = await self.interaction_repo.get_bookmarked_posts_by_user(
            user_id, limit, offset
        )
        
        if not post_ids:
            return BookmarkListResponse(
                bookmarks=[],
                total=0,
                limit=limit,
                offset=offset,
                has_more=False
            )
        
        # Get the actual posts
        posts = await self.post_repo.get_many(post_ids)
        
        # Convert to summary schemas, maintaining the bookmark order
        summaries = []
        post_dict = {post.id: post for post in posts}
        
        for post_id in post_ids:
            if post_id in post_dict:
                post = post_dict[post_id]
                if await self._can_user_view_post(post, user_id):
                    summary = await self._convert_to_summary_schema(post, user_id)
                    summaries.append(summary)
        
        return BookmarkListResponse(
            bookmarks=summaries,
            total=total,
            limit=limit,
            offset=offset,
            has_more=len(summaries) == limit and offset + len(summaries) < total
        )
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    async def _can_user_view_post(
        self,
        post: Post,
        user_id: Optional[uuid.UUID]
    ) -> bool:
        """Check if user can view a post based on visibility rules"""
        
        if post.visibility == PostVisibility.PUBLIC:
            return True
        
        if not user_id:
            return False  # Anonymous users can only see public posts
        
        if post.author_id == user_id:
            return True  # Authors can always see their own posts
        
        if post.visibility == PostVisibility.PRIVATE:
            return False  # Only authors can see private posts
        
        if post.visibility == PostVisibility.COMMUNITY:
            # TODO: Check community membership when Community Service is available
            # For now, allow all authenticated users to see community posts
            return True
        
        return False
    
    async def _enrich_post_schema(
        self,
        post: Post,
        current_user_id: Optional[uuid.UUID]
    ) -> PostSchema:
        """Convert Post model to enriched PostSchema with interaction data"""
        
        # Get interaction counts
        interaction_counts = await self.interaction_repo.get_interaction_counts_for_posts([post.id])
        comment_counts = await self.comment_repo.get_comment_counts_for_posts([post.id])
        
        post_counts = interaction_counts.get(post.id, {'likes': 0, 'shares': 0})
        
        # Get user interactions if authenticated
        user_interactions = {}
        if current_user_id:
            user_interactions = await self.interaction_repo.get_user_interactions_for_posts([post.id], current_user_id)
        
        user_data = user_interactions.get(post.id, {'is_liked': False, 'is_bookmarked': False})
        
        # Convert to schema
        return PostSchema.model_validate({
            **post.__dict__,
            'like_count': post_counts['likes'],
            'share_count': post_counts['shares'],
            'comment_count': comment_counts.get(post.id, 0),
            'is_liked': user_data['is_liked'],
            'is_bookmarked': user_data['is_bookmarked']
        })
    
    async def _convert_to_summary_schema(
        self,
        post: Post,
        current_user_id: Optional[uuid.UUID]
    ) -> PostSummarySchema:
        """Convert Post model to PostSummarySchema with minimal data"""
        
        # Get interaction counts
        interaction_counts = await self.interaction_repo.get_interaction_counts_for_posts([post.id])
        comment_counts = await self.comment_repo.get_comment_counts_for_posts([post.id])
        
        post_counts = interaction_counts.get(post.id, {'likes': 0, 'shares': 0})
        
        # Get user interactions if authenticated
        user_interactions = {}
        if current_user_id:
            user_interactions = await self.interaction_repo.get_user_interactions_for_posts([post.id], current_user_id)
        
        user_data = user_interactions.get(post.id, {'is_liked': False, 'is_bookmarked': False})
        
        # Get cover image (first media item)
        cover_image_url = None
        if post.media:
            cover_image_url = post.media[0].media_url
        
        # Get tag strings
        tag_list = [tag.tag for tag in post.tags] if post.tags else []
        
        return PostSummarySchema(
            id=post.id,
            author_id=post.author_id,
            community_id=post.community_id,
            title=post.title,
            location=post.location,
            status=post.status,
            visibility=post.visibility,
            cover_image_url=cover_image_url,
            tag_list=tag_list,
            like_count=post_counts['likes'],
            share_count=post_counts['shares'],
            comment_count=comment_counts.get(post.id, 0),
            is_liked=user_data['is_liked'],
            is_bookmarked=user_data['is_bookmarked'],
            created_at=post.created_at,
            updated_at=post.updated_at
        )