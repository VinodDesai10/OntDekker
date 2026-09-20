"""
Feed Service — Post API Routes

REST API endpoints for the Feed Service following the agreed API contract.
"""

import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import PostService, CommentService
from app.schemas.feed import (
    PostCreateRequest,
    PostUpdateRequest,
    PostSchema,
    PostListResponse,
    PostQueryParams,
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentSchema,
    CommentListResponse,
    CommentQueryParams,
)
from shared.dependencies import get_db, get_current_user, optional_current_user
from shared.exceptions import NotFoundError, ForbiddenError, ValidationError

router = APIRouter(prefix="/api/v1/feed", tags=["Feed"])


def _user_id(payload: Dict[str, Any]) -> uuid.UUID:
    """Extract user UUID from JWT payload sub claim."""
    return uuid.UUID(payload["sub"])


# -------------------------------------------------------------------------
# Post CRUD Endpoints
# -------------------------------------------------------------------------

@router.post("/posts", response_model=PostSchema, status_code=status.HTTP_201_CREATED)
@router.post("/stories", response_model=PostSchema, status_code=status.HTTP_201_CREATED)
async def create_post(
    request: PostCreateRequest,
    authorization: Optional[str] = Header(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new travel post.

    Author is always derived from the JWT sub claim — never from the request body.

    Visibility rules enforced by the service layer:
      PUBLIC   → community_id must be null
      COMMUNITY → community_id required; user must be an active member
      PRIVATE  → community_id must be null
    """
    service = PostService(db)
    try:
        return await service.create_post(request, _user_id(current_user), authorization)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/posts", response_model=PostListResponse)
@router.get("/stories", response_model=PostListResponse)
async def list_posts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    author_id: Optional[uuid.UUID] = Query(None),
    community_id: Optional[uuid.UUID] = Query(None),
    expedition_id: Optional[uuid.UUID] = Query(None),
    tags: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List posts with filtering and pagination.

    When the caller is authenticated the service layer automatically:
    - Excludes the caller's own posts (own-post exclusion via JWT sub).
    - Fetches the caller's community memberships and includes community posts
      from those communities only.
    """
    params = PostQueryParams(
        limit=limit,
        offset=offset,
        author_id=author_id,
        community_id=community_id,
        expedition_id=expedition_id,
        tags=tags,
        location=location,
    )
    service = PostService(db)
    user_id = _user_id(current_user) if current_user else None
    return await service.list_posts(params, user_id, authorization)


@router.get("/posts/{post_id}", response_model=PostSchema)
@router.get("/stories/{post_id}", response_model=PostSchema)
async def get_post(
    post_id: uuid.UUID,
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific post by ID."""
    service = PostService(db)
    try:
        user_id = _user_id(current_user) if current_user else None
        return await service.get_post(post_id, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/posts/{post_id}", response_model=PostSchema)
@router.put("/stories/{post_id}", response_model=PostSchema)
async def update_post(
    post_id: uuid.UUID,
    request: PostUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a post (author only)."""
    service = PostService(db)
    try:
        return await service.update_post(post_id, request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/stories/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a post (author only)."""
    service = PostService(db)
    try:
        success = await service.delete_post(post_id, _user_id(current_user))
        if not success:
            raise HTTPException(status_code=404, detail="Post not found")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


# -------------------------------------------------------------------------
# User-specific and Community-specific Post Endpoints
# -------------------------------------------------------------------------

@router.get("/me/posts", response_model=PostListResponse)
async def get_my_posts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the authenticated user's own posts (Global + Community).

    Author identity is always derived from the JWT sub claim — the caller
    cannot supply an arbitrary author_id through query parameters.

    Returns all PUBLISHED posts authored by the current user, including:
      - PUBLIC (Global) posts
      - COMMUNITY posts

    This endpoint is intended for the user's Profile → My Posts section.
    It is distinct from GET /users/{user_id}/posts (public profile) in that:
      - No viewer_id ambiguity: the JWT *is* the author.
      - Returns the full own-view (same as viewer==author in get_posts_by_author).
    """
    author_id = _user_id(current_user)
    service = PostService(db)
    # Pass author_id as both the target author and current_user_id so the
    # repository applies the "viewing own posts" path (shows all PUBLISHED posts).
    return await service.get_posts_by_author(author_id, limit, offset, author_id)


@router.get("/users/{user_id}/posts", response_model=PostListResponse)
async def get_user_posts(
    user_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get posts by a specific user."""
    service = PostService(db)
    viewer_id = _user_id(current_user) if current_user else None
    return await service.get_posts_by_author(user_id, limit, offset, viewer_id)


@router.get("/communities/{community_id}/posts", response_model=PostListResponse)
async def get_community_posts(
    community_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[Dict[str, Any]] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get posts in a specific community."""
    service = PostService(db)
    viewer_id = _user_id(current_user) if current_user else None
    return await service.get_posts_by_community(community_id, limit, offset, viewer_id)


# -------------------------------------------------------------------------
# Comment Endpoints (kept in posts.py for route co-location)
# -------------------------------------------------------------------------

@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    post_id: uuid.UUID,
    request: CommentCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a comment on a post."""
    service = CommentService(db)
    try:
        return await service.create_comment(post_id, request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/posts/{post_id}/comments", response_model=CommentListResponse)
async def get_post_comments(
    post_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    include_replies: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Get comments for a post."""
    params = CommentQueryParams(
        limit=limit,
        offset=offset,
        include_replies=include_replies,
    )
    service = CommentService(db)
    return await service.get_post_comments(post_id, params)


@router.put("/comments/{comment_id}", response_model=CommentSchema)
async def update_comment(
    comment_id: uuid.UUID,
    request: CommentUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a comment (author only)."""
    service = CommentService(db)
    try:
        return await service.update_comment(comment_id, request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a comment (author only)."""
    service = CommentService(db)
    try:
        success = await service.delete_comment(comment_id, _user_id(current_user))
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post(
    "/comments/{comment_id}/reply",
    response_model=CommentSchema,
    status_code=status.HTTP_201_CREATED,
)
async def reply_to_comment(
    comment_id: uuid.UUID,
    request: CommentCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a reply to a comment (one level only)."""
    from app.repositories import CommentRepository

    comment_repo = CommentRepository(db)
    parent_comment = await comment_repo.get_by_id(comment_id)
    if not parent_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    reply_request = CommentCreateRequest(
        content=request.content,
        parent_comment_id=comment_id,
    )
    service = CommentService(db)
    try:
        return await service.create_comment(parent_comment.post_id, reply_request, _user_id(current_user))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
