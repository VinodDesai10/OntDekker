# Authentication Service — Models Package
#
# Importing all models here ensures that SQLAlchemy's Base.metadata
# is populated with every table when this package is imported.
# Alembic's env.py imports this package, which triggers model registration.

from app.models.user import (
    User,
    Role,
    UserRole_,
    RefreshToken,
    EmailVerificationToken,
    PasswordResetToken,
    EmailVerificationOTP,
)

__all__ = [
    "User",
    "Role",
    "UserRole_",
    "RefreshToken",
    "EmailVerificationToken",
    "PasswordResetToken",
    "EmailVerificationOTP",
]
