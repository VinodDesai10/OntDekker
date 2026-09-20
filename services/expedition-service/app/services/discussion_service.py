"""
DiscussionService — business logic for expedition discussion messages.

Authorization rules (STEP 5):
  - GET: requires authentication; expedition must exist.
    (Consistent with how the workspace requires auth to see trip details.)
  - POST: requires the caller to be an ACTIVE participant or organizer of
    the expedition.  Non-members receive ForbiddenException.

Identity rule:
  - author_id is ALWAYS derived from the JWT sub (current_user_id parameter).
    It is never accepted from the request body.

Validation rules:
  - content must be non-empty after stripping (enforced in schema + here).
  - content must not exceed DISCUSSION_CONTENT_MAX_LENGTH characters.

Ordering:
  - Messages are always returned oldest → newest (ascending created_at).
"""

from __future__ import annotations

import math
from uuid import UUID

from shared import ForbiddenException, NotFoundException, ValidationException

from app.models.participant import ParticipantStatus
from app.repositories.discussion_repository import DiscussionRepository
from app.repositories.expedition_repository import ExpeditionRepository
from app.repositories.participant_repository import ParticipantRepository
from app.schemas.common import PaginationMeta
from app.schemas.discussion import (
    DISCUSSION_CONTENT_MAX_LENGTH,
    DiscussionListResponse,
    DiscussionMessageCreate,
    DiscussionMessageResponse,
)

# Default page size for discussion list (same ballpark as other endpoints)
_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 100


class DiscussionService:

    def __init__(
        self,
        expedition_repo: ExpeditionRepository,
        discussion_repo: DiscussionRepository,
        participant_repo: ParticipantRepository,
    ) -> None:
        self._expedition_repo = expedition_repo
        self._discussion_repo = discussion_repo
        self._participant_repo = participant_repo

    # ------------------------------------------------------------------
    # GET — list messages (paginated, oldest → newest)
    # ------------------------------------------------------------------

    async def list_messages(
        self,
        trip_id: UUID,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_PAGE_SIZE,
    ) -> DiscussionListResponse:
        """Return a paginated list of discussion messages for a trip.

        Raises NotFoundException if the expedition/trip does not exist.
        The caller must be authenticated (enforced at the router via
        Depends(get_current_user)), but no membership check is required
        for reading — consistent with how trip details are viewable
        by all authenticated users.
        """
        await self._require_expedition(trip_id)

        # Clamp page_size to [1, _MAX_PAGE_SIZE]
        page_size = max(1, min(page_size, _MAX_PAGE_SIZE))
        page = max(1, page)

        total = await self._discussion_repo.count_by_expedition(trip_id)
        messages = await self._discussion_repo.list_by_expedition(
            trip_id, page=page, page_size=page_size
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return DiscussionListResponse(
            items=[DiscussionMessageResponse.model_validate(m) for m in messages],
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
        )

    # ------------------------------------------------------------------
    # POST — create a new message
    # ------------------------------------------------------------------

    async def create_message(
        self,
        trip_id: UUID,
        payload: DiscussionMessageCreate,
        current_user_id: UUID,
    ) -> DiscussionMessageResponse:
        """Post a new discussion message.

        Authorization:
          - The expedition must exist (NotFoundException).
          - The caller must be an ACTIVE participant or organizer
            (ForbiddenException if not).

        author_id is always current_user_id (JWT sub).
        The payload's content has already been validated by the schema
        (non-empty, within max length); the service adds a defensive
        recheck for belt-and-suspenders safety.

        Returns the created message.
        """
        # 1. Verify expedition exists
        await self._require_expedition(trip_id)

        # 2. Authorization — active membership required
        is_member = await self._participant_repo.is_participant(trip_id, current_user_id)
        if not is_member:
            raise ForbiddenException(
                "You must be an active participant or organizer of this expedition "
                "to post in the discussion.",
                error_code="NOT_EXPEDITION_MEMBER",
            )

        # 3. Belt-and-suspenders content validation
        content = payload.content.strip()
        if not content:
            raise ValidationException(
                "Discussion message content must not be empty.",
                error_code="CONTENT_EMPTY",
            )
        if len(content) > DISCUSSION_CONTENT_MAX_LENGTH:
            raise ValidationException(
                f"Discussion message content must not exceed "
                f"{DISCUSSION_CONTENT_MAX_LENGTH} characters.",
                error_code="CONTENT_TOO_LONG",
            )

        # 4. Persist — author_id is always from JWT, never from request body
        message = await self._discussion_repo.create(
            expedition_id=trip_id,
            author_id=current_user_id,
            content=content,
        )

        return DiscussionMessageResponse.model_validate(message)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _require_expedition(self, trip_id: UUID):
        """Raise NotFoundException if the expedition does not exist."""
        expedition = await self._expedition_repo.get_by_id(trip_id)
        if not expedition:
            raise NotFoundException(
                f"Trip {trip_id} not found.",
                error_code="TRIP_NOT_FOUND",
            )
        return expedition
