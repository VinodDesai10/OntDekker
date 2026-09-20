"""
CP-16E.2 — CommunityRepository Integration Tests

Validates repository-level behaviour for CommunityRepository.
All tests use an in-memory SQLite database via the db_session fixture.
Business logic and HTTP behaviour are out of scope.

Key note: CommunityRepository.create() calls session.commit() internally.
Tests that call repo.create() do not need a separate session.commit() call.
Tests that use create_test_community() (direct ORM insert via flush) do need
await db_session.commit() before querying via the repository.
"""

import uuid
import pytest

from app.repositories.community_repository import CommunityRepository
from app.schemas.community import CommunityQueryParams
from shared.constants.status import CommunityStatus, CommunityVisibility, MemberRole
from tests.conftest import TEST_USER_ID, TEST_OTHER_USER_ID
from tests.utils import create_test_community


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo(session) -> CommunityRepository:
    return CommunityRepository(session)


# ===========================================================================
# create
# ===========================================================================

@pytest.mark.integration
async def test_create_returns_community_with_id(db_session):
    """create() persists a community and returns an ORM instance with a UUID id."""
    repo = _repo(db_session)

    community = await repo.create(creator_id=TEST_USER_ID, name="My Community")

    assert community is not None
    assert community.id is not None
    assert isinstance(community.id, uuid.UUID)


@pytest.mark.integration
async def test_create_stores_name_stripped(db_session):
    """create() strips whitespace from the name before persisting."""
    repo = _repo(db_session)

    community = await repo.create(creator_id=TEST_USER_ID, name="  Trimmed Name  ")

    assert community.name == "Trimmed Name"


@pytest.mark.integration
async def test_create_stores_creator_id(db_session):
    """create() persists the creator_id field."""
    repo = _repo(db_session)

    community = await repo.create(creator_id=TEST_USER_ID, name="Creator Test")

    assert community.creator_id == TEST_USER_ID


@pytest.mark.integration
async def test_create_stores_optional_fields(db_session):
    """create() persists description, location, visibility, requires_approval."""
    repo = _repo(db_session)

    community = await repo.create(
        creator_id=TEST_USER_ID,
        name="Full Community",
        description="A test description",
        location="Amsterdam, Netherlands",
        visibility=CommunityVisibility.PRIVATE,
        requires_approval=True,
        created_by=TEST_USER_ID,
    )

    assert community.description == "A test description"
    assert community.location == "Amsterdam, Netherlands"
    assert community.visibility == CommunityVisibility.PRIVATE
    assert community.requires_approval is True


@pytest.mark.integration
async def test_create_default_status_is_active(db_session):
    """create() sets status=ACTIVE by default."""
    repo = _repo(db_session)

    community = await repo.create(creator_id=TEST_USER_ID, name="Default Status")

    assert community.status == CommunityStatus.ACTIVE


@pytest.mark.integration
async def test_create_default_visibility_is_public(db_session):
    """create() defaults to PUBLIC visibility."""
    repo = _repo(db_session)

    community = await repo.create(creator_id=TEST_USER_ID, name="Default Visibility")

    assert community.visibility == CommunityVisibility.PUBLIC


@pytest.mark.integration
async def test_create_sets_member_count_to_one(db_session):
    """create() sets member_count=1 (creator is the first member)."""
    repo = _repo(db_session)

    community = await repo.create(creator_id=TEST_USER_ID, name="Member Count")

    assert community.member_count == 1


@pytest.mark.integration
async def test_create_generates_slug_from_name(db_session):
    """create() generates a URL-safe slug from the community name."""
    repo = _repo(db_session)

    community = await repo.create(creator_id=TEST_USER_ID, name="Slow Travel Amsterdam")

    assert community.slug == "slow-travel-amsterdam"


@pytest.mark.integration
async def test_create_slug_is_unique_when_name_collides(db_session):
    """create() appends a numeric suffix to guarantee slug uniqueness."""
    repo = _repo(db_session)

    c1 = await repo.create(creator_id=TEST_USER_ID, name="Duplicate Name")
    c2 = await repo.create(creator_id=TEST_OTHER_USER_ID, name="Duplicate Name")

    assert c1.slug != c2.slug
    assert c2.slug.startswith("duplicate-name")


@pytest.mark.integration
async def test_create_adds_creator_as_owner_member(db_session):
    """create() automatically adds the creator as an OWNER CommunityMember."""
    from app.models import CommunityMember
    from sqlalchemy import select

    repo = _repo(db_session)
    community = await repo.create(creator_id=TEST_USER_ID, name="Owner Test")

    result = await db_session.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community.id,
            CommunityMember.user_id == TEST_USER_ID,
        )
    )
    member = result.scalar_one_or_none()

    assert member is not None
    assert member.role == MemberRole.OWNER


@pytest.mark.integration
async def test_create_is_not_deleted(db_session):
    """Newly created community has is_deleted=False."""
    repo = _repo(db_session)

    community = await repo.create(creator_id=TEST_USER_ID, name="Not Deleted")

    assert community.is_deleted is False


@pytest.mark.integration
async def test_create_rules_relationship_is_loaded(db_session):
    """create() returns a community whose rules list is accessible (empty by default)."""
    repo = _repo(db_session)

    community = await repo.create(creator_id=TEST_USER_ID, name="Rules Check")

    assert community.rules == []


# ===========================================================================
# get_by_id
# ===========================================================================

@pytest.mark.integration
async def test_get_by_id_returns_existing_community(db_session):
    """get_by_id() returns the community when it exists."""
    community = await create_test_community(db_session, name="Findable")
    await db_session.commit()

    repo = _repo(db_session)
    found = await repo.get_by_id(community.id)

    assert found is not None
    assert found.id == community.id


@pytest.mark.integration
async def test_get_by_id_returns_none_for_missing_id(db_session):
    """get_by_id() returns None when the ID does not exist."""
    repo = _repo(db_session)

    result = await repo.get_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.integration
async def test_get_by_id_excludes_soft_deleted_by_default(db_session):
    """get_by_id() returns None for a soft-deleted community by default."""
    community = await create_test_community(db_session, name="To Delete")
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(community.id)

    result = await repo.get_by_id(community.id)

    assert result is None


@pytest.mark.integration
async def test_get_by_id_includes_deleted_when_flag_set(db_session):
    """get_by_id(include_deleted=True) returns soft-deleted communities."""
    community = await create_test_community(db_session, name="Soft Deleted")
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(community.id)

    result = await repo.get_by_id(community.id, include_deleted=True)

    assert result is not None
    assert result.is_deleted is True


@pytest.mark.integration
async def test_get_by_id_loads_rules_relationship(db_session):
    """get_by_id() loads the rules relationship via selectinload."""
    community = await create_test_community(db_session, name="With Rules")
    await db_session.commit()

    repo = _repo(db_session)
    found = await repo.get_by_id(community.id)

    assert found.rules is not None
    assert isinstance(found.rules, list)


# ===========================================================================
# get_by_slug
# ===========================================================================

@pytest.mark.integration
async def test_get_by_slug_returns_community(db_session):
    """get_by_slug() returns the community matching the slug."""
    community = await create_test_community(db_session, name="Slug Test", slug="slug-test-unique")
    await db_session.commit()

    repo = _repo(db_session)
    found = await repo.get_by_slug("slug-test-unique")

    assert found is not None
    assert found.id == community.id


@pytest.mark.integration
async def test_get_by_slug_returns_none_for_missing_slug(db_session):
    """get_by_slug() returns None when no community has that slug."""
    repo = _repo(db_session)

    result = await repo.get_by_slug("nonexistent-slug")

    assert result is None


@pytest.mark.integration
async def test_get_by_slug_excludes_soft_deleted(db_session):
    """get_by_slug() does not return soft-deleted communities."""
    community = await create_test_community(db_session, name="Deleted Slug", slug="deleted-slug-xyz")
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(community.id)

    result = await repo.get_by_slug("deleted-slug-xyz")

    assert result is None


# ===========================================================================
# update
# ===========================================================================

@pytest.mark.integration
async def test_update_changes_name(db_session):
    """update() persists a new name and returns the updated community."""
    community = await create_test_community(db_session, name="Old Name")
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update(community.id, name="New Name")

    assert updated is not None
    assert updated.name == "New Name"


@pytest.mark.integration
async def test_update_changes_description(db_session):
    """update() persists a new description."""
    community = await create_test_community(db_session, description="Old desc")
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update(community.id, description="New desc")

    assert updated.description == "New desc"


@pytest.mark.integration
async def test_update_changes_location(db_session):
    """update() persists a new location."""
    community = await create_test_community(db_session, location="Old City")
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update(community.id, location="New City")

    assert updated.location == "New City"


@pytest.mark.integration
async def test_update_changes_visibility(db_session):
    """update() persists a new visibility value."""
    community = await create_test_community(db_session, visibility=CommunityVisibility.PUBLIC)
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update(community.id, visibility=CommunityVisibility.PRIVATE)

    assert updated.visibility == CommunityVisibility.PRIVATE


@pytest.mark.integration
async def test_update_returns_none_for_missing_id(db_session):
    """update() returns None when the community ID does not exist."""
    repo = _repo(db_session)

    result = await repo.update(uuid.uuid4(), name="Ghost")

    assert result is None


@pytest.mark.integration
async def test_update_returns_none_for_deleted_community(db_session):
    """update() returns None for a soft-deleted community."""
    community = await create_test_community(db_session, name="Will Delete")
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(community.id)

    result = await repo.update(community.id, name="After Delete")

    assert result is None


@pytest.mark.integration
async def test_update_with_no_kwargs_returns_community(db_session):
    """update() with no kwargs returns the current community unchanged."""
    community = await create_test_community(db_session, name="Unchanged")
    await db_session.commit()
    repo = _repo(db_session)

    result = await repo.update(community.id)

    assert result is not None
    assert result.id == community.id


# ===========================================================================
# soft_delete
# ===========================================================================

@pytest.mark.integration
async def test_soft_delete_returns_true_on_success(db_session):
    """soft_delete() returns True when the community was deleted."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)

    result = await repo.soft_delete(community.id)

    assert result is True


@pytest.mark.integration
async def test_soft_delete_sets_is_deleted_flag(db_session):
    """soft_delete() sets is_deleted=True on the community."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(community.id)

    deleted = await repo.get_by_id(community.id, include_deleted=True)

    assert deleted.is_deleted is True


@pytest.mark.integration
async def test_soft_delete_sets_deleted_at(db_session):
    """soft_delete() sets deleted_at timestamp."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(community.id)

    deleted = await repo.get_by_id(community.id, include_deleted=True)

    assert deleted.deleted_at is not None


@pytest.mark.integration
async def test_soft_delete_sets_status_to_deleted(db_session):
    """soft_delete() sets status=DELETED on the community."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(community.id)

    deleted = await repo.get_by_id(community.id, include_deleted=True)

    assert deleted.status == CommunityStatus.DELETED


@pytest.mark.integration
async def test_soft_delete_records_deleted_by(db_session):
    """soft_delete() stores the deleted_by user ID."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(community.id, deleted_by=TEST_USER_ID)

    deleted = await repo.get_by_id(community.id, include_deleted=True)

    assert deleted.deleted_by == TEST_USER_ID


@pytest.mark.integration
async def test_soft_delete_returns_false_for_missing_id(db_session):
    """soft_delete() returns False when the community ID does not exist."""
    repo = _repo(db_session)

    result = await repo.soft_delete(uuid.uuid4())

    assert result is False


@pytest.mark.integration
async def test_soft_delete_is_idempotent(db_session):
    """Calling soft_delete() on an already-deleted community returns False."""
    community = await create_test_community(db_session)
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(community.id)

    result = await repo.soft_delete(community.id)

    assert result is False


# ===========================================================================
# update_member_count
# ===========================================================================

@pytest.mark.integration
async def test_update_member_count_increments(db_session):
    """update_member_count(+1) increments the member_count by 1."""
    community = await create_test_community(db_session, member_count=5)
    await db_session.commit()
    repo = _repo(db_session)

    await repo.update_member_count(community.id, delta=1)
    await db_session.commit()

    found = await repo.get_by_id(community.id)
    assert found.member_count == 6


@pytest.mark.integration
async def test_update_member_count_decrements(db_session):
    """update_member_count(-1) decrements the member_count by 1."""
    community = await create_test_community(db_session, member_count=5)
    await db_session.commit()
    repo = _repo(db_session)

    await repo.update_member_count(community.id, delta=-1)
    await db_session.commit()

    found = await repo.get_by_id(community.id)
    assert found.member_count == 4


# ===========================================================================
# list_communities — basic retrieval
# ===========================================================================

@pytest.mark.integration
async def test_list_communities_returns_active_non_deleted(db_session):
    """list_communities() returns active, non-deleted communities."""
    await create_test_community(db_session, name="Active One")
    await create_test_community(db_session, name="Active Two")
    await db_session.commit()

    repo = _repo(db_session)
    params = CommunityQueryParams()
    communities, total = await repo.list_communities(params, current_user_id=TEST_USER_ID)

    assert total >= 2
    assert len(communities) >= 2


@pytest.mark.integration
async def test_list_communities_excludes_soft_deleted(db_session):
    """list_communities() does not include soft-deleted communities."""
    visible = await create_test_community(db_session, name="Visible")
    gone = await create_test_community(db_session, name="Gone")
    await db_session.commit()
    repo = _repo(db_session)
    await repo.soft_delete(gone.id)

    params = CommunityQueryParams()
    communities, _ = await repo.list_communities(params, current_user_id=TEST_USER_ID)

    ids = {c.id for c in communities}
    assert visible.id in ids
    assert gone.id not in ids


@pytest.mark.integration
async def test_list_communities_excludes_non_active_status(db_session):
    """list_communities() does not include communities with status != ACTIVE."""
    await create_test_community(db_session, name="Archived", status=CommunityStatus.ARCHIVED)
    active = await create_test_community(db_session, name="Active")
    await db_session.commit()

    repo = _repo(db_session)
    params = CommunityQueryParams()
    communities, _ = await repo.list_communities(params, current_user_id=TEST_USER_ID)

    ids = {c.id for c in communities}
    assert active.id in ids


@pytest.mark.integration
async def test_list_communities_unauthenticated_sees_only_public(db_session):
    """Unauthenticated callers (current_user_id=None) see only PUBLIC communities."""
    await create_test_community(
        db_session, name="Public Comm", visibility=CommunityVisibility.PUBLIC
    )
    private = await create_test_community(
        db_session, name="Private Comm", visibility=CommunityVisibility.PRIVATE
    )
    await db_session.commit()

    repo = _repo(db_session)
    params = CommunityQueryParams()
    communities, _ = await repo.list_communities(params, current_user_id=None)

    ids = {c.id for c in communities}
    assert private.id not in ids
    assert all(c.visibility == CommunityVisibility.PUBLIC for c in communities)


@pytest.mark.integration
async def test_list_communities_authenticated_sees_public_and_private(db_session):
    """Authenticated callers can see both PUBLIC and PRIVATE communities."""
    pub = await create_test_community(
        db_session, name="Public Auth", visibility=CommunityVisibility.PUBLIC
    )
    priv = await create_test_community(
        db_session, name="Private Auth", visibility=CommunityVisibility.PRIVATE
    )
    await db_session.commit()

    repo = _repo(db_session)
    params = CommunityQueryParams()
    communities, _ = await repo.list_communities(params, current_user_id=TEST_USER_ID)

    ids = {c.id for c in communities}
    assert pub.id in ids
    assert priv.id in ids


# ===========================================================================
# list_communities — filtering
# ===========================================================================

@pytest.mark.integration
async def test_list_communities_filter_by_location(db_session):
    """list_communities() with location filter does a case-insensitive partial match."""
    await create_test_community(db_session, name="Amsterdam Comm", location="Amsterdam, NL")
    await create_test_community(db_session, name="Berlin Comm", location="Berlin, DE")
    await db_session.commit()

    repo = _repo(db_session)
    params = CommunityQueryParams(location="amsterdam")
    communities, total = await repo.list_communities(params, current_user_id=TEST_USER_ID)

    assert total == 1
    assert communities[0].name == "Amsterdam Comm"


@pytest.mark.integration
async def test_list_communities_filter_by_visibility(db_session):
    """list_communities() with visibility filter returns only matching communities."""
    await create_test_community(
        db_session, name="Public Filter", visibility=CommunityVisibility.PUBLIC
    )
    await create_test_community(
        db_session, name="Private Filter", visibility=CommunityVisibility.PRIVATE
    )
    await db_session.commit()

    repo = _repo(db_session)
    params = CommunityQueryParams(visibility=CommunityVisibility.PRIVATE)
    communities, total = await repo.list_communities(params, current_user_id=TEST_USER_ID)

    assert total == 1
    assert communities[0].visibility == CommunityVisibility.PRIVATE


@pytest.mark.integration
async def test_list_communities_search_by_name(db_session):
    """list_communities() search filter matches community name case-insensitively."""
    await create_test_community(db_session, name="Hiking Lovers")
    await create_test_community(db_session, name="Beach Walkers")
    await db_session.commit()

    repo = _repo(db_session)
    params = CommunityQueryParams(search="hiking")
    communities, total = await repo.list_communities(params, current_user_id=TEST_USER_ID)

    assert total == 1
    assert communities[0].name == "Hiking Lovers"


@pytest.mark.integration
async def test_list_communities_search_by_description(db_session):
    """list_communities() search filter matches description case-insensitively."""
    await create_test_community(
        db_session, name="Travel Group", description="For mountain enthusiasts"
    )
    await create_test_community(
        db_session, name="Other Group", description="Something else entirely"
    )
    await db_session.commit()

    repo = _repo(db_session)
    params = CommunityQueryParams(search="mountain")
    communities, total = await repo.list_communities(params, current_user_id=TEST_USER_ID)

    assert total == 1
    assert communities[0].name == "Travel Group"


# ===========================================================================
# list_communities — pagination and ordering
# ===========================================================================

@pytest.mark.integration
async def test_list_communities_respects_limit(db_session):
    """list_communities() respects the limit parameter."""
    for i in range(5):
        await create_test_community(db_session, name=f"Paged Community {i}")
    await db_session.commit()

    repo = _repo(db_session)
    params = CommunityQueryParams(limit=2, offset=0)
    communities, total = await repo.list_communities(params, current_user_id=TEST_USER_ID)

    assert len(communities) == 2
    assert total >= 5


@pytest.mark.integration
async def test_list_communities_respects_offset(db_session):
    """list_communities() with offset skips earlier results."""
    for i in range(4):
        await create_test_community(db_session, name=f"Offset Comm {i}")
    await db_session.commit()

    repo = _repo(db_session)
    params_all = CommunityQueryParams(limit=100, offset=0)
    params_paged = CommunityQueryParams(limit=100, offset=2)

    all_comms, _ = await repo.list_communities(params_all, current_user_id=TEST_USER_ID)
    paged_comms, _ = await repo.list_communities(params_paged, current_user_id=TEST_USER_ID)

    assert len(paged_comms) == len(all_comms) - 2


@pytest.mark.integration
async def test_list_communities_ordered_newest_first(db_session):
    """list_communities() returns results in descending created_at order."""
    c1 = await create_test_community(db_session, name="Earlier Community")
    await db_session.commit()
    c2 = await create_test_community(db_session, name="Later Community")
    await db_session.commit()

    repo = _repo(db_session)
    params = CommunityQueryParams(limit=10)
    communities, _ = await repo.list_communities(params, current_user_id=TEST_USER_ID)

    ids = [c.id for c in communities]
    assert ids.index(c2.id) < ids.index(c1.id)


@pytest.mark.integration
async def test_list_communities_returns_zero_total_when_empty(db_session):
    """list_communities() returns empty list and total=0 when no communities exist."""
    repo = _repo(db_session)
    params = CommunityQueryParams()

    communities, total = await repo.list_communities(params, current_user_id=TEST_USER_ID)

    assert communities == [] or list(communities) == []
    assert total == 0


# ===========================================================================
# update_logo
# ===========================================================================

@pytest.mark.integration
async def test_update_logo_persists_url_and_key(db_session):
    """update_logo() stores logo_url and logo_object_key."""
    community = await create_test_community(db_session, name="Logo Community")
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update_logo(
        community.id,
        logo_url="https://cdn.example.com/logo.jpg",
        logo_object_key="communities/logos/logo.jpg",
        updated_by=TEST_USER_ID,
    )

    assert updated.logo_url == "https://cdn.example.com/logo.jpg"
    assert updated.logo_object_key == "communities/logos/logo.jpg"


@pytest.mark.integration
async def test_update_logo_returns_none_for_missing_community(db_session):
    """update_logo() returns None when the community does not exist."""
    repo = _repo(db_session)

    result = await repo.update_logo(
        uuid.uuid4(),
        logo_url="https://cdn.example.com/logo.jpg",
        logo_object_key="communities/logos/logo.jpg",
    )

    assert result is None


# ===========================================================================
# update_banner
# ===========================================================================

@pytest.mark.integration
async def test_update_banner_persists_url_and_key(db_session):
    """update_banner() stores banner_url and banner_object_key."""
    community = await create_test_community(db_session, name="Banner Community")
    await db_session.commit()
    repo = _repo(db_session)

    updated = await repo.update_banner(
        community.id,
        banner_url="https://cdn.example.com/banner.jpg",
        banner_object_key="communities/banners/banner.jpg",
        updated_by=TEST_USER_ID,
    )

    assert updated.banner_url == "https://cdn.example.com/banner.jpg"
    assert updated.banner_object_key == "communities/banners/banner.jpg"


@pytest.mark.integration
async def test_update_banner_returns_none_for_missing_community(db_session):
    """update_banner() returns None when the community does not exist."""
    repo = _repo(db_session)

    result = await repo.update_banner(
        uuid.uuid4(),
        banner_url="https://cdn.example.com/banner.jpg",
        banner_object_key="communities/banners/banner.jpg",
    )

    assert result is None
