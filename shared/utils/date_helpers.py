from datetime import datetime, timezone
from typing import Union

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def format_iso(dt: datetime) -> str:
    return dt.isoformat()

def parse_iso(s: str) -> datetime:
    # Handles ISO parsing with timezone awareness
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
