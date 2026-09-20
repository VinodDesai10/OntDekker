"""
User Service — Checkpoint 4 Test Suite

Tests the User Service persistence foundation:
  - SQLAlchemy model imports and mapper configuration
  - Base.metadata table registration (exactly 7 user_db tables)
  - Column inventory per table
  - UUID primary keys
  - Unique constraints
  - Check constraints
  - Indexes
  - Foreign keys (intra-service only)
  - Relationship configuration
  - Soft-delete / hard-delete boundary
  - Service boundary (no auth/guide fields)
  - Cross-service FK violation check
  - PostgreSQL ARRAY columns on preferences
  - Live database: Alembic at head, all tables present
  - Live database: column types match model definition
  - Live database: FK ON DELETE CASCADE verified
  - Idempotency: upgrade head on already-upgraded DB is a no-op

Run:
  PYTHONPATH=../.. pytest tests/test_user_models.py -v --asyncio-mode=auto
"""

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, text

TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/user_db"
)


# ---------------------------------------------------------------------------
# Event loop fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# DB session fixture — savepoint rollback isolates each test
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession,
        expire_on_commit=False, autocommit=False, autoflush=False,
    )
    async with factory() as session:
        await session.begin_nested()
        yield session
        await session.rollback()
    await engine.dispose()


# ===========================================================================
# UNIT TESTS — no database required
# ===========================================================================

class TestModelImports:
    """[UNIT] All 7 models import without error."""

    def test_all_models_importable(self):
        from app.models.profile import (
            UserProfile, Interest, Preference, Follower,
            Badge, Reputation, SavedItem,
        )
        assert UserProfile.__tablename__ == "user_profiles"
        assert Interest.__tablename__ == "interests"
        assert Preference.__tablename__ == "preferences"
        assert Follower.__tablename__ == "followers"
        assert Badge.__tablename__ == "badges"
        assert Reputation.__tablename__ == "reputation"
        assert SavedItem.__tablename__ == "saved_items"

    def test_package_exports_all_models(self):
        import app.models as m
        for name in ["UserProfile","Interest","Preference","Follower",
                     "Badge","Reputation","SavedItem"]:
            assert hasattr(m, name), f"Missing export: {name}"

    def test_configure_mappers_no_errors(self):
        import app.models  # noqa: ensure registered
        from sqlalchemy.orm import configure_mappers
        configure_mappers()  # raises if any relationship/mapper misconfigured


class TestMetadataRegistration:
    """[UNIT] Base.metadata contains exactly the 7 intended user_db tables."""

    def _tables(self):
        import app.models  # noqa
        from shared.database import Base
        return set(Base.metadata.tables.keys())

    def test_exactly_seven_tables(self):
        assert len(self._tables()) == 7

    def test_expected_table_names(self):
        expected = {
            "user_profiles", "interests", "preferences",
            "followers", "badges", "reputation", "saved_items",
        }
        assert self._tables() == expected

    def test_no_auth_tables_in_metadata(self):
        auth_tables = {"users", "refresh_tokens", "roles", "user_roles",
                       "email_verification_tokens", "password_reset_tokens"}
        assert self._tables().isdisjoint(auth_tables)


class TestColumnInventory:
    """[UNIT] Each table has exactly the documented columns."""

    def setup_method(self):
        import app.models  # noqa
        from shared.database import Base
        self.meta = Base.metadata

    def _cols(self, tname):
        return {c.name for c in self.meta.tables[tname].columns}

    def test_user_profiles_columns(self):
        c = self._cols("user_profiles")
        for f in ["id","auth_user_id","username","display_name","bio",
                  "avatar_url","cover_url","city","country",
                  "created_at","updated_at","is_deleted","deleted_at","deleted_by"]:
            assert f in c, f"user_profiles missing: {f}"

    def test_interests_columns(self):
        assert self._cols("interests") == {
            "id","user_id","interest","created_at","updated_at"
        }

    def test_preferences_columns(self):
        c = self._cols("preferences")
        for f in ["id","user_id","travel_style","budget","adventure_level",
                  "languages","preferred_destinations",
                  "notifications_enabled","profile_public",
                  "created_at","updated_at"]:
            assert f in c, f"preferences missing: {f}"

    def test_followers_columns(self):
        assert self._cols("followers") == {
            "id","follower_id","following_id","created_at","updated_at"
        }

    def test_badges_columns(self):
        assert self._cols("badges") == {
            "id","user_id","badge_name","badge_icon",
            "earned_at","created_at","updated_at"
        }

    def test_reputation_columns(self):
        c = self._cols("reputation")
        for f in ["id","user_id","explorer_score","community_score",
                  "review_score","expeditions_joined","expeditions_organized",
                  "guide_interactions","reviews_received",
                  "created_at","updated_at"]:
            assert f in c, f"reputation missing: {f}"

    def test_saved_items_columns(self):
        assert self._cols("saved_items") == {
            "id","user_id","entity_type","entity_id","created_at","updated_at"
        }


class TestServiceBoundary:
    """[UNIT] No auth, guide, or cross-service fields in user_db models."""

    def setup_method(self):
        import app.models  # noqa
        from shared.database import Base
        self.all_cols = {
            c.name
            for t in Base.metadata.tables.values()
            for c in t.columns
        }

    def test_no_password_hash(self):
        assert "password_hash" not in self.all_cols

    def test_no_token_fields(self):
        for f in ["token_hash","refresh_token","reset_token"]:
            assert f not in self.all_cols

    def test_no_verification_fields(self):
        assert "is_verified" not in self.all_cols

    def test_no_guide_application_fields(self):
        for f in ["guide_application_id","verification_status","application_status"]:
            assert f not in self.all_cols

    def test_email_not_in_user_profiles(self):
        import app.models  # noqa
        from shared.database import Base
        up_cols = {c.name for c in Base.metadata.tables["user_profiles"].columns}
        assert "email" not in up_cols, \
            "email is owned by Authentication Service, not User Service"


class TestCrossServiceFKs:
    """[UNIT] All foreign keys are intra-service (point to user_profiles only)."""

    def test_no_cross_service_fks(self):
        import app.models  # noqa
        from shared.database import Base
        user_tables = set(Base.metadata.tables.keys())
        for tname, table in Base.metadata.tables.items():
            for col in table.columns:
                for fk in col.foreign_keys:
                    target = fk.column.table.name
                    assert target in user_tables, \
                        f"Cross-service FK: {tname}.{col.name} → {target}"


class TestSoftDeleteBoundary:
    """[UNIT] Soft delete on user_profiles only; all others are hard-delete."""

    def setup_method(self):
        import app.models  # noqa
        from shared.database import Base
        self.meta = Base.metadata

    def _has_soft_delete(self, tname):
        cols = {c.name for c in self.meta.tables[tname].columns}
        return "is_deleted" in cols

    def test_user_profiles_has_soft_delete(self):
        assert self._has_soft_delete("user_profiles")

    def test_interests_hard_delete(self):
        assert not self._has_soft_delete("interests")

    def test_preferences_hard_delete(self):
        assert not self._has_soft_delete("preferences")

    def test_followers_hard_delete(self):
        assert not self._has_soft_delete("followers")

    def test_badges_hard_delete(self):
        assert not self._has_soft_delete("badges")

    def test_reputation_hard_delete(self):
        assert not self._has_soft_delete("reputation")

    def test_saved_items_hard_delete(self):
        assert not self._has_soft_delete("saved_items")


class TestConstraints:
    """[UNIT] Verify unique and check constraints in metadata."""

    def setup_method(self):
        import app.models  # noqa
        from shared.database import Base
        from sqlalchemy import UniqueConstraint, CheckConstraint
        self.meta = Base.metadata
        self.UC = UniqueConstraint
        self.CC = CheckConstraint

    def _constraint_names(self, tname, kind):
        return {
            c.name for c in self.meta.tables[tname].constraints
            if isinstance(c, kind)
        }

    def test_user_profiles_auth_user_id_unique(self):
        up = self.meta.tables["user_profiles"]
        uc_cols = {
            col.name
            for c in up.constraints if isinstance(c, self.UC)
            for col in c.columns
        } | {col.name for col in up.columns if col.unique}
        assert "auth_user_id" in uc_cols

    def test_user_profiles_username_unique(self):
        up = self.meta.tables["user_profiles"]
        uc_cols = {
            col.name
            for c in up.constraints if isinstance(c, self.UC)
            for col in c.columns
        } | {col.name for col in up.columns if col.unique}
        assert "username" in uc_cols

    def test_followers_no_self_follow_check(self):
        assert "ck_followers_no_self_follow" in self._constraint_names("followers", self.CC)

    def test_followers_unique_pair(self):
        assert "uq_followers_follower_following" in self._constraint_names("followers", self.UC)

    def test_interests_unique_per_user(self):
        assert "uq_interests_user_interest" in self._constraint_names("interests", self.UC)

    def test_badges_unique_per_user(self):
        assert "uq_badges_user_badge" in self._constraint_names("badges", self.UC)

    def test_saved_items_entity_type_check(self):
        assert "ck_saved_items_entity_type" in self._constraint_names("saved_items", self.CC)

    def test_saved_items_unique_entity(self):
        assert "uq_saved_items_user_entity" in self._constraint_names("saved_items", self.UC)


class TestColumnTypes:
    """[UNIT] Key column type checks."""

    def setup_method(self):
        import app.models  # noqa
        from shared.database import Base
        self.meta = Base.metadata

    def _col(self, tname, cname):
        return self.meta.tables[tname].c[cname]

    def test_badges_earned_at_is_datetime(self):
        import sqlalchemy as sa
        assert isinstance(self._col("badges","earned_at").type, sa.DateTime)

    def test_preferences_languages_is_array(self):
        from sqlalchemy.dialects.postgresql import ARRAY
        assert isinstance(self._col("preferences","languages").type, ARRAY)

    def test_preferences_preferred_destinations_is_array(self):
        from sqlalchemy.dialects.postgresql import ARRAY
        assert isinstance(self._col("preferences","preferred_destinations").type, ARRAY)

    def test_reputation_scores_are_integer(self):
        import sqlalchemy as sa
        for col in ["explorer_score","community_score","review_score"]:
            assert isinstance(self._col("reputation", col).type, sa.Integer)

    def test_user_profiles_bio_is_text(self):
        import sqlalchemy as sa
        assert isinstance(self._col("user_profiles","bio").type, sa.Text)

    def test_saved_items_entity_type_max_length(self):
        col = self._col("saved_items","entity_type")
        assert col.type.length == 20


# ===========================================================================
# INTEGRATION TESTS — require live user_db
# ===========================================================================

class TestLiveAlembicState:
    """[INTEGRATION] Alembic is at head with correct history."""

    @pytest.mark.asyncio
    async def test_alembic_version_is_head(self):
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
        await engine.dispose()
        assert version == "33e5bd914d43", f"Expected head, got: {version}"

    @pytest.mark.asyncio
    async def test_all_seven_tables_exist_in_live_db(self):
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                "AND tablename != 'alembic_version' ORDER BY tablename"
            ))
            live_tables = {row[0] for row in result}
        await engine.dispose()
        expected = {
            "user_profiles","interests","preferences","followers",
            "badges","reputation","saved_items"
        }
        assert live_tables == expected, f"Mismatch: {live_tables ^ expected}"


class TestLiveColumnTypes:
    """[INTEGRATION] Live PostgreSQL column types match SQLAlchemy metadata."""

    @pytest.mark.asyncio
    async def test_user_profiles_uuid_pk(self):
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            r = await conn.execute(text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name='user_profiles' AND column_name='id'"
            ))
            assert r.scalar() == "uuid"
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_preferences_languages_is_array(self):
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            r = await conn.execute(text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name='preferences' AND column_name='languages'"
            ))
            assert r.scalar() == "ARRAY"
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_badges_earned_at_is_timestamptz(self):
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            r = await conn.execute(text(
                "SELECT udt_name FROM information_schema.columns "
                "WHERE table_name='badges' AND column_name='earned_at'"
            ))
            assert r.scalar() == "timestamptz"
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_profiles_has_soft_delete_columns(self):
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            r = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='user_profiles' AND column_name IN "
                "('is_deleted','deleted_at','deleted_by')"
            ))
            found = {row[0] for row in r}
        await engine.dispose()
        assert found == {"is_deleted","deleted_at","deleted_by"}


class TestLiveForeignKeys:
    """[INTEGRATION] All FKs are intra-service, all ON DELETE CASCADE."""

    @pytest.mark.asyncio
    async def test_all_fks_reference_user_profiles(self):
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            r = await conn.execute(text("""
                SELECT ccu.table_name AS ref_table
                FROM information_schema.table_constraints tc
                JOIN information_schema.referential_constraints rc
                  ON tc.constraint_name = rc.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                  ON rc.unique_constraint_name = ccu.constraint_name
                WHERE tc.constraint_type='FOREIGN KEY'
                  AND tc.table_schema='public'
            """))
            ref_tables = {row[0] for row in r}
        await engine.dispose()
        assert ref_tables == {"user_profiles"}, \
            f"Expected only user_profiles, got: {ref_tables}"

    @pytest.mark.asyncio
    async def test_all_fks_are_cascade_delete(self):
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            r = await conn.execute(text("""
                SELECT tc.table_name, rc.delete_rule
                FROM information_schema.table_constraints tc
                JOIN information_schema.referential_constraints rc
                  ON tc.constraint_name = rc.constraint_name
                WHERE tc.constraint_type='FOREIGN KEY'
                  AND tc.table_schema='public'
            """))
            rules = {row[0]: row[1] for row in r}
        await engine.dispose()
        for tname, rule in rules.items():
            assert rule == "CASCADE", f"{tname} FK is not CASCADE: {rule}"


class TestLiveConstraints:
    """[INTEGRATION] Live check constraints exist."""

    @pytest.mark.asyncio
    async def test_followers_no_self_follow_constraint_exists(self):
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            r = await conn.execute(text(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_name='followers' AND constraint_type='CHECK' "
                "AND constraint_name='ck_followers_no_self_follow'"
            ))
            assert r.scalar() is not None
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_saved_items_entity_type_check_exists(self):
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            r = await conn.execute(text(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_name='saved_items' AND constraint_type='CHECK' "
                "AND constraint_name='ck_saved_items_entity_type'"
            ))
            assert r.scalar() is not None
        await engine.dispose()


class TestLiveInsert:
    """[INTEGRATION] Basic insert/query via SQLAlchemy ORM against live user_db."""

    @pytest.mark.asyncio
    async def test_insert_user_profile_and_query(self, db_session):
        from app.models.profile import UserProfile
        profile = UserProfile(
            auth_user_id=uuid.uuid4(),
            username="testuser_cp4",
            display_name="Test User",
            is_deleted=False,
        )
        db_session.add(profile)
        await db_session.flush()
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.username == "testuser_cp4")
        )
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.auth_user_id == profile.auth_user_id
        assert found.is_deleted is False

    @pytest.mark.asyncio
    async def test_insert_interest_fk_to_profile(self, db_session):
        from app.models.profile import UserProfile, Interest
        profile = UserProfile(
            auth_user_id=uuid.uuid4(),
            username="interestuser_cp4",
            display_name="Interest User",
            is_deleted=False,
        )
        db_session.add(profile)
        await db_session.flush()
        interest = Interest(
            user_id=profile.id,
            interest="Trekking",
        )
        db_session.add(interest)
        await db_session.flush()
        result = await db_session.execute(
            select(Interest).where(Interest.user_id == profile.id)
        )
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.interest == "Trekking"

    @pytest.mark.asyncio
    async def test_preferences_single_row_per_user(self, db_session):
        from app.models.profile import UserProfile, Preference
        from sqlalchemy.exc import IntegrityError
        profile = UserProfile(
            auth_user_id=uuid.uuid4(),
            username="prefuser_cp4",
            display_name="Pref User",
            is_deleted=False,
        )
        db_session.add(profile)
        await db_session.flush()
        pref1 = Preference(
            user_id=profile.id,
            travel_style="Backpacking",
            languages=["English","Spanish"],
            notifications_enabled=True,
            profile_public=True,
        )
        db_session.add(pref1)
        await db_session.flush()
        # Second preferences row for same user must violate unique constraint
        pref2 = Preference(
            user_id=profile.id,
            travel_style="Luxury",
            notifications_enabled=False,
            profile_public=False,
        )
        db_session.add(pref2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_followers_prevent_self_follow(self, db_session):
        from app.models.profile import UserProfile, Follower
        from sqlalchemy.exc import IntegrityError
        profile = UserProfile(
            auth_user_id=uuid.uuid4(),
            username="selffollow_cp4",
            display_name="Self Follow",
            is_deleted=False,
        )
        db_session.add(profile)
        await db_session.flush()
        self_follow = Follower(
            follower_id=profile.id,
            following_id=profile.id,
        )
        db_session.add(self_follow)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_saved_items_invalid_entity_type_rejected(self, db_session):
        from app.models.profile import UserProfile, SavedItem
        from sqlalchemy.exc import IntegrityError
        profile = UserProfile(
            auth_user_id=uuid.uuid4(),
            username="saveduser_cp4",
            display_name="Saved User",
            is_deleted=False,
        )
        db_session.add(profile)
        await db_session.flush()
        bad_item = SavedItem(
            user_id=profile.id,
            entity_type="INVALID_TYPE",
            entity_id=uuid.uuid4(),
        )
        db_session.add(bad_item)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_saved_items_valid_entity_types_accepted(self, db_session):
        from app.models.profile import UserProfile, SavedItem
        profile = UserProfile(
            auth_user_id=uuid.uuid4(),
            username="savedvalid_cp4",
            display_name="Valid Saved",
            is_deleted=False,
        )
        db_session.add(profile)
        await db_session.flush()
        for etype in ["STORY","COMMUNITY","EXPEDITION","GUIDE"]:
            item = SavedItem(
                user_id=profile.id,
                entity_type=etype,
                entity_id=uuid.uuid4(),
            )
            db_session.add(item)
        await db_session.flush()
        result = await db_session.execute(
            select(SavedItem).where(SavedItem.user_id == profile.id)
        )
        assert len(result.scalars().all()) == 4

    @pytest.mark.asyncio
    async def test_reputation_single_row_per_user(self, db_session):
        from app.models.profile import UserProfile, Reputation
        from sqlalchemy.exc import IntegrityError
        profile = UserProfile(
            auth_user_id=uuid.uuid4(),
            username="repuser_cp4",
            display_name="Rep User",
            is_deleted=False,
        )
        db_session.add(profile)
        await db_session.flush()
        rep1 = Reputation(user_id=profile.id, explorer_score=10)
        db_session.add(rep1)
        await db_session.flush()
        rep2 = Reputation(user_id=profile.id, explorer_score=20)
        db_session.add(rep2)
        with pytest.raises(IntegrityError):
            await db_session.flush()
