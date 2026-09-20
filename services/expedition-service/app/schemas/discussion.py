"""
Discussion Pydantic schemas — /api/v1/trips/{trip_id}/discussion endpoints.

Schema hierarchy:
  DiscussionMessageCreate  — POST /api/v1/trips/{trip_id}/discussion (request body)
  DiscussionMessageResponse — single message (used in both GET and POST responses)
  DiscussionListResponse   — paginated list of messages

Identity convention:
  - author_id is NEVER accepted from the client.  The service layer always
    derives author_id from the JWT sub claim.
  - The response includes author_id so the frontend can resolve display
    name / avatar via the user-service batchProfilesByAuth() flow later.

Serialisation:
  - All response schemas use alias_generator=to_camel so the JSON keys
    match the existing camelCase TypeScript interfaces.
"""

from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.schemas.common import PaginationMeta

# Application-level content length limit
DISCUSSION_CONTENT_MAX_LENGTH: int = 2000


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class DiscussionMessageCreate(BaseModel):
    """Body for POST /api/v1/trips/{trip_id}/discussion.

    author_id is intentionally absent — the server always derives it
    from the JWT sub claim.  Including it in the request body would be
    ignored (and would be a security risk).
    """

    content: str = Field(
        ...,
        min_length=1,
        max_length=DISCUSSION_CONTENT_MAX_LENGTH,
        description=(
            "Message text. Must be non-empty. "
            f"Maximum {DISCUSSION_CONTENT_MAX_LENGTH} characters."
        ),
    )

    @field_validator("content")
    @classmethod
    def content_not_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be blank or whitespace only.")
        return v


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class DiscussionMessageResponse(BaseModel):
    """Full message record.

    Returned by:
      GET  /api/v1/trips/{trip_id}/discussion  (within items list)
      POST /api/v1/trips/{trip_id}/discussion  (the newly created message)

    author_id is included so the frontend can call
    batchProfilesByAuth([authorId, ...]) to resolve display names / avatars.
    """

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    expedition_id: UUID      # → expeditionId in JSON
    author_id: UUID          # → authorId in JSON
    content: str
    created_at: datetime     # → createdAt in JSON
    updated_at: datetime     # → updatedAt in JSON


# ---------------------------------------------------------------------------
# Paginated list response
# ---------------------------------------------------------------------------

class DiscussionListResponse(BaseModel):
    """Paginated list of discussion messages.

    Returned by GET /api/v1/trips/{trip_id}/discussion.

    Follows the same PaginatedResponse[T] structure used throughout the
    expedition-service, but typed concretely to avoid an extra generic
    nesting layer in the OpenAPI schema.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    items: List[DiscussionMessageResponse] = Field(
        default_factory=list,
        description="Page of discussion messages, oldest first.",
    )
    pagination: PaginationMeta = Field(
        ...,
        description="Pagination metadata.",
    )
