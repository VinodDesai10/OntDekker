# models package initialisation
#
# CRITICAL FOR ALEMBIC: every model module must be imported here.
#
# When alembic/env.py runs `from shared import Base` and then reads
# `Base.metadata`, SQLAlchemy only knows about tables whose ORM classes
# have been imported into the Python process. Importing them here ensures
# that simply doing `from app.models import *` or importing this package
# is sufficient for Alembic autogenerate to detect every table in trip_db.
#
# Import order follows the dependency graph (parent before children):
#   Expedition → everything else

from app.models.expedition import Expedition, ExpeditionStatus, ExpeditionVisibility
from app.models.participant import ExpeditionParticipant, ParticipantRole, ParticipantStatus
from app.models.join_request import ExpeditionJoinRequest, JoinRequestStatus
from app.models.itinerary import ExpeditionItinerary
from app.models.gallery import ExpeditionGallery
from app.models.gear_item import GearItem, GearCategory
from app.models.review import ExpeditionReview
from app.models.discussion import ExpeditionDiscussionMessage

__all__ = [
    # Core aggregate
    "Expedition",
    "ExpeditionStatus",
    "ExpeditionVisibility",

    # Participants
    "ExpeditionParticipant",
    "ParticipantRole",
    "ParticipantStatus",

    # Join requests
    "ExpeditionJoinRequest",
    "JoinRequestStatus",

    # Itinerary
    "ExpeditionItinerary",

    # Gallery
    "ExpeditionGallery",

    # Gear / Pack Weight Optimizer
    "GearItem",
    "GearCategory",

    # Post-expedition reviews
    "ExpeditionReview",

    # Discussion
    "ExpeditionDiscussionMessage",
]
