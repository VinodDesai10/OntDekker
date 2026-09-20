from shared.exceptions import (
    OntDekkerException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ConflictException,
    ValidationException,
    DatabaseException,
    # Short-form aliases
    NotFoundError,
    ForbiddenError,
    ValidationError,
    ConflictError,
    UnauthorizedError,
    register_exception_handlers
)
from shared.logging import setup_logging, request_id_ctx, correlation_id_ctx
from shared.database import Base, TimestampMixin, SoftDeleteMixin, AuditMixin
from shared.config import get_common_settings, CommonSettings
from shared.dependencies import get_db, get_request_id, get_current_user, optional_current_user, require_role

__all__ = [
    # Exceptions
    "OntDekkerException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "ConflictException",
    "ValidationException",
    "DatabaseException",
    # Short-form aliases
    "NotFoundError",
    "ForbiddenError",
    "ValidationError",
    "ConflictError",
    "UnauthorizedError",
    "register_exception_handlers",
    
    # Logging
    "setup_logging",
    "request_id_ctx",
    "correlation_id_ctx",
    
    # Database
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    
    # Config
    "get_common_settings",
    "CommonSettings",
    
    # Dependencies
    "get_db",
    "get_request_id",
    "get_current_user",
    "optional_current_user",
    "require_role",
]
