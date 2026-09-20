"""
Feed Service — Interaction Models
Owns: likes, bookmarks, shares tables in feed_db.

Design rules:
- user_id is a plain UUID (NOT a database FK) — references user_db.
- post_id IS a real FK within feed_db → posts.id.
- Likes and Bookmarks are idempotent per user per post (unique constraint).
- Shares are NOT idempotent — each share is a separate event record.
- Bookmarks are private to the user — never exposed in public post responses.
"""

import uuid
from typing import Optional

from sqlalchemy import (
    UUID,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base, TimestampMixin


class Like(TimestampMixin, Base):
    """
    Records a user liking a post.
    A user can like a given post exactly once (unique constraint enforced).
    """

    __tablename__ = "likes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_like_post_user"),
        Index("ix_likes_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Like post_id={self.post_id} user_id={self.user_id}>"


class Bookmark(TimestampMixin, Base):
    """
    Records a user bookmarking (saving) a post.
    Bookmarks are private — only the owning user can see their own bookmarks.
    A user can bookmark a given post exactly once (unique constraint enforced).
    """

    __tablename__ = "bookmarks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_bookmark_post_user"),
        Index("ix_bookmarks_user_id", "user_id"),
        Index("ix_bookmarks_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Bookmark post_id={self.post_id} user_id={self.user_id}>"


class Share(TimestampMixin, Base):
    """
    Records a user sharing a post.
    Shares are NOT idempotent — a user may share the same post multiple times.
    Each share is a distinct event (useful for analytics and share-count tracking).
    """

    __tablename__ = "shares"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    share_channel: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_shares_post_id", "post_id"),
        Index("ix_shares_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Share post_id={self.post_id} user_id={self.user_id}>"
