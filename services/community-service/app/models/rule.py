"""
Community Service — Rule Model
Owns: community_rules table in community_db.

Design rules:
- community_id IS a real FK within community_db → communities.id.
- Rules are ordered by order_index (ascending).
- Only owners and moderators can create/modify/delete rules.
"""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    UUID,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base, AuditMixin

if TYPE_CHECKING:
    from app.models.community import Community


class CommunityRule(AuditMixin, Base):
    """
    A rule for a community.
    Communities can have multiple ordered rules visible to all members.
    """

    __tablename__ = "community_rules"

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

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    community: Mapped["Community"] = relationship("Community", back_populates="rules")

    __table_args__ = (
        Index("ix_community_rules_community_order", "community_id", "order_index"),
    )

    def __repr__(self) -> str:
        return f"<CommunityRule community={self.community_id} title={self.title!r} order={self.order_index}>"
