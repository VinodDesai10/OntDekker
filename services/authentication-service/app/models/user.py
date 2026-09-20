"""
Authentication Service — SQLAlchemy ORM Models

Database: auth_db
Owner: Developer 1

Tables:
  - users               : Core identity and credentials
  - roles               : System role definitions
  - user_roles          : Many-to-many user ↔ role mapping
  - refresh_tokens      : Persisted, revocable refresh token records
  - email_verification_tokens : One-time email ownership tokens
  - password_reset_tokens     : One-time password reset tokens
  - email_verification_otps   : Short-lived OTP records for email verification

Design decisions:
  - All primary keys: UUID (server-generated via uuid4)
  - All timestamps: UTC, via TimestampMixin
  - users: soft-deleted (is_deleted, deleted_at, deleted_by from SoftDeleteMixin)
  - All token tables: hard-deleted per documented architecture
    ("Hard Deletes reserved for Temporary Tokens" — 06-database-architecture.md)
  - Tokens are stored as SHA-256 digest (token_hash), never as raw values.
    Documentation states "Refresh tokens stored securely" without specifying the
    mechanism. Storing only the hash prevents token leakage from a DB compromise.
  - OTP secrets are stored as hashed digests (otp_hash), never as plaintext.
  - No cross-service foreign keys. user_id in token tables references users.id
    within auth_db only.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base, SoftDeleteMixin, TimestampMixin


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------

class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    Core identity record for every registered account.

    Owns: email, hashed password, verification status, active status.
    Does NOT own: profile data, preferences, reputation, badges — those
    belong to user_db (User Service).

    Soft-deleted because accounts require auditability and moderation
    recovery. Deletion does not physically remove the row.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    # Timestamp set when the user's email is confirmed. Null until verified.
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    roles: Mapped[List["UserRole_"]] = relationship(
        "UserRole_",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    email_verification_tokens: Mapped[List["EmailVerificationToken"]] = relationship(
        "EmailVerificationToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    password_reset_tokens: Mapped[List["PasswordResetToken"]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    email_verification_otps: Mapped[List["EmailVerificationOTP"]] = relationship(
        "EmailVerificationOTP",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        # email is the primary lookup field — unique index applied.
        Index("ix_users_email", "email"),
        # Soft-delete filter is common — index is_deleted for performance.
        Index("ix_users_is_deleted", "is_deleted"),
        # Sorting / audit queries by creation time.
        Index("ix_users_created_at", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email!r} verified={self.is_verified}>"


# ---------------------------------------------------------------------------
# roles
# ---------------------------------------------------------------------------

class Role(Base, TimestampMixin):
    """
    System role definitions.

    Stores the four documented roles: USER, GUIDE, MODERATOR, ADMIN.
    Seeded at migration time; not user-created.

    Uses the shared UserRole enum to enforce the valid role name set.
    """

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )

    # Relationships
    user_roles: Mapped[List["UserRole_"]] = relationship(
        "UserRole_",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_roles_name", "name"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Role id={self.id} name={self.name!r}>"


# ---------------------------------------------------------------------------
# user_roles  (many-to-many join table)
# ---------------------------------------------------------------------------

class UserRole_(Base, TimestampMixin):
    """
    Many-to-many join between users and roles.

    Named UserRole_ (with trailing underscore) to avoid collision with the
    shared UserRole enum import. The underlying table is named 'user_roles'.

    Supports future multiple role assignments per user.
    Within auth_db, uses real FK constraints to both users and roles.
    """

    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")

    __table_args__ = (
        # Each user may hold a given role only once.
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
        Index("ix_user_roles_user_id", "user_id"),
        Index("ix_user_roles_role_id", "role_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserRole_ user_id={self.user_id} role_id={self.role_id}>"


# ---------------------------------------------------------------------------
# refresh_tokens
# ---------------------------------------------------------------------------

class RefreshToken(Base, TimestampMixin):
    """
    Persisted refresh token record.

    Security: the raw token is NEVER stored. Only the SHA-256 hex digest
    (token_hash) is persisted. This means a database compromise cannot
    expose active sessions. The raw token is generated in memory, returned
    to the client once, and discarded.

    Lifecycle:
      - is_revoked = False: token is valid (subject to expiry check)
      - is_revoked = True : token has been explicitly invalidated (logout,
                             rotation, suspicious activity)
      - expires_at past   : token is expired and must be rejected

    Hard-deleted per architecture ("Hard Deletes reserved for Temporary
    Tokens"). Expired or revoked tokens are physically removed by a
    cleanup job (implemented in a later checkpoint).
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # SHA-256 hex digest of the raw token (64 hex chars = 256 bits).
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        # Primary lookup path: validate a token by its hash.
        Index("ix_refresh_tokens_token_hash", "token_hash"),
        # Look up all tokens for a user (e.g., logout all sessions).
        Index("ix_refresh_tokens_user_id", "user_id"),
        # Cleanup job: find all expired tokens efficiently.
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RefreshToken id={self.id} user_id={self.user_id} "
            f"revoked={self.is_revoked}>"
        )


# ---------------------------------------------------------------------------
# email_verification_tokens
# ---------------------------------------------------------------------------

class EmailVerificationToken(Base, TimestampMixin):
    """
    One-time email ownership verification token.

    Issued on registration. User clicks a verification link containing the
    raw token; the service looks up the SHA-256 hash, checks expiry and
    used status, then marks the user as verified.

    is_used = True once consumed, preventing replay attacks.
    Hard-deleted after use or expiry.
    """

    __tablename__ = "email_verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # SHA-256 hex digest of the raw verification token.
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="email_verification_tokens"
    )

    __table_args__ = (
        Index("ix_email_verification_tokens_token_hash", "token_hash"),
        Index("ix_email_verification_tokens_user_id", "user_id"),
        Index("ix_email_verification_tokens_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<EmailVerificationToken id={self.id} user_id={self.user_id} "
            f"used={self.is_used}>"
        )


# ---------------------------------------------------------------------------
# password_reset_tokens
# ---------------------------------------------------------------------------

class PasswordResetToken(Base, TimestampMixin):
    """
    One-time password reset token.

    Issued on 'forgot password' request. User submits the raw token from
    their email; the service verifies the SHA-256 hash, checks expiry and
    used status, then allows the password update.

    is_used = True once consumed. Hard-deleted after use or expiry.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # SHA-256 hex digest of the raw reset token.
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="password_reset_tokens")

    __table_args__ = (
        Index("ix_password_reset_tokens_token_hash", "token_hash"),
        Index("ix_password_reset_tokens_user_id", "user_id"),
        Index("ix_password_reset_tokens_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PasswordResetToken id={self.id} user_id={self.user_id} "
            f"used={self.is_used}>"
        )


# ---------------------------------------------------------------------------
# email_verification_otps
# ---------------------------------------------------------------------------

class EmailVerificationOTP(Base, TimestampMixin):
    """
    Short-lived OTP record for email address verification.

    Security: the raw OTP is NEVER stored. Only the hashed digest
    (otp_hash) is persisted, preventing OTP leakage from a DB compromise.

    Lifecycle:
      - Each OTP has a fixed expiry (expires_at).
      - attempts tracks how many times verification was tried against this
        record; the verification logic (Checkpoint 2) enforces a limit.
      - Hard-deleted per architecture: expired or consumed OTPs are
        physically removed; no soft-delete columns.

    Relationship:
      - Belongs to one User (user_id → users.id, ON DELETE CASCADE).
      - User may have many OTP records (e.g., after resend).
    """

    __tablename__ = "email_verification_otps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Hashed digest of the raw OTP — raw value is never stored.
    otp_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    # Number of failed verification attempts against this OTP record.
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="email_verification_otps"
    )

    __table_args__ = (
        # Primary lookup: find active OTP records for a given user.
        Index("ix_email_verification_otps_user_id", "user_id"),
        # Cleanup job: efficiently find all expired OTP records.
        Index("ix_email_verification_otps_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<EmailVerificationOTP id={self.id} user_id={self.user_id} "
            f"expires_at={self.expires_at}>"
        )
