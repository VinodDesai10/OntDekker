"""
GuideApplicationService — business logic for the guide application workflow.

State machine:
  DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED (creates GuideProfile)
                                   → REJECTED

Rules:
  - A user may only have one application record at a time.
    On APPROVED or REJECTED, a user may re-apply only after rejection,
    enforced by the service layer (the DB has a unique constraint on user_id).
  - On APPROVED: a GuideProfile is automatically created for the applicant.
  - Only the applicant may view and edit their own application.
  - Only admins may move an application to UNDER_REVIEW, APPROVED, or REJECTED.
  - Editing is only allowed while status is DRAFT.
  - Submission changes status from DRAFT to SUBMITTED.
"""

from __future__ import annotations

from uuid import UUID

from shared import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from shared.logging import setup_logging

from app.models.guide_application import ApplicationStatus
from app.repositories.guide_application_repository import GuideApplicationRepository
from app.repositories.guide_profile_repository import GuideProfileRepository
from app.schemas.guide_application import (
    GuideApplicationCreate,
    GuideApplicationResponse,
    GuideApplicationUpdate,
)

logger = setup_logging(service_name="guide-service", log_level="INFO")

# Valid application status transitions
_VALID_APP_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.DRAFT:        {ApplicationStatus.SUBMITTED},
    ApplicationStatus.SUBMITTED:    {ApplicationStatus.UNDER_REVIEW, ApplicationStatus.REJECTED},
    ApplicationStatus.UNDER_REVIEW: {ApplicationStatus.APPROVED, ApplicationStatus.REJECTED},
    ApplicationStatus.APPROVED:     set(),
    ApplicationStatus.REJECTED:     set(),
}


class GuideApplicationService:
    """Coordinates business logic for guide application lifecycle."""

    def __init__(
        self,
        application_repo: GuideApplicationRepository,
        profile_repo: GuideProfileRepository,
    ) -> None:
        self._application_repo = application_repo
        self._profile_repo = profile_repo

    # ------------------------------------------------------------------
    # CREATE — applicant starts a new application (DRAFT)
    # ------------------------------------------------------------------

    async def create_application(
        self,
        payload: GuideApplicationCreate,
        current_user_id: UUID,
    ) -> GuideApplicationResponse:
        """Create a new guide application in DRAFT status.

        Raises 409 if an application already exists for this user.
        Raises 409 if the user already has an active guide profile.
        """
        # Check for existing application
        existing = await self._application_repo.get_by_user_id(current_user_id)
        if existing is not None:
            raise ConflictException(
                "An application already exists for this user. "
                "Retrieve your existing application to continue.",
                error_code="APPLICATION_ALREADY_EXISTS",
            )

        # Check for existing guide profile
        if await self._profile_repo.exists_for_user(current_user_id):
            raise ConflictException(
                "A guide profile already exists for this user.",
                error_code="GUIDE_PROFILE_ALREADY_EXISTS",
            )

        application = await self._application_repo.create(
            user_id=current_user_id,
            biography=payload.biography,
            areas_covered=payload.areas_covered,
            languages=payload.languages,
            experience_years=payload.experience_years,
            certifications=payload.certifications,
            identity_document_url=payload.identity_document_url,
        )
        return GuideApplicationResponse.model_validate(application)

    # ------------------------------------------------------------------
    # READ — applicant views their own application
    # ------------------------------------------------------------------

    async def get_my_application(
        self,
        current_user_id: UUID,
    ) -> GuideApplicationResponse:
        """Fetch the current user's application. Raises 404 if none exists."""
        application = await self._application_repo.get_by_user_id(current_user_id)
        if not application:
            raise NotFoundException(
                "No guide application found for this user.",
                error_code="APPLICATION_NOT_FOUND",
            )
        return GuideApplicationResponse.model_validate(application)

    async def get_application_by_id(
        self,
        application_id: UUID,
        current_user_id: UUID,
    ) -> GuideApplicationResponse:
        """Fetch an application by ID. The caller must be the owner."""
        application = await self._application_repo.get_by_id(application_id)
        if not application:
            raise NotFoundException(
                f"Guide application {application_id} not found.",
                error_code="APPLICATION_NOT_FOUND",
            )
        if application.user_id != current_user_id:
            raise ForbiddenException(
                "You can only view your own application.",
                error_code="NOT_APPLICATION_OWNER",
            )
        return GuideApplicationResponse.model_validate(application)

    # ------------------------------------------------------------------
    # UPDATE — applicant edits their DRAFT application
    # ------------------------------------------------------------------

    async def update_application(
        self,
        application_id: UUID,
        payload: GuideApplicationUpdate,
        current_user_id: UUID,
    ) -> GuideApplicationResponse:
        """Update a DRAFT application. Only the owner may update.

        Raises 403 if caller is not the owner.
        Raises 422 if the application is not in DRAFT status.
        """
        application = await self._application_repo.get_by_id(application_id)
        if not application:
            raise NotFoundException(
                f"Guide application {application_id} not found.",
                error_code="APPLICATION_NOT_FOUND",
            )
        if application.user_id != current_user_id:
            raise ForbiddenException(
                "You can only edit your own application.",
                error_code="NOT_APPLICATION_OWNER",
            )
        if application.status != ApplicationStatus.DRAFT:
            raise ValidationException(
                f"Application cannot be edited in '{application.status}' status. "
                "Only DRAFT applications can be modified.",
                error_code="APPLICATION_NOT_EDITABLE",
            )

        update_data = payload.model_dump(exclude_none=True)
        updated = await self._application_repo.update(application_id, **update_data)
        if not updated:
            raise NotFoundException(
                f"Guide application {application_id} not found.",
                error_code="APPLICATION_NOT_FOUND",
            )
        return GuideApplicationResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # SUBMIT — applicant submits their DRAFT application
    # ------------------------------------------------------------------

    async def submit_application(
        self,
        application_id: UUID,
        current_user_id: UUID,
    ) -> GuideApplicationResponse:
        """Submit a DRAFT application for review.

        Transitions status: DRAFT → SUBMITTED.
        Only the owner may submit.
        """
        application = await self._application_repo.get_by_id(application_id)
        if not application:
            raise NotFoundException(
                f"Guide application {application_id} not found.",
                error_code="APPLICATION_NOT_FOUND",
            )
        if application.user_id != current_user_id:
            raise ForbiddenException(
                "You can only submit your own application.",
                error_code="NOT_APPLICATION_OWNER",
            )
        if application.status != ApplicationStatus.DRAFT:
            raise ValidationException(
                f"Only DRAFT applications can be submitted. "
                f"Current status: '{application.status}'.",
                error_code="INVALID_STATUS_TRANSITION",
            )

        updated = await self._application_repo.update_status(
            application_id,
            ApplicationStatus.SUBMITTED,
        )
        return GuideApplicationResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # ADMIN — review workflow transitions
    # ------------------------------------------------------------------

    async def admin_transition_status(
        self,
        application_id: UUID,
        new_status: ApplicationStatus,
        admin_user_id: UUID,
        review_notes: str | None = None,
    ) -> GuideApplicationResponse:
        """Admin-only: transition an application to UNDER_REVIEW, APPROVED, or REJECTED.

        On APPROVED, automatically creates a GuideProfile for the applicant.
        The caller is responsible for verifying admin role before calling this.
        """
        application = await self._application_repo.get_by_id(application_id)
        if not application:
            raise NotFoundException(
                f"Guide application {application_id} not found.",
                error_code="APPLICATION_NOT_FOUND",
            )

        allowed = _VALID_APP_TRANSITIONS.get(application.status, set())
        if new_status not in allowed:
            raise ValidationException(
                f"Cannot transition from '{application.status}' to '{new_status}'.",
                error_code="INVALID_STATUS_TRANSITION",
            )

        updated = await self._application_repo.update_status(
            application_id,
            new_status,
            reviewed_by=admin_user_id,
            review_notes=review_notes,
        )

        # On APPROVED: create a GuideProfile for the applicant
        if new_status == ApplicationStatus.APPROVED:
            if not await self._profile_repo.exists_for_user(application.user_id):
                await self._profile_repo.create(
                    user_id=application.user_id,
                    bio=application.biography,
                    created_by=admin_user_id,
                )
                logger.info(
                    "GuideProfile created for user %s after application %s approved.",
                    application.user_id,
                    application_id,
                )

        return GuideApplicationResponse.model_validate(updated)
