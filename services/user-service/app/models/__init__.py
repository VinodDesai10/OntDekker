# User Service — Models Package
#
# Importing all models here ensures SQLAlchemy's Base.metadata is populated
# with every table definition when this package is imported.
# Alembic's env.py imports this package to trigger model registration
# before autogenerate compares metadata against the live schema.

from app.models.profile import (
    UserProfile,
    Interest,
    Preference,
    Follower,
    Badge,
    Reputation,
    SavedItem,
)

__all__ = [
    "UserProfile",
    "Interest",
    "Preference",
    "Follower",
    "Badge",
    "Reputation",
    "SavedItem",
]
