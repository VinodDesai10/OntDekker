from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid

class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    event_version: int = 1
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: Optional[str] = None
    producer: str
    payload: Dict[str, Any]

class UserRegisteredPayload(BaseModel):
    user_id: str
    email: str
    created_at: str

class StoryCreatedPayload(BaseModel):
    story_id: str
    author_id: str
    community_id: str
    title: str

class CommunityJoinedPayload(BaseModel):
    community_id: str
    user_id: str
    joined_at: str

class ExpeditionCompletedPayload(BaseModel):
    expedition_id: str
    organizer_id: str
    completed_at: str
