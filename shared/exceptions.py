from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional, Any, Dict

class OntDekkerException(Exception):
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details

class NotFoundException(OntDekkerException):
    def __init__(self, message: str = "Resource not found.", error_code: str = "NOT_FOUND", details: Optional[Any] = None):
        super().__init__(message, error_code, 404, details)

class UnauthorizedException(OntDekkerException):
    def __init__(self, message: str = "Unauthorized access.", error_code: str = "UNAUTHORIZED", details: Optional[Any] = None):
        super().__init__(message, error_code, 401, details)

class ForbiddenException(OntDekkerException):
    def __init__(self, message: str = "Access forbidden.", error_code: str = "FORBIDDEN", details: Optional[Any] = None):
        super().__init__(message, error_code, 403, details)

class ConflictException(OntDekkerException):
    def __init__(self, message: str = "Conflict occurred.", error_code: str = "CONFLICT", details: Optional[Any] = None):
        super().__init__(message, error_code, 409, details)

class ValidationException(OntDekkerException):
    def __init__(self, message: str = "Validation failed.", error_code: str = "VALIDATION_ERROR", details: Optional[Any] = None):
        super().__init__(message, error_code, 422, details)

class DatabaseException(OntDekkerException):
    def __init__(self, message: str = "Database operation failed.", error_code: str = "DATABASE_ERROR", details: Optional[Any] = None):
        super().__init__(message, error_code, 500, details)


# ---------------------------------------------------------------------------
# Short-form aliases used across services for ergonomic imports
# ---------------------------------------------------------------------------

NotFoundError = NotFoundException
ForbiddenError = ForbiddenException
ValidationError = ValidationException
ConflictError = ConflictException
UnauthorizedError = UnauthorizedException


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(OntDekkerException)
    async def ontdekker_exception_handler(request: Request, exc: OntDekkerException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "code": exc.error_code,
                "details": exc.details
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Input validation failed.",
                "code": "VALIDATION_ERROR",
                "details": exc.errors()
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # In production, we'd log the stacktrace here using shared logger
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An unexpected error occurred.",
                "code": "INTERNAL_SERVER_ERROR",
                "details": str(exc) if app.debug else None
            }
        )
