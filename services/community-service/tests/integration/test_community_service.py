"""
CP-16E.3 — CommunityService Integration Tests

Validates service-layer behaviour for CommunityService.
Tests exercise the full Service → Repository → SQLite stack.
No HTTP requests; no mocking of repository methods.

Public methods under test:
  - create_community
  - get_community
  - get_community_by_slug
  - list_communities
  - update_community
  - delete_community
  - archive_community
"""

import uuid
import pytest

from app.services.community_service import CommunityService
from app.schemas.community import (
    CommunityCreateRequest,
    CommunityUpdateRequest,
    CommunityQueryParams,
    CommunitySchema,
    CommunityListResponse,
)
from shared.constants.status import (
    CommunityStatus,
    CommunityVisibility,
    MemberRole,
    MembershipStatus,
)
from shared.exceptions import NotFoundError, ForbiddenError

from tests.conftest import TEST_USER_ID, TEST_OTHER_USER_ID
from tests.utils import create_test_community, create_test_member


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc(session) -> CommunityService:
    return CommunityService(session)


def _create_request(
    name: str = "Test Community",
    description: str = "A test description.",
    location: str = "Amsterdam",
    visibility: CommunityVisibility = CommunityVisibility.PUBLIC,
    requires_approval: bool = False,
) -> CommunityCreateRequest:
    return CommunityCreateRequest(
        name=name,
        description=description,
        location=location,
        visibility=visibility,
        requires_approval=requires_approval,
    )


def _update_request(**kwargs) -> CommunityUpdateRequest:
    return CommunityUpdateRequest(**kwargs)


def _query_params(**kwargs) -> CommunityQueryParams:
    defaults = {"limit": 20, "offset": 0}
    defaults.update(kwargs)
    return CommunityQueryParams(**defaults)


# ===========================================================================
# create_community
# ===========================================================================

@pytest.mark.integration
async def test_create_community_returns_schema(db_session):
    """create_community() returns a CommunitySchema instance."""
    svc = _svc(db_session)
    result = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    assert isinstance(result, CommunitySchema)


@pytest.mark.integration
async def test_create_community_fields_are_correct(db_session):
    """create_community() stores and returns the correct field values."""
    svc = _svc(db_session)
    result = await svc.create_community(
        _create_request(
            name="Slow Travel Europe",
            description="For slow travelers.",
            location="Europe",
            visibility=CommunityVisibility.PUBLIC,
            requires_approval=False,
        ),
        creator_id=TEST_USER_ID,
    )

    assert result.name == "Slow Travel Europe"
    assert result.description == "For slow travelers."
    assert result.location == "Europe"
    assert result.visibility == CommunityVisibility.PUBLIC
    assert result.requires_approval is False
    assert result.creator_id == TEST_USER_ID
    assert result.id is not None
    assert result.slug is not None


@pytest.mark.integration
async def test_create_community_creator_is_member(db_session):
    """create_community() automatically makes the creator an OWNER member."""
    svc = _svc(db_session)
    result = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    # The returned schema should reflect creator as a member with OWNER role
    assert result.is_member is True
    assert result.current_user_role == MemberRole.OWNER


@pytest.mark.integration
async def test_create_community_member_count_is_one(db_session):
    """create_community() initialises member_count to 1 (the creator)."""
    svc = _svc(db_session)
    result = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    assert result.member_count == 1


@pytest.mark.integration
async def test_create_community_default_status_is_active(db_session):
    """create_community() sets status=ACTIVE by default."""
    svc = _svc(db_session)
    result = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    assert result.status == CommunityStatus.ACTIVE


@pytest.mark.integration
async def test_create_community_is_not_deleted(db_session):
    """A freshly created community is not soft-deleted."""
    svc = _svc(db_session)
    result = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    assert result.is_deleted is False


@pytest.mark.integration
async def test_create_community_private_visibility(db_session):
    """create_community() stores PRIVATE visibility correctly."""
    svc = _svc(db_session)
    result = await svc.create_community(
        _create_request(visibility=CommunityVisibility.PRIVATE),
        creator_id=TEST_USER_ID,
    )

    assert result.visibility == CommunityVisibility.PRIVATE


@pytest.mark.integration
async def test_create_community_requires_approval(db_session):
    """create_community() stores requires_approval=True correctly."""
    svc = _svc(db_session)
    result = await svc.create_community(
        _create_request(requires_approval=True),
        creator_id=TEST_USER_ID,
    )

    assert result.requires_approval is True


@pytest.mark.integration
async def test_create_community_generates_unique_slugs(db_session):
    """Two communities with the same name receive distinct slugs."""
    svc = _svc(db_session)
    c1 = await svc.create_community(_create_request(name="Slug Test"), creator_id=TEST_USER_ID)
    c2 = await svc.create_community(
        _create_request(name="Slug Test"), creator_id=TEST_OTHER_USER_ID
    )

    assert c1.slug != c2.slug


# ===========================================================================
# get_community
# ===========================================================================

@pytest.mark.integration
async def test_get_community_returns_schema(db_session):
    """get_community() returns a CommunitySchema for a known community."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    result = await svc.get_community(created.id, current_user_id=TEST_USER_ID)

    assert isinstance(result, CommunitySchema)
    assert result.id == created.id


@pytest.mark.integration
async def test_get_community_not_found_raises(db_session):
    """get_community() raises NotFoundError for an unknown community ID."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.get_community(uuid.uuid4())


@pytest.mark.integration
async def test_get_community_public_no_auth(db_session):
    """get_community() allows unauthenticated access to PUBLIC communities."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(visibility=CommunityVisibility.PUBLIC),
        creator_id=TEST_USER_ID,
    )

    result = await svc.get_community(created.id, current_user_id=None)

    assert result.id == created.id
    assert result.is_member is False
    assert result.current_user_role is None


@pytest.mark.integration
async def test_get_community_private_unauthenticated_raises(db_session):
    """get_community() raises ForbiddenError for PRIVATE community without user ID."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(visibility=CommunityVisibility.PRIVATE),
        creator_id=TEST_USER_ID,
    )

    with pytest.raises(ForbiddenError):
        await svc.get_community(created.id, current_user_id=None)


@pytest.mark.integration
async def test_get_community_private_non_member_raises(db_session):
    """get_community() raises ForbiddenError for PRIVATE community if user is not a member."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(visibility=CommunityVisibility.PRIVATE),
        creator_id=TEST_USER_ID,
    )

    with pytest.raises(ForbiddenError):
        await svc.get_community(created.id, current_user_id=TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_get_community_private_member_succeeds(db_session):
    """get_community() returns schema for PRIVATE community if user is an active member."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(visibility=CommunityVisibility.PRIVATE),
        creator_id=TEST_USER_ID,
    )
    # Add other user as a regular member directly
    await create_test_member(
        db_session,
        community_id=created.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )

    result = await svc.get_community(created.id, current_user_id=TEST_OTHER_USER_ID)

    assert result.id == created.id
    assert result.is_member is True


@pytest.mark.integration
async def test_get_community_returns_creator_role(db_session):
    """get_community() includes current_user_role=OWNER for the creator."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    result = await svc.get_community(created.id, current_user_id=TEST_USER_ID)

    assert result.current_user_role == MemberRole.OWNER
    assert result.is_member is True


# ===========================================================================
# get_community_by_slug
# ===========================================================================

@pytest.mark.integration
async def test_get_community_by_slug_returns_schema(db_session):
    """get_community_by_slug() returns a CommunitySchema for a valid slug."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    result = await svc.get_community_by_slug(created.slug, current_user_id=TEST_USER_ID)

    assert result.id == created.id
    assert result.slug == created.slug


@pytest.mark.integration
async def test_get_community_by_slug_not_found_raises(db_session):
    """get_community_by_slug() raises NotFoundError for an unknown slug."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.get_community_by_slug("slug-that-does-not-exist")


@pytest.mark.integration
async def test_get_community_by_slug_private_non_member_raises(db_session):
    """get_community_by_slug() raises ForbiddenError for PRIVATE community if user is not a member."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(visibility=CommunityVisibility.PRIVATE),
        creator_id=TEST_USER_ID,
    )

    with pytest.raises(ForbiddenError):
        await svc.get_community_by_slug(created.slug, current_user_id=TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_get_community_by_slug_private_member_succeeds(db_session):
    """get_community_by_slug() allows member access to PRIVATE community."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(visibility=CommunityVisibility.PRIVATE),
        creator_id=TEST_USER_ID,
    )

    # The creator is always a member
    result = await svc.get_community_by_slug(created.slug, current_user_id=TEST_USER_ID)
    assert result.id == created.id


# ===========================================================================
# list_communities
# ===========================================================================

@pytest.mark.integration
async def test_list_communities_returns_response(db_session):
    """list_communities() returns a CommunityListResponse."""
    svc = _svc(db_session)
    await svc.create_community(_create_request(name="List A"), creator_id=TEST_USER_ID)

    result = await svc.list_communities(_query_params())

    assert isinstance(result, CommunityListResponse)
    assert result.total >= 1


@pytest.mark.integration
async def test_list_communities_includes_created_community(db_session):
    """list_communities() includes a recently created community in results."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(name="Listing Target"), creator_id=TEST_USER_ID
    )

    result = await svc.list_communities(_query_params())

    ids = [c.id for c in result.communities]
    assert created.id in ids


@pytest.mark.integration
async def test_list_communities_unauthenticated_excludes_private(db_session):
    """list_communities() hides PRIVATE communities from unauthenticated callers."""
    svc = _svc(db_session)
    private = await svc.create_community(
        _create_request(name="Secret Society", visibility=CommunityVisibility.PRIVATE),
        creator_id=TEST_USER_ID,
    )

    result = await svc.list_communities(_query_params(), current_user_id=None)

    ids = [c.id for c in result.communities]
    assert private.id not in ids


@pytest.mark.integration
async def test_list_communities_authenticated_includes_private(db_session):
    """list_communities() may include PRIVATE communities for authenticated users."""
    svc = _svc(db_session)
    private = await svc.create_community(
        _create_request(name="Members Only", visibility=CommunityVisibility.PRIVATE),
        creator_id=TEST_USER_ID,
    )

    result = await svc.list_communities(_query_params(), current_user_id=TEST_USER_ID)

    ids = [c.id for c in result.communities]
    assert private.id in ids


@pytest.mark.integration
async def test_list_communities_pagination_limit(db_session):
    """list_communities() respects the limit parameter."""
    svc = _svc(db_session)
    for i in range(5):
        await svc.create_community(
            _create_request(name=f"Paginate {i}"), creator_id=TEST_USER_ID
        )

    result = await svc.list_communities(_query_params(limit=2, offset=0))

    assert len(result.communities) <= 2
    assert result.limit == 2


@pytest.mark.integration
async def test_list_communities_pagination_offset(db_session):
    """list_communities() offset skips early results."""
    svc = _svc(db_session)
    for i in range(4):
        await svc.create_community(
            _create_request(name=f"Offset Test {i}"), creator_id=TEST_USER_ID
        )

    result_all = await svc.list_communities(_query_params(limit=10, offset=0))
    result_offset = await svc.list_communities(_query_params(limit=10, offset=2))

    assert len(result_offset.communities) == result_all.total - 2


@pytest.mark.integration
async def test_list_communities_search_filter(db_session):
    """list_communities() filters by the search parameter (name/description)."""
    svc = _svc(db_session)
    await svc.create_community(
        _create_request(name="Amsterdam Hikers"), creator_id=TEST_USER_ID
    )
    await svc.create_community(
        _create_request(name="Paris Cyclists"), creator_id=TEST_OTHER_USER_ID
    )

    result = await svc.list_communities(
        _query_params(search="Amsterdam"), current_user_id=TEST_USER_ID
    )

    assert all("amsterdam" in c.name.lower() for c in result.communities)


@pytest.mark.integration
async def test_list_communities_location_filter(db_session):
    """list_communities() filters by location (partial match)."""
    svc = _svc(db_session)
    await svc.create_community(
        _create_request(name="Loc Test A", location="Berlin, Germany"),
        creator_id=TEST_USER_ID,
    )
    await svc.create_community(
        _create_request(name="Loc Test B", location="Tokyo, Japan"),
        creator_id=TEST_OTHER_USER_ID,
    )

    result = await svc.list_communities(
        _query_params(location="Berlin"), current_user_id=TEST_USER_ID
    )

    locs = [c.location for c in result.communities if c.location]
    assert all("Berlin" in loc for loc in locs)


@pytest.mark.integration
async def test_list_communities_is_member_flag(db_session):
    """list_communities() sets is_member=True for communities the user belongs to."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(name="Member Flag Test"), creator_id=TEST_USER_ID
    )

    result = await svc.list_communities(_query_params(), current_user_id=TEST_USER_ID)

    matched = next((c for c in result.communities if c.id == created.id), None)
    assert matched is not None
    assert matched.is_member is True


@pytest.mark.integration
async def test_list_communities_excludes_deleted(db_session):
    """list_communities() does not return soft-deleted communities."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(name="To Be Deleted"), creator_id=TEST_USER_ID
    )
    await svc.delete_community(created.id, current_user_id=TEST_USER_ID)

    result = await svc.list_communities(_query_params(), current_user_id=TEST_USER_ID)

    ids = [c.id for c in result.communities]
    assert created.id not in ids


# ===========================================================================
# update_community
# ===========================================================================

@pytest.mark.integration
async def test_update_community_returns_updated_schema(db_session):
    """update_community() returns a CommunitySchema with the new values."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    result = await svc.update_community(
        created.id,
        _update_request(name="Updated Name"),
        current_user_id=TEST_USER_ID,
    )

    assert isinstance(result, CommunitySchema)
    assert result.name == "Updated Name"


@pytest.mark.integration
async def test_update_community_partial_update(db_session):
    """update_community() only changes the provided fields; others are unchanged."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(description="Original desc", location="Original city"),
        creator_id=TEST_USER_ID,
    )

    result = await svc.update_community(
        created.id,
        _update_request(name="New Name Only"),
        current_user_id=TEST_USER_ID,
    )

    assert result.name == "New Name Only"
    assert result.location == "Original city"


@pytest.mark.integration
async def test_update_community_not_found_raises(db_session):
    """update_community() raises NotFoundError for an unknown community ID."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.update_community(
            uuid.uuid4(),
            _update_request(name="Ghost"),
            current_user_id=TEST_USER_ID,
        )


@pytest.mark.integration
async def test_update_community_forbidden_for_non_owner(db_session):
    """update_community() raises ForbiddenError if caller is not the owner."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)
    # Add other user as a plain member
    await create_test_member(
        db_session,
        community_id=created.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )

    with pytest.raises(ForbiddenError):
        await svc.update_community(
            created.id,
            _update_request(name="Hijacked Name"),
            current_user_id=TEST_OTHER_USER_ID,
        )


@pytest.mark.integration
async def test_update_community_forbidden_for_non_member(db_session):
    """update_community() raises ForbiddenError if caller is not even a member."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    with pytest.raises(ForbiddenError):
        await svc.update_community(
            created.id,
            _update_request(name="Stolen"),
            current_user_id=TEST_OTHER_USER_ID,
        )


@pytest.mark.integration
async def test_update_community_visibility(db_session):
    """update_community() can change community visibility."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(visibility=CommunityVisibility.PUBLIC),
        creator_id=TEST_USER_ID,
    )

    result = await svc.update_community(
        created.id,
        _update_request(visibility=CommunityVisibility.PRIVATE),
        current_user_id=TEST_USER_ID,
    )

    assert result.visibility == CommunityVisibility.PRIVATE


@pytest.mark.integration
async def test_update_community_requires_approval(db_session):
    """update_community() can change requires_approval."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(requires_approval=False), creator_id=TEST_USER_ID
    )

    result = await svc.update_community(
        created.id,
        _update_request(requires_approval=True),
        current_user_id=TEST_USER_ID,
    )

    assert result.requires_approval is True


@pytest.mark.integration
async def test_update_community_empty_request_returns_unchanged(db_session):
    """update_community() with no fields in request returns the unmodified community."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(name="Steady Name"), creator_id=TEST_USER_ID
    )

    result = await svc.update_community(
        created.id,
        CommunityUpdateRequest(),
        current_user_id=TEST_USER_ID,
    )

    assert result.name == "Steady Name"


# ===========================================================================
# delete_community
# ===========================================================================

@pytest.mark.integration
async def test_delete_community_returns_true(db_session):
    """delete_community() returns True on success."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    result = await svc.delete_community(created.id, current_user_id=TEST_USER_ID)

    assert result is True


@pytest.mark.integration
async def test_delete_community_makes_it_unfindable(db_session):
    """After delete_community(), get_community() raises NotFoundError."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    await svc.delete_community(created.id, current_user_id=TEST_USER_ID)

    with pytest.raises(NotFoundError):
        await svc.get_community(created.id)


@pytest.mark.integration
async def test_delete_community_not_found_raises(db_session):
    """delete_community() raises NotFoundError for an unknown community ID."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.delete_community(uuid.uuid4(), current_user_id=TEST_USER_ID)


@pytest.mark.integration
async def test_delete_community_forbidden_for_non_owner(db_session):
    """delete_community() raises ForbiddenError if caller is not the owner."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)
    await create_test_member(
        db_session,
        community_id=created.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )

    with pytest.raises(ForbiddenError):
        await svc.delete_community(created.id, current_user_id=TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_delete_community_sets_status_deleted(db_session):
    """After delete_community(), the community status is DELETED in the DB."""
    from app.repositories.community_repository import CommunityRepository

    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    await svc.delete_community(created.id, current_user_id=TEST_USER_ID)

    repo = CommunityRepository(db_session)
    deleted = await repo.get_by_id(created.id, include_deleted=True)
    assert deleted is not None
    assert deleted.is_deleted is True
    assert deleted.status == CommunityStatus.DELETED


# ===========================================================================
# archive_community
# ===========================================================================

@pytest.mark.integration
async def test_archive_community_returns_schema(db_session):
    """archive_community() returns a CommunitySchema with status=ARCHIVED."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    result = await svc.archive_community(created.id, current_user_id=TEST_USER_ID)

    assert isinstance(result, CommunitySchema)
    assert result.status == CommunityStatus.ARCHIVED


@pytest.mark.integration
async def test_archive_community_not_found_raises(db_session):
    """archive_community() raises NotFoundError for unknown community."""
    svc = _svc(db_session)

    with pytest.raises(NotFoundError):
        await svc.archive_community(uuid.uuid4(), current_user_id=TEST_USER_ID)


@pytest.mark.integration
async def test_archive_community_forbidden_for_non_owner(db_session):
    """archive_community() raises ForbiddenError if caller is not the owner."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)
    await create_test_member(
        db_session,
        community_id=created.id,
        user_id=TEST_OTHER_USER_ID,
        role=MemberRole.MEMBER,
    )

    with pytest.raises(ForbiddenError):
        await svc.archive_community(created.id, current_user_id=TEST_OTHER_USER_ID)


@pytest.mark.integration
async def test_archive_community_persists_archived_status(db_session):
    """archive_community() persists status=ARCHIVED to the database."""
    from app.repositories.community_repository import CommunityRepository

    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    await svc.archive_community(created.id, current_user_id=TEST_USER_ID)

    repo = CommunityRepository(db_session)
    fetched = await repo.get_by_id(created.id)
    assert fetched.status == CommunityStatus.ARCHIVED


@pytest.mark.integration
async def test_archive_community_is_still_gettable(db_session):
    """Archived communities are still retrievable via get_community()."""
    svc = _svc(db_session)
    created = await svc.create_community(_create_request(), creator_id=TEST_USER_ID)

    await svc.archive_community(created.id, current_user_id=TEST_USER_ID)

    result = await svc.get_community(created.id, current_user_id=TEST_USER_ID)
    assert result.status == CommunityStatus.ARCHIVED


@pytest.mark.integration
async def test_archive_community_excluded_from_listing(db_session):
    """Archived communities are excluded from list_communities() (active only)."""
    svc = _svc(db_session)
    created = await svc.create_community(
        _create_request(name="To Be Archived"), creator_id=TEST_USER_ID
    )

    await svc.archive_community(created.id, current_user_id=TEST_USER_ID)

    result = await svc.list_communities(_query_params(), current_user_id=TEST_USER_ID)
    ids = [c.id for c in result.communities]
    assert created.id not in ids
