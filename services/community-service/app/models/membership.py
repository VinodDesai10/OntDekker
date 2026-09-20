"""
Community Service — Membership Models
Owns: community_members, join_requests tables in community_db.

Design rules:
- user_id is a plain UUID (NOT a database FK) — references user_db.
- community_id IS a real FK within community_db → communities.id.
- A user can be a member of a community exactly once (unique constraint).
- Banned members have role=BANNED and status=BANNED.
- Join requests are created for private communities or communities requiring approval.
"""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    UUID,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base, TimestampMixin, AuditMixin
from shared.constants.status import MemberRole, MembershipStatus, JoinRequestStatus

if TYPE_CHECKING:
    from app.models.community import Community


class CommunityMember(AuditMixin, Base):
    """
    Records a user's membership in a community.
    A user can be a member of a given community exactly once.
    Role determines permissions within the community.
    """

    __tablename__ = "community_members"

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

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MemberRole.MEMBER,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MembershipStatus.ACTIVE,
        index=True,
    )

    community: Mapped["Community"] = relationship("Community", back_populates="members")

    __table_args__ = (
        UniqueConstraint("community_id", "user_id", name="uq_community_member"),
        Index("ix_community_members_user_id", "user_id"),
        Index("ix_community_members_community_status", "community_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<CommunityMember community={self.community_id} user={self.user_id} role={self.role}>"


class JoinRequest(AuditMixin, Base):
    """
    Records a user's request to join a private or approval-required community.
    After approval/rejection the record is kept for audit purposes.
    """

    __tablename__ = "join_requests"

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

    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=JoinRequestStatus.PENDING,
        index=True,
    )

    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    community: Mapped["Community"] = relationship("Community", back_populates="join_requests")

    __table_args__ = (
        Index("ix_join_requests_community_status", "community_id", "status"),
        Index("ix_join_requests_requester_id", "requester_id"),
    )

    def __repr__(self) -> str:
        return f"<JoinRequest community={self.community_id} requester={self.requester_id} status={self.status}>"
