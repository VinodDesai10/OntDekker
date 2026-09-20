"""
ParticipantRepository — persistence layer for ExpeditionParticipant.

Responsibilities:
  - Add participants (used both for direct join and after approval)
  - Query participants by expedition
  - Query participations by user (My Trips)
  - Update participant role
  - Update participant status (left / removed)
  - Count active participants (for capacity checks)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.participant import (
    ExpeditionParticipant,
    ParticipantRole,
    ParticipantStatus,
)


class ParticipantRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def add(
        self,
        *,
        expedition_id: UUID,
        user_id: UUID,
        role: ParticipantRole = ParticipantRole.PARTICIPANT,
    ) -> ExpeditionParticipant:
        """Add a confirmed participant to an expedition.

        Called when:
          - Organiser creates the expedition (role=ORGANIZER)
          - A user joins a PUBLIC expedition directly (role=PARTICIPANT)
          - A join request is approved (role=PARTICIPANT)
        """
        now = datetime.now(timezone.utc)
        participant = ExpeditionParticipant(
            id=uuid.uuid4(),
            expedition_id=expedition_id,
            user_id=user_id,
            role=role,
            status=ParticipantStatus.ACTIVE,
            joined_at=now,
        )
        self._session.add(participant)
        await self._session.flush()
        await self._session.refresh(participant)
        return participant

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_by_id(self, participant_id: UUID) -> Optional[ExpeditionParticipant]:
        """Fetch a single participant row by its own PK."""
        stmt = select(ExpeditionParticipant).where(
            ExpeditionParticipant.id == participant_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_expedition_and_user(
        self,
        expedition_id: UUID,
        user_id: UUID,
    ) -> Optional[ExpeditionParticipant]:
        """Fetch the participant row for a specific user in a specific expedition.

        Used to check whether a user is already a participant before
        allowing a join action.
        """
        stmt = (
            select(ExpeditionParticipant)
            .where(ExpeditionParticipant.expedition_id == expedition_id)
            .where(ExpeditionParticipant.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_expedition(
        self,
        expedition_id: UUID,
        *,
        active_only: bool = True,
    ) -> Sequence[ExpeditionParticipant]:
        """Return all participants for an expedition.

        active_only=True (default) returns only ACTIVE participants.
        active_only=False includes LEFT and REMOVED rows (for history).
        """
        stmt = (
            select(ExpeditionParticipant)
            .where(ExpeditionParticipant.expedition_id == expedition_id)
        )
        if active_only:
            stmt = stmt.where(
                ExpeditionParticipant.status == ParticipantStatus.ACTIVE
            )
        stmt = stmt.order_by(ExpeditionParticipant.joined_at.asc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        active_only: bool = True,
    ) -> Sequence[ExpeditionParticipant]:
        """Return all participation rows for a user (My Trips).

        Used to build the My Trips page by finding all expedition_ids
        the user is participating in, then fetching expedition details.
        """
        stmt = (
            select(ExpeditionParticipant)
            .where(ExpeditionParticipant.user_id == user_id)
        )
        if active_only:
            stmt = stmt.where(
                ExpeditionParticipant.status == ParticipantStatus.ACTIVE
            )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_active(self, expedition_id: UUID) -> int:
        """Count active participants for an expedition.

        Used by the service layer to enforce max_participants capacity
        before allowing a new participant to join.
        """
        stmt = (
            select(func.count())
            .select_from(ExpeditionParticipant)
            .where(ExpeditionParticipant.expedition_id == expedition_id)
            .where(ExpeditionParticipant.status == ParticipantStatus.ACTIVE)
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def is_participant(self, expedition_id: UUID, user_id: UUID) -> bool:
        """Return True if the user is an ACTIVE participant."""
        stmt = (
            select(func.count())
            .select_from(ExpeditionParticipant)
            .where(ExpeditionParticipant.expedition_id == expedition_id)
            .where(ExpeditionParticipant.user_id == user_id)
            .where(ExpeditionParticipant.status == ParticipantStatus.ACTIVE)
        )
        return (await self._session.execute(stmt)).scalar_one() > 0

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    async def update_role(
        self,
        expedition_id: UUID,
        user_id: UUID,
        role: ParticipantRole,
    ) -> Optional[ExpeditionParticipant]:
        """Update the role of a participant."""
        stmt = (
            update(ExpeditionParticipant)
            .where(ExpeditionParticipant.expedition_id == expedition_id)
            .where(ExpeditionParticipant.user_id == user_id)
            .where(ExpeditionParticipant.status == ParticipantStatus.ACTIVE)
            .values(
                role=role,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(ExpeditionParticipant)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        expedition_id: UUID,
        user_id: UUID,
        status: ParticipantStatus,
    ) -> Optional[ExpeditionParticipant]:
        """Update the status of a participant (LEFT or REMOVED)."""
        stmt = (
            update(ExpeditionParticipant)
            .where(ExpeditionParticipant.expedition_id == expedition_id)
            .where(ExpeditionParticipant.user_id == user_id)
            .values(
                status=status,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(ExpeditionParticipant)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
