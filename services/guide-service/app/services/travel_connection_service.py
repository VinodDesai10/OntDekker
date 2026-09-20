"""
TravelConnectionService — business logic for guide–traveler connections.

TravelConnections track the relationship history between a traveler and a
guide: expeditions taken together, conversations, photos shared, and whether
the traveler has bookmarked the guide for future reference.

Connection lifecycle:
  - Connections are created automatically when a traveler and guide have
    an expedition together (Phase 1: manual event; Phase 2: Kafka event).
  - The service provides a method to record a new connection or
    increment counters on an existing one.
  - Travelers may bookmark guides they want to reconnect with.
  - Both the traveler (My Guides view) and the guide (who travelled with me)
    can view the list of connections.

Rules:
  - A guide cannot be in a connection with themselves
    (enforced at schema + service + DB CHECK).
  - Only the traveler may toggle their own bookmark.
  - Counter increments are idempotent-safe: get-or-create before incrementing.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from shared import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from shared.logging import setup_logging

from app.repositories.guide_profile_repository import GuideProfileRepository
from app.repositories.travel_connection_repository import TravelConnectionRepository
from app.schemas.common import PaginationMeta
from app.schemas.travel_connection import (
    TravelConnectionListResponse,
    TravelConnectionResponse,
)

logger = setup_logging(service_name="guide-service", log_level="INFO")


class TravelConnectionService:
    """Coordinates business logic for guide–traveler connection management."""

    def __init__(
        self,
        profile_repo: GuideProfileRepository,
        connection_repo: TravelConnectionRepository,
    ) -> None:
        self._profile_repo = profile_repo
        self._connection_repo = connection_repo

    # ------------------------------------------------------------------
    # PRIVATE HELPER
    # ------------------------------------------------------------------

    async def _require_guide_exists(self, guide_id: UUID) -> None:
        """Raise 404 if the guide profile does not exist."""
        profile = await self._profile_repo.get_by_id(guide_id)
        if not profile:
            raise NotFoundException(
                f"Guide profile {guide_id} not found.",
                error_code="GUIDE_PROFILE_NOT_FOUND",
            )

    async def _get_or_create_connection(
        self,
        guide_id: UUID,
        traveler_id: UUID,
        first_met: Optional[datetime] = None,
    ) -> TravelConnectionResponse:
        """Return existing connection or create a new one."""
        connection = await self._connection_repo.get_by_guide_and_traveler(
            guide_id, traveler_id
        )
        if connection is None:
            connection = await self._connection_repo.create(
                guide_id=guide_id,
                traveler_id=traveler_id,
                first_met=first_met or datetime.now(timezone.utc),
            )
        return TravelConnectionResponse.model_validate(connection)

    # ------------------------------------------------------------------
    # READ — traveler's My Guides list
    # ------------------------------------------------------------------

    async def list_my_connections(
        self,
        traveler_id: UUID,
        bookmarked_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> TravelConnectionListResponse:
        """Return a paginated list of guide connections for the current traveler."""
        connections, total = await self._connection_repo.list_by_traveler(
            traveler_id,
            bookmarked_only=bookmarked_only,
            page=page,
            page_size=page_size,
        )
        total_pages = max(1, math.ceil(total / page_size))
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
        return TravelConnectionListResponse(
            traveler_id=traveler_id,
            connections=[TravelConnectionResponse.model_validate(c) for c in connections],
            pagination=pagination,
        )

    async def list_guide_connections(
        self,
        guide_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> TravelConnectionListResponse:
        """Return a paginated list of traveler connections for a guide profile.

        Visible to the guide owner only (enforced at the router layer).
        """
        await self._require_guide_exists(guide_id)

        connections, total = await self._connection_repo.list_by_guide(
            guide_id,
            page=page,
            page_size=page_size,
        )
        total_pages = max(1, math.ceil(total / page_size))
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
        # Use the guide_id as the list "owner" identifier for consistency
        return TravelConnectionListResponse(
            traveler_id=guide_id,  # re-used field for the list envelope
            connections=[TravelConnectionResponse.model_validate(c) for c in connections],
            pagination=pagination,
        )

    # ------------------------------------------------------------------
    # RECORD — create connection or increment expedition counter
    # ------------------------------------------------------------------

    async def record_expedition_together(
        self,
        guide_id: UUID,
        traveler_id: UUID,
        expedition_date: Optional[datetime] = None,
    ) -> TravelConnectionResponse:
        """Record an expedition between a guide and traveler.

        If no connection exists, creates one with expeditions_together=1.
        If a connection exists, increments expeditions_together by 1.

        Raises 422 if guide_id == traveler_id.
        """
        await self._require_guide_exists(guide_id)

        if guide_id == traveler_id:
            raise ValidationException(
                "A guide cannot form a connection with themselves.",
                error_code="SELF_CONNECTION_NOT_ALLOWED",
            )

        connection = await self._connection_repo.get_by_guide_and_traveler(
            guide_id, traveler_id
        )

        if connection is None:
            # First shared expedition — create the connection record
            connection = await self._connection_repo.create(
                guide_id=guide_id,
                traveler_id=traveler_id,
                first_met=expedition_date or datetime.now(timezone.utc),
            )
            # Increment expedition count from 0 to 1
            updated = await self._connection_repo.increment_expedition_count(
                guide_id, traveler_id
            )
            if updated:
                return TravelConnectionResponse.model_validate(updated)
        else:
            updated = await self._connection_repo.increment_expedition_count(
                guide_id, traveler_id
            )
            if updated:
                return TravelConnectionResponse.model_validate(updated)

        return TravelConnectionResponse.model_validate(connection)

    # ------------------------------------------------------------------
    # BOOKMARK — toggle the bookmark flag
    # ------------------------------------------------------------------

    async def set_bookmark(
        self,
        guide_id: UUID,
        current_user_id: UUID,  # must be the traveler
        bookmarked: bool,
    ) -> TravelConnectionResponse:
        """Bookmark or un-bookmark a guide connection.

        The connection is created if it does not yet exist (a traveler
        can bookmark a guide without a shared expedition).

        Raises 404 if the guide profile does not exist.
        """
        await self._require_guide_exists(guide_id)

        if guide_id == current_user_id:
            raise ValidationException(
                "A guide cannot bookmark themselves.",
                error_code="SELF_CONNECTION_NOT_ALLOWED",
            )

        # Ensure connection exists before setting bookmark
        connection = await self._connection_repo.get_by_guide_and_traveler(
            guide_id, current_user_id
        )
        if connection is None:
            connection = await self._connection_repo.create(
                guide_id=guide_id,
                traveler_id=current_user_id,
            )

        updated = await self._connection_repo.set_bookmark(
            guide_id, current_user_id, bookmarked
        )
        if not updated:
            raise NotFoundException(
                "Travel connection not found.",
                error_code="CONNECTION_NOT_FOUND",
            )
        return TravelConnectionResponse.model_validate(updated)
