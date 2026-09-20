# models package initialisation
#
# CRITICAL FOR ALEMBIC: every model module must be imported here.
#
# When alembic/env.py runs `import app.models` and then reads
# Base.metadata, SQLAlchemy only knows about tables whose ORM classes
# have been imported into the Python process. Importing them here
# ensures that a single `import app.models` is sufficient for Alembic
# to detect all 7 tables in guide_db.
#
# Import order follows the FK dependency graph:
#   GuideProfile (root) → all children

from app.models.guide_profile import GuideProfile, VerificationStatus
from app.models.guide_application import GuideApplication, ApplicationStatus
from app.models.guide_location import GuideLocation
from app.models.guide_language import GuideLanguage
from app.models.guide_availability import GuideAvailability, AvailabilityStatus
from app.models.guide_review import GuideReview
from app.models.travel_connection import TravelConnection
from app.models.guide_specialization import GuideSpecialization

__all__ = [
    # Root aggregate
    "GuideProfile",
    "VerificationStatus",

    # Application workflow
    "GuideApplication",
    "ApplicationStatus",

    # Profile children
    "GuideLocation",
    "GuideLanguage",
    "GuideSpecialization",

    # Availability
    "GuideAvailability",
    "AvailabilityStatus",

    # Reviews
    "GuideReview",

    # Travel connections
    "TravelConnection",
]
