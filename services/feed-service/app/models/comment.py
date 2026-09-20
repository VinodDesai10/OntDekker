"""
Feed Service — Comment Model
Owns: comments table in feed_db.

Design rules:
- author_id is a plain UUID (NOT a database FK) — references user_db.
- post_id IS a real FK within feed_db → posts.id.
- parent_comment_id is a real FK for nested comments (one level only).
- Soft-delete via SoftDeleteMixin to preserve comment threads.
"""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    UUID,
    ForeignKey,
    Index,
    String,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.post import Post


class Comment(TimestampMixin, SoftDeleteMixin, Base):
    """
    User comments on travel posts.
    Supports one level of nesting (replies to comments).
    """

    __tablename__ = "comments"

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

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    parent_comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    post: Mapped["Post"] = relationship(
        "Post",
        foreign_keys=[post_id],
    )
    parent_comment: Mapped[Optional["Comment"]] = relationship(
        "Comment",
        remote_side="Comment.id",
        foreign_keys=[parent_comment_id],
        back_populates="replies",
    )
    replies: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="parent_comment",
        cascade="all, delete-orphan",
        foreign_keys=[parent_comment_id],
    )

    __table_args__ = (
        Index("ix_comments_post_created", "post_id", "created_at"),
        Index("ix_comments_parent_id", "parent_comment_id"),
        Index("ix_comments_author_id", "author_id"),
        CheckConstraint("LENGTH(TRIM(content)) > 0", name="ck_comment_content_not_empty"),
    )

    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Comment id={self.id} post_id={self.post_id} content={content_preview!r}>"
