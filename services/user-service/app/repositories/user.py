"""
User Service — Repository Layer

Pure persistence: CRUD + queries only.
No business logic, no HTTP concerns, no Kafka events.

All operations use the AsyncSession passed by the FastAPI get_db dependency.
Repositories use flush() for intermediate writes; commit is managed by get_db.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, func, update, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import (
    Badge,
    Follower,
    Interest,
    Preference,
    Reputation,
    SavedItem,
    UserProfile,
)


# ---------------------------------------------------------------------------
# ProfileRepository
# ---------------------------------------------------------------------------

class ProfileRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_id(self, profile_id: uuid.UUID) -> Optional[UserProfile]:
        r = await self._s.execute(
            select(UserProfile).where(
                UserProfile.id == profile_id,
                UserProfile.is_deleted == False,  # noqa: E712
            )
        )
        return r.scalar_one_or_none()

    async def get_by_auth_user_id(self, auth_user_id: uuid.UUID) -> Optional[UserProfile]:
        r = await self._s.execute(
            select(UserProfile).where(
                UserProfile.auth_user_id == auth_user_id,
                UserProfile.is_deleted == False,  # noqa: E712
            )
        )
        return r.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[UserProfile]:
        r = await self._s.execute(
            select(UserProfile).where(
                UserProfile.username == username,
                UserProfile.is_deleted == False,  # noqa: E712
            )
        )
        return r.scalar_one_or_none()

    async def get_by_ids(self, profile_ids: List[uuid.UUID]) -> List[UserProfile]:
        """Fetch multiple profiles by their IDs in a single query."""
        if not profile_ids:
            return []
        r = await self._s.execute(
            select(UserProfile).where(
                UserProfile.id.in_(profile_ids),
                UserProfile.is_deleted == False,  # noqa: E712
            )
        )
        return list(r.scalars().all())

    async def get_by_auth_user_ids(self, auth_user_ids: List[uuid.UUID]) -> List[UserProfile]:
        """Fetch multiple profiles by their auth_user_id in a single query.

        Used when the caller holds auth-service UUIDs (the JWT sub claim) rather
        than user-service profile UUIDs — e.g. feed posts, community memberships.
        """
        if not auth_user_ids:
            return []
        r = await self._s.execute(
            select(UserProfile).where(
                UserProfile.auth_user_id.in_(auth_user_ids),
                UserProfile.is_deleted == False,  # noqa: E712
            )
        )
        return list(r.scalars().all())

    async def create(
        self,
        auth_user_id: uuid.UUID,
        username: str,
        display_name: str,
    ) -> UserProfile:
        """
        Insert a new profile row.
        Raises IntegrityError if auth_user_id or username is already taken.
        Callers catch this and convert to ConflictException.
        """
        profile = UserProfile(
            auth_user_id=auth_user_id,
            username=username,
            display_name=display_name,
            is_deleted=False,
        )
        self._s.add(profile)
        await self._s.flush()
        return profile

    async def update(self, profile_id: uuid.UUID, **fields) -> None:
        fields["updated_at"] = datetime.now(timezone.utc)
        await self._s.execute(
            update(UserProfile)
            .where(UserProfile.id == profile_id)
            .values(**fields)
        )

    async def follower_count(self, profile_id: uuid.UUID) -> int:
        r = await self._s.execute(
            select(func.count()).select_from(Follower).where(
                Follower.following_id == profile_id
            )
        )
        return r.scalar() or 0

    async def following_count(self, profile_id: uuid.UUID) -> int:
        r = await self._s.execute(
            select(func.count()).select_from(Follower).where(
                Follower.follower_id == profile_id
            )
        )
        return r.scalar() or 0


# ---------------------------------------------------------------------------
# InterestRepository
# ---------------------------------------------------------------------------

class InterestRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_user(self, user_id: uuid.UUID) -> List[Interest]:
        r = await self._s.execute(
            select(Interest).where(Interest.user_id == user_id)
        )
        return list(r.scalars().all())

    async def replace_all(self, user_id: uuid.UUID, interests: List[str]) -> None:
        """Delete all existing interests and insert new ones atomically."""
        await self._s.execute(
            delete(Interest).where(Interest.user_id == user_id)
        )
        for name in interests:
            self._s.add(Interest(user_id=user_id, interest=name))
        await self._s.flush()


# ---------------------------------------------------------------------------
# PreferenceRepository
# ---------------------------------------------------------------------------

class PreferenceRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_user(self, user_id: uuid.UUID) -> Optional[Preference]:
        r = await self._s.execute(
            select(Preference).where(Preference.user_id == user_id)
        )
        return r.scalar_one_or_none()

    async def upsert(self, user_id: uuid.UUID, **fields) -> Preference:
        """Create or update preferences for a user (single row per user)."""
        existing = await self.get_by_user(user_id)
        if existing is None:
            pref = Preference(
                user_id=user_id,
                notifications_enabled=fields.pop("notifications_enabled", True),
                profile_public=fields.pop("profile_public", True),
                **{k: v for k, v in fields.items() if v is not None},
            )
            self._s.add(pref)
            await self._s.flush()
            return pref
        else:
            fields["updated_at"] = datetime.now(timezone.utc)
            await self._s.execute(
                update(Preference)
                .where(Preference.user_id == user_id)
                .values(**{k: v for k, v in fields.items() if v is not None})
            )
            await self._s.flush()
            return await self.get_by_user(user_id)


# ---------------------------------------------------------------------------
# FollowerRepository
# ---------------------------------------------------------------------------

class FollowerRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def follow(self, follower_id: uuid.UUID, following_id: uuid.UUID) -> None:
        """
        Idempotent follow — uses INSERT ON CONFLICT DO NOTHING.
        Never raises IntegrityError under concurrent duplicate requests.
        """
        stmt = (
            pg_insert(Follower)
            .values(
                id=uuid.uuid4(),
                follower_id=follower_id,
                following_id=following_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_nothing(constraint="uq_followers_follower_following")
        )
        await self._s.execute(stmt)

    async def unfollow(self, follower_id: uuid.UUID, following_id: uuid.UUID) -> None:
        await self._s.execute(
            delete(Follower).where(
                Follower.follower_id == follower_id,
                Follower.following_id == following_id,
            )
        )

    async def is_following(self, follower_id: uuid.UUID, following_id: uuid.UUID) -> bool:
        r = await self._s.execute(
            select(func.count()).select_from(Follower).where(
                Follower.follower_id == follower_id,
                Follower.following_id == following_id,
            )
        )
        return (r.scalar() or 0) > 0

    async def get_followers(
        self, profile_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> List[uuid.UUID]:
        """Return IDs of users who follow profile_id."""
        r = await self._s.execute(
            select(Follower.follower_id)
            .where(Follower.following_id == profile_id)
            .offset(offset)
            .limit(limit)
        )
        return [row[0] for row in r.all()]

    async def get_following(
        self, profile_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> List[uuid.UUID]:
        """Return IDs of users that profile_id follows."""
        r = await self._s.execute(
            select(Follower.following_id)
            .where(Follower.follower_id == profile_id)
            .offset(offset)
            .limit(limit)
        )
        return [row[0] for row in r.all()]

    async def follower_count(self, profile_id: uuid.UUID) -> int:
        r = await self._s.execute(
            select(func.count()).select_from(Follower).where(
                Follower.following_id == profile_id
            )
        )
        return r.scalar() or 0

    async def following_count(self, profile_id: uuid.UUID) -> int:
        r = await self._s.execute(
            select(func.count()).select_from(Follower).where(
                Follower.follower_id == profile_id
            )
        )
        return r.scalar() or 0


# ---------------------------------------------------------------------------
# BadgeRepository
# ---------------------------------------------------------------------------

class BadgeRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_user(self, user_id: uuid.UUID) -> List[Badge]:
        r = await self._s.execute(
            select(Badge).where(Badge.user_id == user_id)
        )
        return list(r.scalars().all())


# ---------------------------------------------------------------------------
# ReputationRepository
# ---------------------------------------------------------------------------

class ReputationRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_user(self, user_id: uuid.UUID) -> Optional[Reputation]:
        r = await self._s.execute(
            select(Reputation).where(Reputation.user_id == user_id)
        )
        return r.scalar_one_or_none()

    async def create_default(self, user_id: uuid.UUID) -> Reputation:
        """Create a zeroed reputation record for a new profile."""
        rep = Reputation(user_id=user_id)
        self._s.add(rep)
        await self._s.flush()
        return rep


# ---------------------------------------------------------------------------
# SavedItemRepository
# ---------------------------------------------------------------------------

class SavedItemRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        entity_type: Optional[str] = None,
    ) -> List[SavedItem]:
        q = select(SavedItem).where(SavedItem.user_id == user_id)
        if entity_type:
            q = q.where(SavedItem.entity_type == entity_type)
        r = await self._s.execute(q)
        return list(r.scalars().all())

    async def save(
        self,
        user_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> SavedItem:
        """
        Idempotent save — returns existing record if already saved.
        Uses INSERT ON CONFLICT DO NOTHING to prevent duplicate constraint errors.
        """
        stmt = (
            pg_insert(SavedItem)
            .values(
                id=uuid.uuid4(),
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_nothing(constraint="uq_saved_items_user_entity")
        )
        await self._s.execute(stmt)
        await self._s.flush()
        # Return the now-existing record
        r = await self._s.execute(
            select(SavedItem).where(
                SavedItem.user_id == user_id,
                SavedItem.entity_type == entity_type,
                SavedItem.entity_id == entity_id,
            )
        )
        return r.scalar_one()

    async def unsave(
        self,
        user_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> None:
        await self._s.execute(
            delete(SavedItem).where(
                SavedItem.user_id == user_id,
                SavedItem.entity_type == entity_type,
                SavedItem.entity_id == entity_id,
            )
        )
