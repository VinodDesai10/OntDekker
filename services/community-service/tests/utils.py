"""
Community Service — Test Utilities

Standalone helper functions and async ORM factory functions for building
Community Service test data.

Contents
--------
JWT / Auth helpers:
  build_jwt_token        — mint a signed JWT for any user payload
  make_user_payload      — construct a realistic JWT payload dict
  build_auth_headers     — convenience: returns {"Authorization": "Bearer <token>"}

Request body factories (return plain dicts for httpx json= param):
  make_community_payload          — valid CommunityCreateRequest body
  make_community_update_payload   — valid CommunityUpdateRequest body
  make_membership_payload         — valid JoinCommunityRequest body
  make_discussion_payload         — valid DiscussionCreateRequest body
  make_discussion_comment_payload — valid DiscussionCommentCreateRequest body
  make_rule_payload               — valid CommunityRuleCreateRequest body

ORM factory helpers (require a live db_session fixture from conftest.py):
  create_test_community   — persist a Community ORM object
  create_test_member      — persist a CommunityMember ORM object
  create_test_discussion  — persist a Discussion ORM object
  create_test_comment     — persist a DiscussionComment ORM object

None of the factory helpers test business logic.  They create valid model
state directly in the database for use in repository and service-layer tests.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from shared.utils.security import create_jwt_token
from shared.config import get_common_settings
from shared.constants.status import (
    CommunityStatus,
    CommunityVisibility,
    MemberRole,
    MembershipStatus,
    JoinRequestStatus,
)


# ─────────────────────────────────────────────────────────────────────────────
# JWT / Auth helpers
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
        user_id:    UUID for the user.  Defaults to a freshly generated one.
        email:      Email claim in the token.
        roles:      List of role strings (e.g. ``["user", "moderator"]``).
        expires_in: Token lifetime.  Defaults to 1 hour.

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
    Mint a signed JWT using the shared JWT_SECRET from CommonSettings.

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

        token = build_jwt_token()                           # generic test user
        token = build_jwt_token(user_id=some_uuid)          # specific user
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

    # Strip 'exp' — create_jwt_token adds its own expiry field.
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
    Return a complete Authorization header dict for the given user.

    Useful for tests that need a non-default test identity, e.g. to check
    that a second user cannot edit another user's community.

    Args:
        user_id: Optional specific user UUID.
        email:   Email claim.
        roles:   Role list.

    Returns:
        ``{"Authorization": "Bearer <token>"}``

    Example::

        other_headers = build_auth_headers(user_id=uuid.uuid4())
        response = await client.delete(
            f"/api/v1/communities/{community_id}",
            headers=other_headers,
        )
    """
    token = build_jwt_token(user_id=user_id, email=email, roles=roles)
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# Request body factories
# ─────────────────────────────────────────────────────────────────────────────

def make_community_payload(
    name: str = "Slow Travel Amsterdam",
    description: Optional[str] = "A community for slow travelers in Amsterdam.",
    location: Optional[str] = "Amsterdam, Netherlands",
    visibility: str = CommunityVisibility.PUBLIC,
    requires_approval: bool = False,
    **overrides: Any,
) -> Dict[str, Any]:
    """
    Build a valid ``CommunityCreateRequest`` body dict.

    All arguments are optional with sensible defaults::

        payload = make_community_payload()
        payload = make_community_payload(name="Private Hikers", visibility="PRIVATE")

    Args:
        name:              Community display name (3–100 chars).
        description:       Optional description (up to 2000 chars).
        location:          Optional location string (up to 255 chars).
        visibility:        ``"PUBLIC"`` | ``"PRIVATE"``.
        requires_approval: Whether members must be approved.
        **overrides:       Additional fields merged into the result.

    Returns:
        Dict ready for the ``json=`` parameter of an httpx request.
    """
    payload: Dict[str, Any] = {
        "name": name,
        "description": description,
        "location": location,
        "visibility": visibility,
        "requires_approval": requires_approval,
    }
    payload.update(overrides)
    return payload


def make_community_update_payload(
    name: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    visibility: Optional[str] = None,
    requires_approval: Optional[bool] = None,
    **overrides: Any,
) -> Dict[str, Any]:
    """
    Build a valid ``CommunityUpdateRequest`` body dict.

    Omits None values so only the provided fields are sent.  This matches
    how partial-update endpoints work (PATCH semantics).

    Args:
        name:              New display name (3–100 chars).
        description:       New description.
        location:          New location.
        visibility:        New visibility string.
        requires_approval: New approval requirement.
        **overrides:       Additional fields.

    Returns:
        Dict ready for the ``json=`` parameter of an httpx PATCH request.

    Example::

        payload = make_community_update_payload(name="Renamed Community")
    """
    payload: Dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if location is not None:
        payload["location"] = location
    if visibility is not None:
        payload["visibility"] = visibility
    if requires_approval is not None:
        payload["requires_approval"] = requires_approval
    payload.update(overrides)
    return payload


def make_membership_payload(
    message: Optional[str] = None,
    **overrides: Any,
) -> Dict[str, Any]:
    """
    Build a valid ``JoinCommunityRequest`` body dict.

    The message is optional — only relevant for approval-required communities.

    Args:
        message:   Optional message explaining why the user wants to join.
        **overrides: Additional fields.

    Returns:
        Dict ready for the ``json=`` parameter of an httpx POST request.

    Example::

        # Simple join (public community)
        payload = make_membership_payload()

        # Request to join with a message (private/approval-required)
        payload = make_membership_payload(message="I love slow travel!")
    """
    payload: Dict[str, Any] = {"message": message}
    payload.update(overrides)
    return payload


def make_discussion_payload(
    title: str = "Best slow travel routes in Europe",
    content: Optional[str] = "Let's discuss the most scenic routes across Europe.",
    **overrides: Any,
) -> Dict[str, Any]:
    """
    Build a valid ``DiscussionCreateRequest`` body dict.

    Args:
        title:     Discussion title (3–255 chars).
        content:   Optional discussion body (up to 10000 chars).
        **overrides: Additional fields.

    Returns:
        Dict ready for the ``json=`` parameter of an httpx POST request.

    Example::

        payload = make_discussion_payload()
        payload = make_discussion_payload(title="Short question", content=None)
    """
    payload: Dict[str, Any] = {
        "title": title,
        "content": content,
    }
    payload.update(overrides)
    return payload


def make_discussion_comment_payload(
    content: str = "Great discussion topic!",
    **overrides: Any,
) -> Dict[str, Any]:
    """
    Build a valid ``DiscussionCommentCreateRequest`` body dict.

    Community discussion comments are flat (no nesting), so there is no
    parent_comment_id field.

    Args:
        content:   Comment text (1–2000 chars, must not be blank).
        **overrides: Additional fields.

    Returns:
        Dict ready for the ``json=`` parameter of an httpx POST request.

    Example::

        payload = make_discussion_comment_payload()
        payload = make_discussion_comment_payload(content="I disagree!")
    """
    payload: Dict[str, Any] = {"content": content}
    payload.update(overrides)
    return payload


def make_rule_payload(
    title: str = "Be respectful",
    description: Optional[str] = "Treat all members with respect and kindness.",
    order_index: int = 1,
    **overrides: Any,
) -> Dict[str, Any]:
    """
    Build a valid ``CommunityRuleCreateRequest`` body dict.

    Args:
        title:        Rule title (3–255 chars).
        description:  Optional longer explanation (up to 1000 chars).
        order_index:  Display order (1-based).
        **overrides:  Additional fields.

    Returns:
        Dict ready for the ``json=`` parameter of an httpx POST request.

    Example::

        rule = make_rule_payload(title="No spam", order_index=2)
    """
    payload: Dict[str, Any] = {
        "title": title,
        "description": description,
        "order_index": order_index,
    }
    payload.update(overrides)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# ORM model factories (require a live db_session from conftest.py)
# ─────────────────────────────────────────────────────────────────────────────

def _make_slug(name: str) -> str:
    """
    Produce a deterministic slug from a community name for test use.

    Uses a fixed suffix derived from the name to avoid slug collisions between
    tests without adding network or DB round-trips.  Production slug generation
    lives in the service layer and is not replicated here.
    """
    base = name.lower().replace(" ", "-")
    suffix = str(uuid.uuid4())[:8]
    return f"{base}-{suffix}"


async def create_test_community(
    session,
    creator_id: Optional[uuid.UUID] = None,
    name: str = "Test Community",
    description: Optional[str] = "A community for testing.",
    location: Optional[str] = "Test City",
    visibility: str = CommunityVisibility.PUBLIC,
    status: str = CommunityStatus.ACTIVE,
    requires_approval: bool = False,
    member_count: int = 0,
    slug: Optional[str] = None,
):
    """
    Persist a ``Community`` ORM object directly via the test session.

    Use this when a test needs an existing community in the database without
    going through the HTTP endpoint (e.g. for repository or service-layer tests).

    Args:
        session:          AsyncSession from the ``db_session`` fixture.
        creator_id:       UUID of the creator.  Defaults to a fresh UUID.
        name:             Community name.
        description:      Optional description.
        location:         Optional location string.
        visibility:       CommunityVisibility value string.
        status:           CommunityStatus value string.
        requires_approval: Whether joining requires approval.
        member_count:     Initial denormalized member count.
        slug:             URL slug.  Defaults to a name-derived unique slug.

    Returns:
        Persisted ``Community`` ORM instance (with id populated).

    Example::

        async def test_something(db_session):
            from tests.conftest import TEST_USER_ID
            community = await create_test_community(db_session, creator_id=TEST_USER_ID)
            assert community.id is not None
    """
    from app.models.community import Community

    if creator_id is None:
        creator_id = uuid.uuid4()
    if slug is None:
        slug = _make_slug(name)

    community = Community(
        creator_id=creator_id,
        name=name,
        slug=slug,
        description=description,
        location=location,
        visibility=visibility,
        status=status,
        requires_approval=requires_approval,
        member_count=member_count,
    )
    session.add(community)
    await session.flush()
    await session.refresh(community)
    return community


async def create_test_member(
    session,
    community_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
    role: str = MemberRole.MEMBER,
    status: str = MembershipStatus.ACTIVE,
):
    """
    Persist a ``CommunityMember`` ORM object directly via the test session.

    Args:
        session:      AsyncSession from the ``db_session`` fixture.
        community_id: UUID of the community (must already exist).
        user_id:      UUID of the user.  Defaults to a fresh UUID.
        role:         MemberRole value string.
        status:       MembershipStatus value string.

    Returns:
        Persisted ``CommunityMember`` ORM instance.

    Example::

        member = await create_test_member(session, community_id=community.id)
    """
    from app.models.membership import CommunityMember

    if user_id is None:
        user_id = uuid.uuid4()

    member = CommunityMember(
        community_id=community_id,
        user_id=user_id,
        role=role,
        status=status,
    )
    session.add(member)
    await session.flush()
    await session.refresh(member)
    return member


async def create_test_discussion(
    session,
    community_id: uuid.UUID,
    author_id: Optional[uuid.UUID] = None,
    title: str = "Test Discussion",
    content: Optional[str] = "Test discussion content.",
    comment_count: int = 0,
):
    """
    Persist a ``Discussion`` ORM object directly via the test session.

    Args:
        session:       AsyncSession from the ``db_session`` fixture.
        community_id:  UUID of the parent community (must already exist).
        author_id:     UUID of the discussion author.  Defaults to a fresh UUID.
        title:         Discussion title.
        content:       Optional discussion body.
        comment_count: Initial denormalized comment count.

    Returns:
        Persisted ``Discussion`` ORM instance.

    Example::

        discussion = await create_test_discussion(
            db_session,
            community_id=community.id,
            author_id=TEST_USER_ID,
        )
    """
    from app.models.discussion import Discussion

    if author_id is None:
        author_id = uuid.uuid4()

    discussion = Discussion(
        community_id=community_id,
        author_id=author_id,
        title=title,
        content=content,
        comment_count=comment_count,
    )
    session.add(discussion)
    await session.flush()
    await session.refresh(discussion)
    return discussion


async def create_test_comment(
    session,
    discussion_id: uuid.UUID,
    author_id: Optional[uuid.UUID] = None,
    content: str = "Test comment content.",
):
    """
    Persist a ``DiscussionComment`` ORM object directly via the test session.

    Community discussion comments are flat — no parent_comment_id.

    Args:
        session:       AsyncSession from the ``db_session`` fixture.
        discussion_id: UUID of the parent discussion (must already exist).
        author_id:     UUID of the comment author.  Defaults to a fresh UUID.
        content:       Comment text (must be non-blank — enforced by DB constraint).

    Returns:
        Persisted ``DiscussionComment`` ORM instance.

    Example::

        comment = await create_test_comment(
            db_session,
            discussion_id=discussion.id,
            author_id=TEST_USER_ID,
        )
    """
    from app.models.discussion import DiscussionComment

    if author_id is None:
        author_id = uuid.uuid4()

    comment = DiscussionComment(
        discussion_id=discussion_id,
        author_id=author_id,
        content=content,
    )
    session.add(comment)
    await session.flush()
    await session.refresh(comment)
    return comment
