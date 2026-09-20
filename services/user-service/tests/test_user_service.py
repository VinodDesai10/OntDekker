"""
User Service — Checkpoint 5 Test Suite

[UNIT]        No database or MinIO. Pure logic tests.
[INTEGRATION] Requires live user_db on localhost:5432.
[MINIO]       Requires MinIO running on localhost:9000 with profiles bucket.

Run:
  PYTHONPATH=../.. \
  DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/user_db \
  MINIO_ENDPOINT=localhost:9000 \
  MINIO_ACCESS_KEY=minioadmin \
  MINIO_SECRET_KEY=minioadmin123 \
  MINIO_BUCKET_PROFILES=profiles \
  pytest tests/test_user_service.py -v --asyncio-mode=auto
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB = "postgresql+asyncpg://postgres:postgres@localhost:5432/user_db"

# ---------------------------------------------------------------------------
# JWT helpers for tests (avoids depending on a running Auth Service)
# ---------------------------------------------------------------------------

def _make_jwt_payload(user_id: uuid.UUID | None = None, roles: list = None) -> dict:
    uid = user_id or uuid.uuid4()
    return {
        "sub": str(uid),
        "email": f"{str(uid)[:8]}@test.example.com",
        "roles": roles or ["USER"],
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }


# ---------------------------------------------------------------------------
# Async event loop
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# DB session fixture — savepoint rollback per test
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DB, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession,
        expire_on_commit=False, autocommit=False, autoflush=False,
    )
    async with factory() as session:
        await session.begin_nested()
        yield session
        await session.rollback()
    await engine.dispose()


# ---------------------------------------------------------------------------
# MinIO client fixture — initialised with local credentials
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def minio_ready():
    """Ensure MinIO client is initialised for tests that use it."""
    import os
    os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
    os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
    os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin123")
    os.environ.setdefault("MINIO_BUCKET_PROFILES", "profiles")
    from app.infrastructure.minio_client import init_minio
    await init_minio()
    yield


# ===========================================================================
# [UNIT] Schema validation tests
# ===========================================================================

class TestSchemaValidation:

    def test_valid_username_accepted(self):
        from app.schemas.user import UpdateProfileRequest
        r = UpdateProfileRequest(username="valid_user123")
        assert r.username == "valid_user123"

    def test_username_too_short_rejected(self):
        from pydantic import ValidationError
        from app.schemas.user import UpdateProfileRequest
        with pytest.raises(ValidationError):
            UpdateProfileRequest(username="ab")

    def test_username_with_spaces_rejected(self):
        from pydantic import ValidationError
        from app.schemas.user import UpdateProfileRequest
        with pytest.raises(ValidationError):
            UpdateProfileRequest(username="bad name")

    def test_username_special_chars_rejected(self):
        from pydantic import ValidationError
        from app.schemas.user import UpdateProfileRequest
        with pytest.raises(ValidationError):
            UpdateProfileRequest(username="bad-name!")

    def test_valid_entity_type_accepted(self):
        from app.schemas.user import SaveItemRequest
        r = SaveItemRequest(entity_type="story", entity_id=uuid.uuid4())
        assert r.entity_type == "STORY"

    def test_invalid_entity_type_rejected(self):
        from pydantic import ValidationError
        from app.schemas.user import SaveItemRequest
        with pytest.raises(ValidationError):
            SaveItemRequest(entity_type="INVALID", entity_id=uuid.uuid4())

    def test_update_interests_deduplication(self):
        from pydantic import ValidationError
        from app.schemas.user import UpdateInterestsRequest
        with pytest.raises(ValidationError):
            UpdateInterestsRequest(interests=["Trekking", "trekking"])

    def test_private_profile_has_no_email_field(self):
        from app.schemas.user import PrivateProfileResponse
        fields = PrivateProfileResponse.model_fields
        assert "email" not in fields
        assert "password_hash" not in fields

    def test_public_profile_has_no_private_fields(self):
        from app.schemas.user import PublicProfileResponse
        fields = PublicProfileResponse.model_fields
        assert "interests" not in fields
        assert "preferences" not in fields
        assert "saved_items" not in fields
        assert "auth_user_id" not in fields


# ===========================================================================
# [UNIT] Service validation helpers
# ===========================================================================

class TestServiceUploadValidation:

    def test_invalid_mime_type_raises(self):
        from shared.exceptions import ValidationException
        from app.services.user import UserService
        with pytest.raises(ValidationException) as exc:
            UserService._validate_upload(b"data", "application/pdf")
        assert "INVALID_FILE_TYPE" in exc.value.error_code

    def test_empty_file_raises(self):
        from shared.exceptions import ValidationException
        from app.services.user import UserService
        with pytest.raises(ValidationException) as exc:
            UserService._validate_upload(b"", "image/jpeg")
        assert "EMPTY_FILE" in exc.value.error_code

    def test_oversized_file_raises(self):
        from shared.exceptions import ValidationException
        from app.services.user import UserService
        big = b"x" * (6 * 1024 * 1024)  # 6 MB > 5 MB limit
        with pytest.raises(ValidationException) as exc:
            UserService._validate_upload(big, "image/jpeg")
        assert "FILE_TOO_LARGE" in exc.value.error_code

    def test_valid_jpeg_passes(self):
        from app.services.user import UserService
        UserService._validate_upload(b"\xff\xd8\xff" + b"x" * 100, "image/jpeg")


# ===========================================================================
# [UNIT] Auto-username generation
# ===========================================================================

class TestAutoUsernameGeneration:

    def test_auto_username_format(self):
        from app.services.user import _auto_username
        uid = uuid.uuid4()
        username = _auto_username(uid)
        assert username.startswith("user_")
        assert len(username) == 13  # "user_" + 8 chars

    def test_auto_username_is_valid_regex(self):
        import re
        from app.schemas.user import USERNAME_REGEX
        from app.services.user import _auto_username
        for _ in range(10):
            un = _auto_username(uuid.uuid4())
            assert USERNAME_REGEX.match(un), f"Invalid username: {un}"

    def test_two_different_users_get_different_usernames(self):
        from app.services.user import _auto_username
        assert _auto_username(uuid.uuid4()) != _auto_username(uuid.uuid4())


# ===========================================================================
# [INTEGRATION] Lazy profile creation
# ===========================================================================

class TestLazyProfileCreation:

    @pytest.mark.asyncio
    async def test_first_call_creates_profile(self, db_session):
        from app.services.user import UserService
        auth_id = uuid.uuid4()
        svc = UserService(db_session)
        result = await svc.get_my_profile(_make_jwt_payload(auth_id))
        assert result.auth_user_id == auth_id
        assert result.username.startswith("user_")

    @pytest.mark.asyncio
    async def test_repeated_calls_are_idempotent(self, db_session):
        from app.services.user import UserService
        auth_id = uuid.uuid4()
        payload = _make_jwt_payload(auth_id)
        svc = UserService(db_session)
        r1 = await svc.get_my_profile(payload)
        r2 = await svc.get_my_profile(payload)
        assert r1.id == r2.id
        assert r1.username == r2.username

    @pytest.mark.asyncio
    async def test_lazy_creation_also_creates_reputation(self, db_session):
        from app.services.user import UserService
        from app.repositories.user import ReputationRepository
        auth_id = uuid.uuid4()
        svc = UserService(db_session)
        profile = await svc.get_my_profile(_make_jwt_payload(auth_id))
        rep = await ReputationRepository(db_session).get_by_user(profile.id)
        assert rep is not None
        assert rep.explorer_score == 0

    @pytest.mark.asyncio
    async def test_new_profile_has_default_values(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        r = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
        assert r.bio is None
        assert r.avatar_url is None
        assert r.follower_count == 0
        assert r.following_count == 0
        assert r.interests == []
        assert r.badges == []


# ===========================================================================
# [INTEGRATION] Profile update
# ===========================================================================

class TestProfileUpdate:

    @pytest.mark.asyncio
    async def test_update_display_name(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        await svc.get_my_profile(payload)
        updated = await svc.update_my_profile(
            payload, username=None, display_name="Alice Explorer",
            bio=None, city=None, country=None,
        )
        assert updated.display_name == "Alice Explorer"

    @pytest.mark.asyncio
    async def test_update_bio_city_country(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        await svc.get_my_profile(payload)
        updated = await svc.update_my_profile(
            payload, username=None, display_name=None,
            bio="Slow traveler", city="Amsterdam", country="Netherlands",
        )
        assert updated.bio == "Slow traveler"
        assert updated.city == "Amsterdam"
        assert updated.country == "Netherlands"

    @pytest.mark.asyncio
    async def test_update_username_to_unique(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        await svc.get_my_profile(payload)
        new_username = f"traveler_{uuid.uuid4().hex[:6]}"
        updated = await svc.update_my_profile(
            payload, username=new_username, display_name=None,
            bio=None, city=None, country=None,
        )
        assert updated.username == new_username

    @pytest.mark.asyncio
    async def test_duplicate_username_raises_conflict(self, db_session):
        from app.services.user import UserService
        from shared.exceptions import ConflictException
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        p2 = _make_jwt_payload(uuid.uuid4())
        r1 = await svc.get_my_profile(p1)
        await svc.get_my_profile(p2)
        with pytest.raises(ConflictException) as exc:
            await svc.update_my_profile(
                p2, username=r1.username, display_name=None,
                bio=None, city=None, country=None,
            )
        assert "USERNAME_TAKEN" in exc.value.error_code

    @pytest.mark.asyncio
    async def test_user_cannot_see_other_users_private_data(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        r1 = await svc.get_my_profile(p1)
        # Public profile should not expose auth_user_id or private fields
        pub = await svc.get_public_profile(r1.username)
        assert not hasattr(pub, "auth_user_id") or pub.__class__.__name__ == "PublicProfileResponse"
        from app.schemas.user import PublicProfileResponse
        assert isinstance(pub, PublicProfileResponse)


# ===========================================================================
# [INTEGRATION] Interests
# ===========================================================================

class TestInterests:

    @pytest.mark.asyncio
    async def test_set_interests(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        r = await svc.update_interests(payload, ["Trekking", "Wildlife", "Photography"])
        names = [i.interest for i in r.interests]
        assert set(names) == {"Trekking", "Wildlife", "Photography"}

    @pytest.mark.asyncio
    async def test_replace_interests(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        await svc.update_interests(payload, ["Trekking", "Camping"])
        r = await svc.update_interests(payload, ["Photography"])
        assert [i.interest for i in r.interests] == ["Photography"]

    @pytest.mark.asyncio
    async def test_empty_interests_clears_all(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        await svc.update_interests(payload, ["Trekking"])
        r = await svc.update_interests(payload, [])
        assert r.interests == []

    @pytest.mark.asyncio
    async def test_interests_isolated_between_users(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        p2 = _make_jwt_payload(uuid.uuid4())
        await svc.update_interests(p1, ["Camping"])
        r2 = await svc.get_my_profile(p2)
        assert r2.interests == []


# ===========================================================================
# [INTEGRATION] Preferences
# ===========================================================================

class TestPreferences:

    @pytest.mark.asyncio
    async def test_upsert_creates_preferences(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        r = await svc.update_preferences(
            payload,
            travel_style="Backpacking",
            budget="Low",
            adventure_level="High",
        )
        assert r.preferences is not None
        assert r.preferences.travel_style == "Backpacking"

    @pytest.mark.asyncio
    async def test_upsert_updates_preferences(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        await svc.update_preferences(payload, travel_style="Backpacking")
        r = await svc.update_preferences(payload, travel_style="Luxury")
        assert r.preferences.travel_style == "Luxury"

    @pytest.mark.asyncio
    async def test_languages_stored_as_list(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        r = await svc.update_preferences(
            payload, languages=["English", "Dutch", "Spanish"]
        )
        assert set(r.preferences.languages) == {"English", "Dutch", "Spanish"}

    @pytest.mark.asyncio
    async def test_preferred_destinations_stored(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        r = await svc.update_preferences(
            payload, preferred_destinations=["Himalayas", "Patagonia"]
        )
        assert "Himalayas" in r.preferences.preferred_destinations


# ===========================================================================
# [INTEGRATION] Follow / Unfollow
# ===========================================================================

class TestFollowUnfollow:

    @pytest.mark.asyncio
    async def test_follow_another_user(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        p2 = _make_jwt_payload(uuid.uuid4())
        r2 = await svc.get_my_profile(p2)
        await svc.get_my_profile(p1)
        result = await svc.follow_user(p1, r2.id)
        assert "Followed" in result.message

    @pytest.mark.asyncio
    async def test_follow_is_idempotent(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        p2 = _make_jwt_payload(uuid.uuid4())
        r2 = await svc.get_my_profile(p2)
        await svc.get_my_profile(p1)
        await svc.follow_user(p1, r2.id)
        # Second follow must not raise
        result = await svc.follow_user(p1, r2.id)
        assert "Followed" in result.message
        # Still only one row
        from app.repositories.user import FollowerRepository
        count = await FollowerRepository(db_session).follower_count(r2.id)
        assert count == 1

    @pytest.mark.asyncio
    async def test_self_follow_is_forbidden(self, db_session):
        from app.services.user import UserService
        from shared.exceptions import ForbiddenException
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        r1 = await svc.get_my_profile(p1)
        with pytest.raises(ForbiddenException) as exc:
            await svc.follow_user(p1, r1.id)
        assert "SELF_FOLLOW" in exc.value.error_code

    @pytest.mark.asyncio
    async def test_unfollow_removes_relationship(self, db_session):
        from app.services.user import UserService
        from app.repositories.user import FollowerRepository
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        p2 = _make_jwt_payload(uuid.uuid4())
        r2 = await svc.get_my_profile(p2)
        await svc.get_my_profile(p1)
        await svc.follow_user(p1, r2.id)
        await svc.unfollow_user(p1, r2.id)
        count = await FollowerRepository(db_session).follower_count(r2.id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_unfollow_nonexistent_is_idempotent(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        await svc.get_my_profile(p1)
        # Unfollowing someone never followed should not raise
        result = await svc.unfollow_user(p1, uuid.uuid4())
        assert result is not None

    @pytest.mark.asyncio
    async def test_follow_nonexistent_user_raises_not_found(self, db_session):
        from app.services.user import UserService
        from shared.exceptions import NotFoundException
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        await svc.get_my_profile(p1)
        with pytest.raises(NotFoundException):
            await svc.follow_user(p1, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_follower_count_reflects_follows(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        p2 = _make_jwt_payload(uuid.uuid4())
        p3 = _make_jwt_payload(uuid.uuid4())
        r1 = await svc.get_my_profile(p1)
        await svc.get_my_profile(p2)
        await svc.get_my_profile(p3)
        await svc.follow_user(p2, r1.id)
        await svc.follow_user(p3, r1.id)
        profile = await svc.get_my_profile(p1)
        assert profile.follower_count == 2

    @pytest.mark.asyncio
    async def test_following_count_reflects_follows(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        p2 = _make_jwt_payload(uuid.uuid4())
        p3 = _make_jwt_payload(uuid.uuid4())
        await svc.get_my_profile(p1)
        r2 = await svc.get_my_profile(p2)
        r3 = await svc.get_my_profile(p3)
        await svc.follow_user(p1, r2.id)
        await svc.follow_user(p1, r3.id)
        profile = await svc.get_my_profile(p1)
        assert profile.following_count == 2


# ===========================================================================
# [INTEGRATION] Badges (read-only in Phase 1)
# ===========================================================================

class TestBadges:

    @pytest.mark.asyncio
    async def test_new_user_has_no_badges(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        r = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
        assert r.badges == []

    @pytest.mark.asyncio
    async def test_get_badges_for_nonexistent_user_raises(self, db_session):
        from app.services.user import UserService
        from shared.exceptions import NotFoundException
        svc = UserService(db_session)
        with pytest.raises(NotFoundException):
            await svc.get_badges(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_badges_returns_list_type(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        r = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
        badges = await svc.get_badges(r.id)
        assert isinstance(badges, list)


# ===========================================================================
# [INTEGRATION] Reputation (read-only in Phase 1)
# ===========================================================================

class TestReputation:

    @pytest.mark.asyncio
    async def test_new_user_has_zero_reputation(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        r = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
        rep = await svc.get_reputation(r.id)
        assert rep.explorer_score == 0
        assert rep.community_score == 0
        assert rep.review_score == 0
        assert rep.expeditions_joined == 0
        assert rep.expeditions_organized == 0
        assert rep.guide_interactions == 0
        assert rep.reviews_received == 0

    @pytest.mark.asyncio
    async def test_reputation_for_nonexistent_user_raises(self, db_session):
        from app.services.user import UserService
        from shared.exceptions import NotFoundException
        svc = UserService(db_session)
        with pytest.raises(NotFoundException):
            await svc.get_reputation(uuid.uuid4())


# ===========================================================================
# [INTEGRATION] Saved items
# ===========================================================================

class TestSavedItems:

    @pytest.mark.asyncio
    async def test_save_story(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        entity_id = uuid.uuid4()
        result = await svc.save_item(payload, "STORY", entity_id)
        assert result.entity_type == "STORY"
        assert result.entity_id == entity_id

    @pytest.mark.asyncio
    async def test_save_all_valid_types(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        for etype in ["STORY", "COMMUNITY", "EXPEDITION", "GUIDE"]:
            r = await svc.save_item(payload, etype, uuid.uuid4())
            assert r.entity_type == etype

    @pytest.mark.asyncio
    async def test_duplicate_save_is_idempotent(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        eid = uuid.uuid4()
        r1 = await svc.save_item(payload, "STORY", eid)
        r2 = await svc.save_item(payload, "STORY", eid)
        assert r1.id == r2.id  # Same record returned

    @pytest.mark.asyncio
    async def test_unsave_item(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        eid = uuid.uuid4()
        await svc.save_item(payload, "STORY", eid)
        result = await svc.unsave_item(payload, "STORY", eid)
        assert "removed" in result.message.lower()
        items = await svc.list_saved(payload)
        assert not any(str(i.entity_id) == str(eid) for i in items)

    @pytest.mark.asyncio
    async def test_list_saved_filtered_by_type(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        await svc.save_item(payload, "STORY", uuid.uuid4())
        await svc.save_item(payload, "COMMUNITY", uuid.uuid4())
        stories = await svc.list_saved(payload, entity_type="STORY")
        assert all(i.entity_type == "STORY" for i in stories)
        assert len(stories) == 1

    @pytest.mark.asyncio
    async def test_saved_items_isolated_between_users(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        p2 = _make_jwt_payload(uuid.uuid4())
        await svc.save_item(p1, "STORY", uuid.uuid4())
        items_p2 = await svc.list_saved(p2)
        assert items_p2 == []

    @pytest.mark.asyncio
    async def test_unsave_nonexistent_is_idempotent(self, db_session):
        from app.services.user import UserService
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        await svc.get_my_profile(payload)
        result = await svc.unsave_item(payload, "STORY", uuid.uuid4())
        assert result is not None


# ===========================================================================
# [MINIO] Avatar and cover image upload
# These tests require MinIO running at localhost:9000 with bucket: profiles
# All MinIO objects created here are deleted in cleanup.
# ===========================================================================

class TestMinIOUpload:
    """[MINIO] Avatar and cover upload via UserService. Requires live MinIO."""

    # Minimal valid 1x1 JPEG bytes (smallest legal JPEG)
    _TINY_JPEG = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xf5\x0a\xff\xd9"
    )

    @pytest.mark.asyncio
    async def test_avatar_upload_returns_object_name_and_url(
        self, db_session, minio_ready
    ):
        from app.services.user import UserService
        from app.infrastructure.minio_client import delete_object
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        result = await svc.upload_avatar(
            jwt_payload=payload,
            file_data=self._TINY_JPEG,
            content_type="image/jpeg",
        )
        assert result.object_name.startswith("avatars/")
        assert result.object_name.endswith(".jpg")
        assert result.presigned_url.startswith("http")
        # Cleanup
        await delete_object(result.object_name)

    @pytest.mark.asyncio
    async def test_cover_upload_returns_object_name_and_url(
        self, db_session, minio_ready
    ):
        from app.services.user import UserService
        from app.infrastructure.minio_client import delete_object
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        result = await svc.upload_cover(
            jwt_payload=payload,
            file_data=self._TINY_JPEG,
            content_type="image/jpeg",
        )
        assert result.object_name.startswith("covers/")
        assert result.object_name.endswith(".jpg")
        assert result.presigned_url.startswith("http")
        await delete_object(result.object_name)

    @pytest.mark.asyncio
    async def test_avatar_upload_updates_db_avatar_url(
        self, db_session, minio_ready
    ):
        from app.services.user import UserService
        from app.repositories.user import ProfileRepository
        from app.infrastructure.minio_client import delete_object
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        result = await svc.upload_avatar(
            jwt_payload=payload,
            file_data=self._TINY_JPEG,
            content_type="image/jpeg",
        )
        profile = await svc.get_my_profile(payload)
        assert profile.avatar_url == result.object_name
        await delete_object(result.object_name)

    @pytest.mark.asyncio
    async def test_cover_upload_updates_db_cover_url(
        self, db_session, minio_ready
    ):
        from app.services.user import UserService
        from app.infrastructure.minio_client import delete_object
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        result = await svc.upload_cover(
            jwt_payload=payload,
            file_data=self._TINY_JPEG,
            content_type="image/jpeg",
        )
        profile = await svc.get_my_profile(payload)
        assert profile.cover_url == result.object_name
        await delete_object(result.object_name)

    @pytest.mark.asyncio
    async def test_presigned_url_is_time_limited_http_url(
        self, db_session, minio_ready
    ):
        from app.services.user import UserService
        from app.infrastructure.minio_client import delete_object
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        result = await svc.upload_avatar(
            jwt_payload=payload,
            file_data=self._TINY_JPEG,
            content_type="image/jpeg",
        )
        # Presigned URL must contain expiry signature params
        url = result.presigned_url
        assert "X-Amz-Expires" in url or "x-amz-expires" in url.lower() or "Expires" in url
        await delete_object(result.object_name)

    @pytest.mark.asyncio
    async def test_avatar_replacement_uses_same_object_key(
        self, db_session, minio_ready
    ):
        """Uploading a second avatar replaces the first (deterministic key)."""
        from app.services.user import UserService
        from app.infrastructure.minio_client import delete_object
        payload = _make_jwt_payload(uuid.uuid4())
        svc = UserService(db_session)
        r1 = await svc.upload_avatar(
            jwt_payload=payload, file_data=self._TINY_JPEG, content_type="image/jpeg"
        )
        r2 = await svc.upload_avatar(
            jwt_payload=payload, file_data=self._TINY_JPEG, content_type="image/jpeg"
        )
        # Same profile → same deterministic key (user_id-based naming)
        assert r1.object_name == r2.object_name
        await delete_object(r1.object_name)

    def test_invalid_mime_type_rejected_before_upload(self):
        from shared.exceptions import ValidationException
        from app.services.user import UserService
        with pytest.raises(ValidationException) as exc:
            UserService._validate_upload(b"data", "image/gif")
        assert "INVALID_FILE_TYPE" in exc.value.error_code

    def test_pdf_mime_rejected(self):
        from shared.exceptions import ValidationException
        from app.services.user import UserService
        with pytest.raises(ValidationException):
            UserService._validate_upload(b"%PDF-1.4", "application/pdf")

    def test_oversized_file_rejected_before_upload(self):
        from shared.exceptions import ValidationException
        from app.services.user import UserService
        oversized = b"x" * (6 * 1024 * 1024)
        with pytest.raises(ValidationException) as exc:
            UserService._validate_upload(oversized, "image/jpeg")
        assert "FILE_TOO_LARGE" in exc.value.error_code

    def test_empty_file_rejected(self):
        from shared.exceptions import ValidationException
        from app.services.user import UserService
        with pytest.raises(ValidationException) as exc:
            UserService._validate_upload(b"", "image/jpeg")
        assert "EMPTY_FILE" in exc.value.error_code

    def test_png_mime_accepted(self):
        from app.services.user import UserService
        # PNG magic bytes header
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        UserService._validate_upload(png_header, "image/png")

    def test_webp_mime_accepted(self):
        from app.services.user import UserService
        webp_data = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 20
        UserService._validate_upload(webp_data, "image/webp")


# ===========================================================================
# [INTEGRATION] Public profile
# ===========================================================================

class TestPublicProfile:

    @pytest.mark.asyncio
    async def test_get_public_profile_by_username(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        payload = _make_jwt_payload(uuid.uuid4())
        private = await svc.get_my_profile(payload)
        pub = await svc.get_public_profile(private.username)
        assert pub.username == private.username
        assert pub.display_name == private.display_name

    @pytest.mark.asyncio
    async def test_unknown_username_raises_not_found(self, db_session):
        from app.services.user import UserService
        from shared.exceptions import NotFoundException
        svc = UserService(db_session)
        with pytest.raises(NotFoundException) as exc:
            await svc.get_public_profile("definitely_does_not_exist_xyz999")
        assert "USER_NOT_FOUND" in exc.value.error_code

    @pytest.mark.asyncio
    async def test_public_profile_has_no_auth_user_id(self, db_session):
        from app.services.user import UserService
        from app.schemas.user import PublicProfileResponse
        svc = UserService(db_session)
        r = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
        pub = await svc.get_public_profile(r.username)
        assert isinstance(pub, PublicProfileResponse)
        assert not hasattr(pub, "auth_user_id")

    @pytest.mark.asyncio
    async def test_public_profile_has_no_interests(self, db_session):
        """Interests are private — not exposed in public profile."""
        from app.services.user import UserService
        from app.schemas.user import PublicProfileResponse
        svc = UserService(db_session)
        payload = _make_jwt_payload(uuid.uuid4())
        await svc.update_interests(payload, ["Trekking"])
        r = await svc.get_my_profile(payload)
        pub = await svc.get_public_profile(r.username)
        assert not hasattr(pub, "interests")

    @pytest.mark.asyncio
    async def test_public_profile_has_no_preferences(self, db_session):
        """Preferences are private — not exposed in public profile."""
        from app.services.user import UserService
        from app.schemas.user import PublicProfileResponse
        svc = UserService(db_session)
        payload = _make_jwt_payload(uuid.uuid4())
        await svc.update_preferences(payload, travel_style="Backpacking")
        r = await svc.get_my_profile(payload)
        pub = await svc.get_public_profile(r.username)
        assert not hasattr(pub, "preferences")

    @pytest.mark.asyncio
    async def test_public_profile_has_no_saved_items(self, db_session):
        from app.services.user import UserService
        from app.schemas.user import PublicProfileResponse
        svc = UserService(db_session)
        payload = _make_jwt_payload(uuid.uuid4())
        await svc.save_item(payload, "STORY", uuid.uuid4())
        r = await svc.get_my_profile(payload)
        pub = await svc.get_public_profile(r.username)
        assert not hasattr(pub, "saved_items")

    @pytest.mark.asyncio
    async def test_public_profile_exposes_follower_counts(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        p2 = _make_jwt_payload(uuid.uuid4())
        r1 = await svc.get_my_profile(p1)
        await svc.get_my_profile(p2)
        await svc.follow_user(p2, r1.id)
        pub = await svc.get_public_profile(r1.username)
        assert pub.follower_count == 1

    @pytest.mark.asyncio
    async def test_public_profile_exposes_badges_and_reputation(self, db_session):
        from app.services.user import UserService
        from app.schemas.user import PublicProfileResponse
        svc = UserService(db_session)
        r = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
        pub = await svc.get_public_profile(r.username)
        assert isinstance(pub.badges, list)
        # reputation may be None for brand new profile before any scoring
        # but the field must exist on the schema
        assert hasattr(pub, "reputation")

    @pytest.mark.asyncio
    async def test_public_and_private_profile_have_same_username(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        payload = _make_jwt_payload(uuid.uuid4())
        priv = await svc.get_my_profile(payload)
        pub = await svc.get_public_profile(priv.username)
        assert pub.id == priv.id
        assert pub.username == priv.username
        assert pub.display_name == priv.display_name

    # -----------------------------------------------------------------------
    # Checkpoint 22.5 — viewer-specific context (is_following, is_own_profile)
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_unauthenticated_viewer_gets_default_false_fields(self, db_session):
        """No viewer payload → is_own_profile=False, is_following=False."""
        from app.services.user import UserService
        svc = UserService(db_session)
        owner_payload = _make_jwt_payload(uuid.uuid4())
        owner = await svc.get_my_profile(owner_payload)

        pub = await svc.get_public_profile(owner.username, viewer_jwt_payload=None)

        assert pub.is_own_profile is False
        assert pub.is_following is False

    @pytest.mark.asyncio
    async def test_own_profile_sets_is_own_profile_true(self, db_session):
        """Owner viewing their own profile → is_own_profile=True, is_following=False."""
        from app.services.user import UserService
        svc = UserService(db_session)
        owner_payload = _make_jwt_payload(uuid.uuid4())
        owner = await svc.get_my_profile(owner_payload)

        pub = await svc.get_public_profile(owner.username, viewer_jwt_payload=owner_payload)

        assert pub.is_own_profile is True
        assert pub.is_following is False  # Cannot follow yourself

    @pytest.mark.asyncio
    async def test_is_following_true_when_viewer_already_follows(self, db_session):
        """Viewer who already follows target → is_following=True, is_own_profile=False."""
        from app.services.user import UserService
        svc = UserService(db_session)
        owner_payload = _make_jwt_payload(uuid.uuid4())
        viewer_payload = _make_jwt_payload(uuid.uuid4())
        owner = await svc.get_my_profile(owner_payload)
        await svc.get_my_profile(viewer_payload)
        await svc.follow_user(viewer_payload, owner.id)

        pub = await svc.get_public_profile(owner.username, viewer_jwt_payload=viewer_payload)

        assert pub.is_own_profile is False
        assert pub.is_following is True

    @pytest.mark.asyncio
    async def test_is_following_false_when_viewer_does_not_follow(self, db_session):
        """Viewer who has NOT followed target → is_following=False, is_own_profile=False."""
        from app.services.user import UserService
        svc = UserService(db_session)
        owner_payload = _make_jwt_payload(uuid.uuid4())
        viewer_payload = _make_jwt_payload(uuid.uuid4())
        owner = await svc.get_my_profile(owner_payload)
        await svc.get_my_profile(viewer_payload)  # Creates viewer profile; no follow

        pub = await svc.get_public_profile(owner.username, viewer_jwt_payload=viewer_payload)

        assert pub.is_own_profile is False
        assert pub.is_following is False

    @pytest.mark.asyncio
    async def test_is_following_false_after_unfollow(self, db_session):
        """Viewer unfollows → is_following transitions to False."""
        from app.services.user import UserService
        svc = UserService(db_session)
        owner_payload = _make_jwt_payload(uuid.uuid4())
        viewer_payload = _make_jwt_payload(uuid.uuid4())
        owner = await svc.get_my_profile(owner_payload)
        await svc.get_my_profile(viewer_payload)
        await svc.follow_user(viewer_payload, owner.id)
        await svc.unfollow_user(viewer_payload, owner.id)

        pub = await svc.get_public_profile(owner.username, viewer_jwt_payload=viewer_payload)

        assert pub.is_following is False

    @pytest.mark.asyncio
    async def test_malformed_viewer_payload_degrades_gracefully(self, db_session):
        """Payload missing 'sub' → silently falls back to unauthenticated defaults."""
        from app.services.user import UserService
        svc = UserService(db_session)
        owner_payload = _make_jwt_payload(uuid.uuid4())
        owner = await svc.get_my_profile(owner_payload)

        bad_payload = {"email": "x@x.com", "roles": ["USER"]}  # no 'sub'
        pub = await svc.get_public_profile(owner.username, viewer_jwt_payload=bad_payload)

        assert pub.is_own_profile is False
        assert pub.is_following is False

    @pytest.mark.asyncio
    async def test_auth_user_id_not_in_public_profile_response(self, db_session):
        """auth_user_id is never present on PublicProfileResponse even with viewer context."""
        from app.services.user import UserService
        svc = UserService(db_session)
        owner_payload = _make_jwt_payload(uuid.uuid4())
        owner = await svc.get_my_profile(owner_payload)

        pub = await svc.get_public_profile(owner.username, viewer_jwt_payload=owner_payload)

        assert not hasattr(pub, "auth_user_id")


# ===========================================================================
# [INTEGRATION] Followers and following lists (paginated)
# ===========================================================================

class TestFollowerFollowingLists:

    @pytest.mark.asyncio
    async def test_followers_list_empty_for_new_user(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        r = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
        result = await svc.get_followers(r.id, page=1, size=20)
        assert result.total == 0
        assert result.items == []
        assert result.page == 1
        assert result.size == 20

    @pytest.mark.asyncio
    async def test_following_list_empty_for_new_user(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        r = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
        result = await svc.get_following(r.id, page=1, size=20)
        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_a_follows_b_means_a_in_b_followers(self, db_session):
        """Relationship direction: A follows B → A appears in B's followers list."""
        from app.services.user import UserService
        svc = UserService(db_session)
        pa = _make_jwt_payload(uuid.uuid4())
        pb = _make_jwt_payload(uuid.uuid4())
        ra = await svc.get_my_profile(pa)
        rb = await svc.get_my_profile(pb)
        await svc.follow_user(pa, rb.id)  # A follows B
        b_followers = await svc.get_followers(rb.id, page=1, size=20)
        follower_ids = [f.id for f in b_followers.items]
        assert ra.id in follower_ids

    @pytest.mark.asyncio
    async def test_a_follows_b_means_b_in_a_following(self, db_session):
        """Relationship direction: A follows B → B appears in A's following list."""
        from app.services.user import UserService
        svc = UserService(db_session)
        pa = _make_jwt_payload(uuid.uuid4())
        pb = _make_jwt_payload(uuid.uuid4())
        ra = await svc.get_my_profile(pa)
        rb = await svc.get_my_profile(pb)
        await svc.follow_user(pa, rb.id)  # A follows B
        a_following = await svc.get_following(ra.id, page=1, size=20)
        following_ids = [f.id for f in a_following.items]
        assert rb.id in following_ids

    @pytest.mark.asyncio
    async def test_followers_list_total_matches_count(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        target = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
        # Three users follow target
        for _ in range(3):
            follower_payload = _make_jwt_payload(uuid.uuid4())
            await svc.get_my_profile(follower_payload)
            await svc.follow_user(follower_payload, target.id)
        result = await svc.get_followers(target.id, page=1, size=20)
        assert result.total == 3
        assert len(result.items) == 3

    @pytest.mark.asyncio
    async def test_following_list_total_matches_count(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        actor_payload = _make_jwt_payload(uuid.uuid4())
        actor = await svc.get_my_profile(actor_payload)
        # Actor follows two users
        for _ in range(2):
            other = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
            await svc.follow_user(actor_payload, other.id)
        result = await svc.get_following(actor.id, page=1, size=20)
        assert result.total == 2
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_followers_pagination_page_and_size(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        target = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
        # Create 5 followers
        for _ in range(5):
            fp = _make_jwt_payload(uuid.uuid4())
            await svc.get_my_profile(fp)
            await svc.follow_user(fp, target.id)
        page1 = await svc.get_followers(target.id, page=1, size=3)
        page2 = await svc.get_followers(target.id, page=2, size=3)
        assert len(page1.items) == 3
        assert len(page2.items) == 2
        assert page1.total == 5
        assert page2.total == 5
        # No overlap between pages
        p1_ids = {f.id for f in page1.items}
        p2_ids = {f.id for f in page2.items}
        assert p1_ids.isdisjoint(p2_ids)

    @pytest.mark.asyncio
    async def test_followers_items_have_required_fields(self, db_session):
        from app.services.user import UserService
        svc = UserService(db_session)
        target = await svc.get_my_profile(_make_jwt_payload(uuid.uuid4()))
        follower_payload = _make_jwt_payload(uuid.uuid4())
        follower = await svc.get_my_profile(follower_payload)
        await svc.follow_user(follower_payload, target.id)
        result = await svc.get_followers(target.id, page=1, size=20)
        assert len(result.items) == 1
        item = result.items[0]
        assert item.id == follower.id
        assert item.username == follower.username
        assert item.display_name == follower.display_name

    @pytest.mark.asyncio
    async def test_get_followers_unknown_user_raises(self, db_session):
        from app.services.user import UserService
        from shared.exceptions import NotFoundException
        svc = UserService(db_session)
        with pytest.raises(NotFoundException):
            await svc.get_followers(uuid.uuid4(), page=1, size=20)

    @pytest.mark.asyncio
    async def test_get_following_unknown_user_raises(self, db_session):
        from app.services.user import UserService
        from shared.exceptions import NotFoundException
        svc = UserService(db_session)
        with pytest.raises(NotFoundException):
            await svc.get_following(uuid.uuid4(), page=1, size=20)


# ===========================================================================
# [UNIT/INTEGRATION] Authorization boundaries
# Tests the JWT dependency and service-layer identity derivation.
# Shared dependency: shared.dependencies.get_current_user
# Raises UnauthorizedException for all invalid/missing token cases.
# ===========================================================================

class TestAuthorizationBoundaries:

    # ── Dependency-level tests (unit — no DB needed) ─────────────────────

    @pytest.mark.asyncio
    async def test_missing_authorization_header_raises(self):
        from shared.exceptions import UnauthorizedException
        from shared.dependencies import get_current_user
        # Simulate dependency call with no header
        with pytest.raises(UnauthorizedException) as exc:
            await get_current_user(authorization=None)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_header_no_bearer_prefix_raises(self):
        from shared.exceptions import UnauthorizedException
        from shared.dependencies import get_current_user
        with pytest.raises(UnauthorizedException):
            await get_current_user(authorization="Token abc123")

    @pytest.mark.asyncio
    async def test_invalid_jwt_string_raises(self):
        from shared.exceptions import UnauthorizedException
        from shared.dependencies import get_current_user
        with pytest.raises(UnauthorizedException):
            await get_current_user(authorization="Bearer not.a.jwt")

    @pytest.mark.asyncio
    async def test_jwt_signed_with_wrong_secret_raises(self):
        from shared.exceptions import UnauthorizedException
        from shared.dependencies import get_current_user
        from shared.utils.security import create_jwt_token
        from datetime import timedelta
        bad_token = create_jwt_token(
            data={"sub": str(uuid.uuid4()), "email": "x@x.com", "roles": ["USER"]},
            secret_key="wrong_secret_key",
            expires_delta=timedelta(hours=1),
        )
        with pytest.raises(UnauthorizedException):
            await get_current_user(authorization=f"Bearer {bad_token}")

    @pytest.mark.asyncio
    async def test_expired_jwt_raises(self):
        from shared.exceptions import UnauthorizedException
        from shared.dependencies import get_current_user
        from shared.utils.security import create_jwt_token
        from app.config.settings import settings
        from datetime import timedelta
        expired = create_jwt_token(
            data={"sub": str(uuid.uuid4()), "email": "x@x.com", "roles": ["USER"]},
            secret_key=settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(UnauthorizedException):
            await get_current_user(authorization=f"Bearer {expired}")

    @pytest.mark.asyncio
    async def test_valid_jwt_returns_payload(self):
        from shared.dependencies import get_current_user
        from app.config.settings import settings
        from shared.utils.security import create_jwt_token
        from datetime import timedelta
        uid = uuid.uuid4()
        token = create_jwt_token(
            data={"sub": str(uid), "email": "valid@test.com", "roles": ["USER"]},
            secret_key=settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
            expires_delta=timedelta(hours=1),
        )
        payload = await get_current_user(authorization=f"Bearer {token}")
        assert payload["sub"] == str(uid)
        assert payload["email"] == "valid@test.com"
        assert "USER" in payload["roles"]

    # ── Service-layer identity derivation (integration — uses DB) ────────

    @pytest.mark.asyncio
    async def test_get_my_profile_derives_identity_from_jwt_sub(self, db_session):
        """auth_user_id comes from JWT sub — not from a client-supplied field."""
        from app.services.user import UserService
        uid = uuid.uuid4()
        payload = _make_jwt_payload(uid)
        svc = UserService(db_session)
        result = await svc.get_my_profile(payload)
        assert result.auth_user_id == uid

    @pytest.mark.asyncio
    async def test_different_jwt_sub_gets_different_profile(self, db_session):
        """Two tokens with different subs produce two separate profiles."""
        from app.services.user import UserService
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        p2 = _make_jwt_payload(uuid.uuid4())
        r1 = await svc.get_my_profile(p1)
        r2 = await svc.get_my_profile(p2)
        assert r1.id != r2.id
        assert r1.auth_user_id != r2.auth_user_id

    @pytest.mark.asyncio
    async def test_update_profile_uses_jwt_sub_not_body_id(self, db_session):
        """Updating profile uses JWT identity — cannot update another user's profile
        by manipulating request body since auth_user_id comes from JWT only."""
        from app.services.user import UserService
        svc = UserService(db_session)
        p1 = _make_jwt_payload(uuid.uuid4())
        p2 = _make_jwt_payload(uuid.uuid4())
        # Both users exist
        r1 = await svc.get_my_profile(p1)
        await svc.get_my_profile(p2)
        # p1 updates their own display name
        updated = await svc.update_my_profile(
            p1, username=None, display_name="I Own This", bio=None, city=None, country=None
        )
        assert updated.display_name == "I Own This"
        # p2's profile is unchanged
        r2_fresh = await svc.get_my_profile(p2)
        assert r2_fresh.display_name != "I Own This"

    @pytest.mark.asyncio
    async def test_missing_sub_in_payload_raises(self, db_session):
        """Payload without 'sub' raises UnauthorizedException."""
        from app.services.user import UserService
        from shared.exceptions import UnauthorizedException
        svc = UserService(db_session)
        bad_payload = {"email": "x@x.com", "roles": ["USER"]}  # no 'sub'
        with pytest.raises(UnauthorizedException):
            await svc.get_my_profile(bad_payload)
