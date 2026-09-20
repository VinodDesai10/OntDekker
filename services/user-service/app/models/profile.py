"""
User Service — SQLAlchemy ORM Models

Database: user_db
Owner: Developer 1

Tables:
  - user_profiles      : Core public/private profile (soft-deleted)
  - interests          : User travel interests (hard-deleted child records)
  - preferences        : Single-row travel preferences per user (hard-deleted)
  - followers          : Follow relationships between users (hard-deleted)
  - badges             : Awarded badges per user (hard-deleted)
  - reputation         : Single-row reputation record per user (hard-deleted)
  - saved_items        : Cross-service saved entity references (hard-deleted)

Design decisions (all derivable from authoritative documentation):

  Soft delete:
    - user_profiles only — documentation explicitly lists "Profiles" as a
      soft-delete example (06-database-architecture.md).
    - All other tables use hard delete — they are child/secondary records
      whose lifecycle is tied to the profile.

  preferences — normalized columns:
    The doc lists what to store (travel_style, budget, languages, etc.) but
    does not specify column names. Normalized columns are used; languages
    uses PostgreSQL ARRAY(Text) since the doc shows it as a list attribute
    of the preferences record, not a separate documented table.

  saved_items — entity_type + entity_id:
    Cross-service references use the entity_type + entity_id pattern,
    consistent with recommendation_history in the same codebase
    (03-microservices.md Part 7, recommendation_history schema).

  No cross-service FK constraints:
    auth_user_id in user_profiles is a plain UUID column — no REFERENCES
    to auth_db.users(id). Enforced by application-level validation only.
    (06-database-architecture.md: "Across services: NO foreign keys.")

  UUID primary keys:
    Every table — consistent with platform-wide convention.

  Timestamps:
    TimestampMixin on all tables (created_at, updated_at).
"""

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base, SoftDeleteMixin, TimestampMixin


# ---------------------------------------------------------------------------
# user_profiles
# ---------------------------------------------------------------------------

class UserProfile(Base, TimestampMixin, SoftDeleteMixin):
    """
    Core profile record.

    auth_user_id: plain UUID application-level reference to auth_db.users.id.
                  No PostgreSQL foreign key — cross-service FK prohibited.

    username: unique identifier chosen by the user (3–30 chars, alphanumeric+_).
    display_name: human-readable name shown on the platform.
    avatar_url / cover_url: object URLs in MinIO; set when user uploads images.

    Soft-deleted because profile removal must support audit trails and
    moderation recovery. (06-database-architecture.md: "Profiles" listed
    as a soft-delete example.)
    """

    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    # Application-level reference to auth_db.users.id — NOT a FK constraint
    auth_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
    )
    username: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
    )
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    bio: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )
    avatar_url: Mapped[str] = mapped_column(
        String(500),
        nullable=True,
    )
    cover_url: Mapped[str] = mapped_column(
        String(500),
        nullable=True,
    )
    city: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )

    # Intra-service relationships
    interests: Mapped[List["Interest"]] = relationship(
        "Interest",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    preferences: Mapped["Preference"] = relationship(
        "Preference",
        back_populates="profile",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    badges: Mapped[List["Badge"]] = relationship(
        "Badge",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reputation: Mapped["Reputation"] = relationship(
        "Reputation",
        back_populates="profile",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    saved_items: Mapped[List["SavedItem"]] = relationship(
        "SavedItem",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # followers/following use separate FKs — see Follower model
    followers: Mapped[List["Follower"]] = relationship(
        "Follower",
        foreign_keys="Follower.following_id",
        back_populates="following",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    following: Mapped[List["Follower"]] = relationship(
        "Follower",
        foreign_keys="Follower.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_user_profiles_auth_user_id", "auth_user_id"),
        Index("ix_user_profiles_username", "username"),
        Index("ix_user_profiles_is_deleted", "is_deleted"),
        Index("ix_user_profiles_created_at", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserProfile id={self.id} username={self.username!r}>"


# ---------------------------------------------------------------------------
# interests
# ---------------------------------------------------------------------------

class Interest(Base, TimestampMixin):
    """
    A single travel interest tagged to a user profile.

    Examples: Trekking, Backpacking, Wildlife, Heritage, Photography.
    Multiple rows per user — each interest is its own record.
    Hard-deleted when removed.
    """

    __tablename__ = "interests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    interest: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="interests"
    )

    __table_args__ = (
        # A user cannot tag the same interest twice
        UniqueConstraint("user_id", "interest", name="uq_interests_user_interest"),
        Index("ix_interests_user_id", "user_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Interest user_id={self.user_id} interest={self.interest!r}>"


# ---------------------------------------------------------------------------
# preferences
# ---------------------------------------------------------------------------

class Preference(Base, TimestampMixin):
    """
    Single-row travel preferences record per user.

    Documentation specifies storing:
      - Preferred Travel Style
      - Budget Preference
      - Languages (list attribute of preferences — stored as PostgreSQL Text[])
      - Preferred Destinations (from Travel Preferences section of doc)
      - Adventure Level (from Travel Preferences section of doc)
      - Notification Preferences
      - Privacy Preferences

    Column names follow snake_case convention.

    languages: PostgreSQL ARRAY(Text) — the documentation lists languages as
    an attribute of preferences, not as a separate documented table.
    preferred_destinations: PostgreSQL ARRAY(Text) — same reasoning.

    notifications_enabled / profile_public: boolean flags representing
    "Notification Preferences" and "Privacy Preferences" at the foundation
    level; richer preference types belong in Checkpoint 5 schema refinement.

    Hard-deleted with the parent profile (cascade).
    """

    __tablename__ = "preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # exactly one preferences row per user
    )
    travel_style: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )
    budget: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )
    adventure_level: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )
    # PostgreSQL native array for multi-valued list attributes
    languages: Mapped[list] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )
    preferred_destinations: Mapped[list] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )
    # Notification and privacy preference booleans
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    profile_public: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="preferences"
    )

    __table_args__ = (
        Index("ix_preferences_user_id", "user_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Preference user_id={self.user_id} style={self.travel_style!r}>"


# ---------------------------------------------------------------------------
# followers
# ---------------------------------------------------------------------------

class Follower(Base, TimestampMixin):
    """
    A directed follow relationship: follower_id follows following_id.

    Both IDs reference user_profiles.id within user_db.
    These are intra-service foreign keys — no cross-service constraint.

    A user cannot follow themselves (enforced by check constraint).
    A user cannot follow the same person twice (unique constraint on pair).
    Hard-deleted when unfollowed.
    """

    __tablename__ = "followers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    follower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    following_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    follower: Mapped["UserProfile"] = relationship(
        "UserProfile",
        foreign_keys=[follower_id],
        back_populates="following",
    )
    following: Mapped["UserProfile"] = relationship(
        "UserProfile",
        foreign_keys=[following_id],
        back_populates="followers",
    )

    __table_args__ = (
        UniqueConstraint(
            "follower_id", "following_id",
            name="uq_followers_follower_following",
        ),
        CheckConstraint(
            "follower_id != following_id",
            name="ck_followers_no_self_follow",
        ),
        Index("ix_followers_follower_id", "follower_id"),
        Index("ix_followers_following_id", "following_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Follower {self.follower_id} → {self.following_id}>"


# ---------------------------------------------------------------------------
# badges
# ---------------------------------------------------------------------------

class Badge(Base, TimestampMixin):
    """
    An awarded badge on a user profile.

    badge_name: e.g. "Trusted Traveler", "Explorer", "Community Builder"
    badge_icon: icon identifier or URL
    earned_at: when the badge was awarded

    Multiple badges per user. Hard-deleted if revoked.
    The award logic lives in the service layer (Checkpoint 5+).
    """

    __tablename__ = "badges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    badge_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    badge_icon: Mapped[str] = mapped_column(
        String(200),
        nullable=True,
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="badges"
    )

    __table_args__ = (
        # A user should not hold the same badge twice
        UniqueConstraint("user_id", "badge_name", name="uq_badges_user_badge"),
        Index("ix_badges_user_id", "user_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Badge user_id={self.user_id} name={self.badge_name!r}>"


# ---------------------------------------------------------------------------
# reputation
# ---------------------------------------------------------------------------

class Reputation(Base, TimestampMixin):
    """
    Single-row reputation record per user.

    Documentation specifies:
      Explorer Score, Trusted Traveler Score, Community Participation,
      Expeditions Joined, Expeditions Organized, Guide Interactions,
      Reviews Received.

    Mapped to integer score columns. Defaults to 0 on creation.
    Calculation logic lives in the service layer.

    Hard-deleted with the parent profile.
    """

    __tablename__ = "reputation"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # exactly one reputation row per user
    )
    explorer_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    community_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    review_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    expeditions_joined: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    expeditions_organized: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    guide_interactions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    reviews_received: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="reputation"
    )

    __table_args__ = (
        Index("ix_reputation_user_id", "user_id"),
        Index("ix_reputation_explorer_score", "explorer_score"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Reputation user_id={self.user_id} explorer={self.explorer_score}>"


# ---------------------------------------------------------------------------
# saved_items
# ---------------------------------------------------------------------------

class SavedItem(Base, TimestampMixin):
    """
    Cross-service saved entity reference.

    Stores application-level references to entities owned by other services.
    No PostgreSQL FK constraints into other service databases.

    entity_type: discriminator — one of STORY, COMMUNITY, EXPEDITION, GUIDE
    entity_id: UUID of the entity in the owning service's database

    The entity_type + entity_id pattern is consistent with the platform-wide
    convention used in recommendation_history (03-microservices.md Part 7).

    A user cannot save the same entity twice (unique on user_id + entity_type
    + entity_id).

    Hard-deleted when unsaved.
    """

    __tablename__ = "saved_items"

    VALID_ENTITY_TYPES = ("STORY", "COMMUNITY", "EXPEDITION", "GUIDE")

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    # UUID of the entity in its owning service's database — application-level ref only
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="saved_items"
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "entity_type", "entity_id",
            name="uq_saved_items_user_entity",
        ),
        CheckConstraint(
            "entity_type IN ('STORY', 'COMMUNITY', 'EXPEDITION', 'GUIDE')",
            name="ck_saved_items_entity_type",
        ),
        Index("ix_saved_items_user_id", "user_id"),
        Index("ix_saved_items_entity_type", "entity_type"),
        Index("ix_saved_items_user_entity_type", "user_id", "entity_type"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SavedItem user_id={self.user_id} type={self.entity_type} id={self.entity_id}>"
