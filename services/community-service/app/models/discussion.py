"""
Community Service — Discussion Models
Owns: discussions, discussion_comments tables in community_db.

Design rules:
- author_id is a plain UUID (NOT a database FK) — references user_db.
- community_id IS a real FK within community_db → communities.id.
- discussion_id IS a real FK within community_db → discussions.id.
- Soft-delete on both discussions and comments to preserve threads.
- Comments are flat (no nesting — unlike feed comments which have replies).
"""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    UUID,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base, AuditMixin, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.community import Community


class Discussion(AuditMixin, SoftDeleteMixin, Base):
    """
    A discussion thread within a community.
    Members with appropriate permissions can create discussions.
    """

    __tablename__ = "discussions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    community: Mapped["Community"] = relationship("Community", back_populates="discussions")

    comments: Mapped[list["DiscussionComment"]] = relationship(
        "DiscussionComment",
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_discussions_community_created", "community_id", "created_at"),
        Index("ix_discussions_author_id", "author_id"),
    )

    def __repr__(self) -> str:
        return f"<Discussion id={self.id} community={self.community_id} title={self.title!r}>"


class DiscussionComment(TimestampMixin, SoftDeleteMixin, Base):
    """
    A comment on a discussion thread.
    Flat structure — no nesting.
    """

    __tablename__ = "discussion_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discussions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    discussion: Mapped["Discussion"] = relationship("Discussion", back_populates="comments")

    __table_args__ = (
        Index("ix_discussion_comments_discussion_created", "discussion_id", "created_at"),
        Index("ix_discussion_comments_author_id", "author_id"),
        CheckConstraint("LENGTH(TRIM(content)) > 0", name="ck_discussion_comment_not_empty"),
    )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<DiscussionComment id={self.id} discussion={self.discussion_id} content={preview!r}>"
