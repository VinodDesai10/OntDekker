"""
JoinRequestRepository — persistence layer for ExpeditionJoinRequest.

Responsibilities:
  - Create a new join request
  - Fetch by expedition + user (duplicate detection)
  - Fetch pending requests for organiser inbox
  - Update status (approve / reject / cancel)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.join_request import ExpeditionJoinRequest, JoinRequestStatus


class JoinRequestRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        expedition_id: UUID,
        user_id: UUID,
        message: Optional[str] = None,
    ) -> ExpeditionJoinRequest:
        """Create a new PENDING join request."""
        request = ExpeditionJoinRequest(
            id=uuid.uuid4(),
            expedition_id=expedition_id,
            user_id=user_id,
            message=message,
            status=JoinRequestStatus.PENDING,
        )
        self._session.add(request)
        await self._session.flush()
        await self._session.refresh(request)
        return request

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_id(
        self, request_id: UUID
    ) -> Optional[ExpeditionJoinRequest]:
        """Fetch a join request by its own PK."""
        stmt = select(ExpeditionJoinRequest).where(
            ExpeditionJoinRequest.id == request_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_expedition_and_user(
        self,
        expedition_id: UUID,
        user_id: UUID,
    ) -> Optional[ExpeditionJoinRequest]:
        """Fetch the join request row for a specific user in a specific expedition.

        Used to detect duplicate requests before creation, and to find
        the request when a user wants to cancel it.
        """
        stmt = (
            select(ExpeditionJoinRequest)
            .where(ExpeditionJoinRequest.expedition_id == expedition_id)
            .where(ExpeditionJoinRequest.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_expedition(
        self,
        expedition_id: UUID,
        *,
        status: Optional[JoinRequestStatus] = None,
    ) -> Sequence[ExpeditionJoinRequest]:
        """Return join requests for an expedition (organiser inbox).

        Defaults to all statuses. Pass status=PENDING for the inbox view.
        """
        stmt = (
            select(ExpeditionJoinRequest)
            .where(ExpeditionJoinRequest.expedition_id == expedition_id)
        )
        if status is not None:
            stmt = stmt.where(ExpeditionJoinRequest.status == status)
        stmt = stmt.order_by(ExpeditionJoinRequest.created_at.asc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_by_user(
        self,
        user_id: UUID,
    ) -> Sequence[ExpeditionJoinRequest]:
        """Return all join requests submitted by a user."""
        stmt = (
            select(ExpeditionJoinRequest)
            .where(ExpeditionJoinRequest.user_id == user_id)
            .order_by(ExpeditionJoinRequest.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def has_pending_request(
        self, expedition_id: UUID, user_id: UUID
    ) -> bool:
        """Return True if the user has an existing PENDING request."""
        stmt = (
            select(func.count())
            .select_from(ExpeditionJoinRequest)
            .where(ExpeditionJoinRequest.expedition_id == expedition_id)
            .where(ExpeditionJoinRequest.user_id == user_id)
            .where(ExpeditionJoinRequest.status == JoinRequestStatus.PENDING)
        )
        return (await self._session.execute(stmt)).scalar_one() > 0

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    async def update_status(
        self,
        request_id: UUID,
        status: JoinRequestStatus,
        *,
        reviewed_by: Optional[UUID] = None,
        rejection_reason: Optional[str] = None,
    ) -> Optional[ExpeditionJoinRequest]:
        """Update the status of a join request.

        Sets reviewed_by and rejection_reason when status is
        APPROVED or REJECTED.
        """
        values: dict = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if reviewed_by is not None:
            values["reviewed_by"] = reviewed_by
        if rejection_reason is not None:
            values["rejection_reason"] = rejection_reason

        stmt = (
            update(ExpeditionJoinRequest)
            .where(ExpeditionJoinRequest.id == request_id)
            .values(**values)
            .returning(ExpeditionJoinRequest)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
