"""
Feed Service — Test Utilities

Standalone helper functions for building test data.  These are plain functions
(not pytest fixtures) so they can be called anywhere without fixture injection.

Contents
--------
- ``build_jwt_token``         — mint a signed JWT for any user payload.
- ``make_user_payload``       — construct a realistic JWT payload dict.
- ``make_post_payload``       — build a valid PostCreateRequest body dict.
- ``make_comment_payload``    — build a valid CommentCreateRequest body dict.
- ``make_share_payload``      — build a valid ShareRequest body dict.

All factory helpers return plain dicts so they can be passed directly to
httpx client methods (e.g. ``await client.post(..., json=make_post_payload())``).

None of these helpers persist anything to the database. For ORM-level object
creation, use the ``db_session`` fixture from conftest.py and instantiate
models directly.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from shared.utils.security import create_jwt_token
from shared.config import get_common_settings
from shared.constants.status import PostStatus, PostVisibility


# ─────────────────────────────────────────────────────────────────────────────
# JWT token helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_user_payload(
    user_id: Optional[uuid.UUID] = None,
    email: str = "test@ontdekker.test",
    roles: Optional[List[str]] = None,
    expires_in: timedelta = timedelta(hours=1),
) -> Dict[str, Any]:
    """
    Return a JWT payload dict representing a synthetic user.

    Args:
        user_id:    UUID for the user. Defaults to a freshly generated one.
        email:      Email claim in the token. Defaults to a placeholder address.
        roles:      List of role strings (e.g. ``["user", "moderator"]``).
        expires_in: Token lifetime. Defaults to 1 hour.

    Returns:
        Dict suitable for passing to :func:`build_jwt_token`.

    Example::

        payload = make_user_payload(roles=["user"])
        token = build_jwt_token(payload)
    """
    if user_id is None:
        user_id = uuid.uuid4()
    if roles is None:
        roles = ["user"]

    expiry = datetime.now(timezone.utc) + expires_in
    return {
        "sub": str(user_id),
        "email": email,
        "roles": roles,
        "exp": int(expiry.timestamp()),
    }


def build_jwt_token(
    payload: Optional[Dict[str, Any]] = None,
    *,
    user_id: Optional[uuid.UUID] = None,
    email: str = "test@ontdekker.test",
    roles: Optional[List[str]] = None,
    expires_in: timedelta = timedelta(hours=1),
) -> str:
    """
    Mint a signed JWT using the test JWT_SECRET from shared settings.

    You can pass an explicit ``payload`` dict *or* use the convenience keyword
    arguments which are forwarded to :func:`make_user_payload`.

    Args:
        payload:    Full payload dict (overrides keyword args if provided).
        user_id:    UUID for the user (used when ``payload`` is None).
        email:      Email claim (used when ``payload`` is None).
        roles:      Role list (used when ``payload`` is None).
        expires_in: Token lifetime.

    Returns:
        Signed JWT string.

    Example::

        token = build_jwt_token()                           # anonymous test user
        token = build_jwt_token(user_id=uuid.uuid4())       # specific user
        headers = {"Authorization": f"Bearer {token}"}
    """
    settings = get_common_settings()

    if payload is None:
        payload = make_user_payload(
            user_id=user_id,
            email=email,
            roles=roles,
            expires_in=expires_in,
        )

    # Strip 'exp' from data dict — create_jwt_token adds its own expiry.
    data = {k: v for k, v in payload.items() if k != "exp"}

    return create_jwt_token(
        data=data,
        secret_key=settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
        expires_delta=expires_in,
    )


def build_auth_headers(
    user_id: Optional[uuid.UUID] = None,
    email: str = "test@ontdekker.test",
    roles: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Convenience wrapper that returns a complete Authorization header dict.

    Args:
        user_id: Optional specific user UUID.
        email:   Email claim.
        roles:   Role list.

    Returns:
        ``{"Authorization": "Bearer <token>"}``

    Example::

        other_user_headers = build_auth_headers(user_id=uuid.uuid4())
        response = await client.delete(f"/api/v1/feed/posts/{post_id}",
                                       headers=other_user_headers)
    """
    token = build_jwt_token(user_id=user_id, email=email, roles=roles)
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# Request body factories
# ─────────────────────────────────────────────────────────────────────────────

def make_post_payload(
    title: str = "Test Travel Post",
    content: Optional[str] = "This is a test post about travel.",
    location: Optional[str] = "Amsterdam, Netherlands",
    tags: Optional[List[str]] = None,
    visibility: str = PostVisibility.PUBLIC,
    community_id: Optional[uuid.UUID] = None,
    expedition_id: Optional[uuid.UUID] = None,
    **overrides: Any,
) -> Dict[str, Any]:
    """
    Build a valid ``PostCreateRequest`` body dict.

    All arguments are optional with sensible defaults so the simplest call is::

        payload = make_post_payload()

    Override specific fields for targeted tests::

        payload = make_post_payload(title="Short", visibility="PRIVATE", tags=["hiking"])

    Args:
        title:          Post title (1–255 chars).
        content:        Post body text.
        location:       Human-readable location string.
        tags:           List of tag strings (lowercase, 1–50 chars each).
        visibility:     ``"PUBLIC"`` | ``"COMMUNITY"`` | ``"PRIVATE"``.
        community_id:   Optional community UUID.
        expedition_id:  Optional expedition UUID.
        **overrides:    Any additional fields to merge into the result.

    Returns:
        Dict ready for ``json=`` parameter of an httpx request.
    """
    if tags is None:
        tags = ["travel", "adventure"]

    payload: Dict[str, Any] = {
        "title": title,
        "content": content,
        "location": location,
        "tags": tags,
        "visibility": visibility,
        "community_id": str(community_id) if community_id else None,
        "expedition_id": str(expedition_id) if expedition_id else None,
    }
    payload.update(overrides)
    return payload


def make_comment_payload(
    content: str = "This is a test comment.",
    parent_comment_id: Optional[uuid.UUID] = None,
    **overrides: Any,
) -> Dict[str, Any]:
    """
    Build a valid ``CommentCreateRequest`` body dict.

    Args:
        content:           Comment text (1–1000 chars).
        parent_comment_id: Set to create a reply to an existing comment.
        **overrides:       Additional fields.

    Returns:
        Dict ready for ``json=`` parameter of an httpx request.

    Example::

        # Top-level comment
        payload = make_comment_payload()

        # Reply to a specific comment
        payload = make_comment_payload(parent_comment_id=some_comment_id)
    """
    payload: Dict[str, Any] = {
        "content": content,
        "parent_comment_id": str(parent_comment_id) if parent_comment_id else None,
    }
    payload.update(overrides)
    return payload


def make_share_payload(
    share_channel: Optional[str] = None,
    **overrides: Any,
) -> Dict[str, Any]:
    """
    Build a valid ``ShareRequest`` body dict.

    Args:
        share_channel: Optional platform name (e.g. ``"twitter"``).
        **overrides:   Additional fields.

    Returns:
        Dict ready for ``json=`` parameter of an httpx request.
    """
    payload: Dict[str, Any] = {
        "share_channel": share_channel,
    }
    payload.update(overrides)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# ORM model factories (require a live db_session fixture from conftest.py)
# ─────────────────────────────────────────────────────────────────────────────

async def create_test_post(
    session,
    author_id: Optional[uuid.UUID] = None,
    title: str = "Test Post",
    content: str = "Test content.",
    location: Optional[str] = "Amsterdam",
    visibility: str = PostVisibility.PUBLIC,
    status: str = PostStatus.PUBLISHED,
    community_id: Optional[uuid.UUID] = None,
    expedition_id: Optional[uuid.UUID] = None,
    tags: Optional[List[str]] = None,
):
    """
    Persist a ``Post`` ORM object directly via the test session.

    Use this when a test needs an existing post in the database without going
    through the HTTP endpoint (e.g. for repository or service-layer tests).

    Args:
        session:      AsyncSession from the ``db_session`` fixture.
        author_id:    UUID of the post author. Defaults to a fresh UUID.
        title:        Post title.
        content:      Post body.
        location:     Location string.
        visibility:   PostVisibility value string.
        status:       PostStatus value string.
        community_id: Optional community UUID.
        expedition_id: Optional expedition UUID.
        tags:         List of tag strings to attach.

    Returns:
        Persisted ``Post`` ORM instance (with id populated).

    Example::

        async def test_something(db_session):
            post = await create_test_post(db_session, author_id=TEST_USER_ID)
            assert post.id is not None
    """
    from app.models.post import Post, PostTag

    if author_id is None:
        author_id = uuid.uuid4()

    post = Post(
        author_id=author_id,
        title=title,
        content=content,
        location=location,
        visibility=visibility,
        status=status,
        community_id=community_id,
        expedition_id=expedition_id,
    )
    session.add(post)
    await session.flush()  # Populate post.id without committing.

    if tags:
        for tag_value in tags:
            tag = PostTag(post_id=post.id, tag=tag_value.strip().lower())
            session.add(tag)
        await session.flush()

    await session.refresh(post)
    return post


async def create_test_comment(
    session,
    post_id: uuid.UUID,
    author_id: Optional[uuid.UUID] = None,
    content: str = "Test comment content.",
    parent_comment_id: Optional[uuid.UUID] = None,
):
    """
    Persist a ``Comment`` ORM object directly via the test session.

    Args:
        session:           AsyncSession from the ``db_session`` fixture.
        post_id:           UUID of the parent post.
        author_id:         UUID of the comment author. Defaults to a fresh UUID.
        content:           Comment text.
        parent_comment_id: Optional parent comment UUID for replies.

    Returns:
        Persisted ``Comment`` ORM instance.
    """
    from app.models.comment import Comment

    if author_id is None:
        author_id = uuid.uuid4()

    comment = Comment(
        post_id=post_id,
        author_id=author_id,
        content=content,
        parent_comment_id=parent_comment_id,
    )
    session.add(comment)
    await session.flush()
    await session.refresh(comment)
    return comment
