"""
Feed Service — Post Models
Owns: posts, post_media, post_tags tables in feed_db.

Design rules:
- author_id, community_id, expedition_id are plain UUIDs (NOT database FKs).
  They reference user_db, community_db, trip_db respectively.
  Referential integrity is enforced at the application/service layer only.
- Binary media is never stored here. post_media stores MinIO object URLs only.
- Soft-delete via SoftDeleteMixin (is_deleted, deleted_at, deleted_by).
"""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    UUID,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import AuditMixin, Base, SoftDeleteMixin
from shared.constants.status import MediaType, PostStatus, PostVisibility

if TYPE_CHECKING:
    from app.models.comment import Comment


class Post(AuditMixin, SoftDeleteMixin, Base):
    """
    Core travel post entity.
    Represents a user's travel story shared on the platform.
    """

    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    community_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    expedition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PostStatus.PUBLISHED,
        index=True,
    )
    visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PostVisibility.PUBLIC,
        index=True,
    )

    media: Mapped[list["PostMedia"]] = relationship(
        "PostMedia",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostMedia.display_order",
        lazy="selectin",
    )
    tags: Mapped[list["PostTag"]] = relationship(
        "PostTag",
        back_populates="post",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        foreign_keys="Comment.post_id",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_posts_author_created", "author_id", "created_at"),
        Index("ix_posts_community_created", "community_id", "created_at"),
        Index("ix_posts_status_visibility", "status", "visibility"),
    )

    def __repr__(self) -> str:
        return f"<Post id={self.id} title={self.title!r} author={self.author_id}>"


class PostMedia(AuditMixin, Base):
    """
    Media metadata for a post.
    Binary files are stored in MinIO (bucket: posts).
    Only the MinIO object URL is persisted here.
    """

    __tablename__ = "post_media"

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

    media_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)

    media_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MediaType.IMAGE,
    )

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alt_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    post: Mapped["Post"] = relationship("Post", back_populates="media")

    __table_args__ = (
        Index("ix_post_media_post_order", "post_id", "display_order"),
    )

    def __repr__(self) -> str:
        return f"<PostMedia id={self.id} post_id={self.post_id} order={self.display_order}>"


class PostTag(Base):
    """
    Travel tags attached to a post.
    Examples: 'Hiking', 'Camping', 'Wildlife', 'Culture', 'Photography'.
    """

    __tablename__ = "post_tags"

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

    tag: Mapped[str] = mapped_column(String(50), nullable=False)

    post: Mapped["Post"] = relationship("Post", back_populates="tags")

    __table_args__ = (
        UniqueConstraint("post_id", "tag", name="uq_post_tag"),
        Index("ix_post_tags_tag", "tag"),
    )

    def __repr__(self) -> str:
        return f"<PostTag post_id={self.post_id} tag={self.tag!r}>"
