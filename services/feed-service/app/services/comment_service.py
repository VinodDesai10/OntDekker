"""
Feed Service — Comment Service

Business logic for comment management.
"""

import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import CommentRepository, PostRepository
from app.schemas.feed import (
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentSchema,
    CommentListResponse,
    CommentQueryParams,
)
from shared.exceptions import NotFoundError, ForbiddenError, ValidationError


class CommentService:
    """Business logic for comment management"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.comment_repo = CommentRepository(session)
        self.post_repo = PostRepository(session)
    
    async def create_comment(
        self,
        post_id: uuid.UUID,
        request: CommentCreateRequest,
        author_id: uuid.UUID
    ) -> CommentSchema:
        """Create a new comment with validation"""
        
        # Verify post exists and user can comment
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise NotFoundError(f"Post {post_id} not found")
        
        comment = await self.comment_repo.create(
            post_id=post_id,
            author_id=author_id,
            content=request.content,
            parent_comment_id=request.parent_comment_id
        )
        
        if not comment:
            raise ValidationError("Failed to create comment")
        
        return CommentSchema.model_validate(comment)
    
    async def update_comment(
        self,
        comment_id: uuid.UUID,
        request: CommentUpdateRequest,
        current_user_id: uuid.UUID
    ) -> CommentSchema:
        """Update a comment with authorization"""
        
        # Check if user can modify this comment
        can_modify = await self.comment_repo.can_user_modify_comment(comment_id, current_user_id)
        if not can_modify:
            raise ForbiddenError("You can only edit your own comments")
        
        comment = await self.comment_repo.update(comment_id, request.content)
        if not comment:
            raise NotFoundError(f"Comment {comment_id} not found")
        
        return CommentSchema.model_validate(comment)
    
    async def delete_comment(
        self,
        comment_id: uuid.UUID,
        current_user_id: uuid.UUID
    ) -> bool:
        """Delete a comment with authorization"""
        
        can_modify = await self.comment_repo.can_user_modify_comment(comment_id, current_user_id)
        if not can_modify:
            raise ForbiddenError("You can only delete your own comments")
        
        return await self.comment_repo.soft_delete(comment_id, current_user_id)
    
    async def get_post_comments(
        self,
        post_id: uuid.UUID,
        params: CommentQueryParams
    ) -> CommentListResponse:
        """Get comments for a post"""
        
        comments, total = await self.comment_repo.get_comments_for_post(
            post_id, params.limit, params.offset, params.include_replies
        )
        
        comment_schemas = [CommentSchema.model_validate(c) for c in comments]
        
        return CommentListResponse(
            comments=comment_schemas,
            total=total,
            limit=params.limit,
            offset=params.offset,
            has_more=len(comment_schemas) == params.limit
        )