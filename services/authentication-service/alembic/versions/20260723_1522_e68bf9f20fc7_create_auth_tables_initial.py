"""create_auth_tables_initial

Creates the initial schema for the Authentication Service (auth_db).

Tables created:
  - users
  - roles
  - user_roles
  - refresh_tokens
  - email_verification_tokens
  - password_reset_tokens

Design notes:
  - All primary keys are UUID (server-generated).
  - All timestamps are stored with timezone (UTC).
  - users uses soft delete (is_deleted, deleted_at, deleted_by).
  - All token tables are hard-deleted — no soft delete columns.
  - Token secrets are stored as SHA-256 hex digests (token_hash, 64 chars).
  - All foreign keys within auth_db use ON DELETE CASCADE.
  - No cross-service foreign key constraints.

Revision ID: e68bf9f20fc7
Revises:
Create Date: 2026-07-23 15:22:00.000000+00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e68bf9f20fc7"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all Authentication Service tables."""

    # ------------------------------------------------------------------
    # users
    # Core identity table. Soft-deleted (is_deleted, deleted_at,
    # deleted_by) because account removal must support audit/recovery.
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        # SoftDeleteMixin
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_is_deleted", "users", ["is_deleted"])
    op.create_index("ix_users_created_at", "users", ["created_at"])

    # ------------------------------------------------------------------
    # roles
    # System role definitions: USER, GUIDE, MODERATOR, ADMIN.
    # Seeded separately; not user-created.
    # ------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_roles_name", "roles", ["name"])

    # ------------------------------------------------------------------
    # user_roles
    # Many-to-many join between users and roles.
    # Supports multiple role assignments per user.
    # ------------------------------------------------------------------
    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    # ------------------------------------------------------------------
    # refresh_tokens
    # Persisted, revocable refresh token records.
    # token_hash = SHA-256 hex digest of the raw token (never plaintext).
    # Hard-deleted: no soft-delete columns.
    # ------------------------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"]
    )
    op.create_index(
        "ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"]
    )
    op.create_index(
        "ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"]
    )

    # ------------------------------------------------------------------
    # email_verification_tokens
    # One-time tokens for email ownership verification.
    # token_hash = SHA-256 hex digest. is_used prevents replay attacks.
    # Hard-deleted.
    # ------------------------------------------------------------------
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_email_verification_tokens_token_hash",
        "email_verification_tokens",
        ["token_hash"],
    )
    op.create_index(
        "ix_email_verification_tokens_user_id",
        "email_verification_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_email_verification_tokens_expires_at",
        "email_verification_tokens",
        ["expires_at"],
    )

    # ------------------------------------------------------------------
    # password_reset_tokens
    # One-time tokens for password reset flow.
    # token_hash = SHA-256 hex digest. is_used prevents replay attacks.
    # Hard-deleted.
    # ------------------------------------------------------------------
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
    )
    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_password_reset_tokens_expires_at",
        "password_reset_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    """Drop all Authentication Service tables in reverse dependency order."""

    # Drop token tables first (they FK to users)
    op.drop_index("ix_password_reset_tokens_expires_at", "password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", "password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", "password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_index("ix_email_verification_tokens_expires_at", "email_verification_tokens")
    op.drop_index("ix_email_verification_tokens_user_id", "email_verification_tokens")
    op.drop_index("ix_email_verification_tokens_token_hash", "email_verification_tokens")
    op.drop_table("email_verification_tokens")

    op.drop_index("ix_refresh_tokens_expires_at", "refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", "refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", "refresh_tokens")
    op.drop_table("refresh_tokens")

    # Drop user_roles before users and roles
    op.drop_index("ix_user_roles_role_id", "user_roles")
    op.drop_index("ix_user_roles_user_id", "user_roles")
    op.drop_table("user_roles")

    # Drop users and roles
    op.drop_index("ix_roles_name", "roles")
    op.drop_table("roles")

    op.drop_index("ix_users_created_at", "users")
    op.drop_index("ix_users_is_deleted", "users")
    op.drop_index("ix_users_email", "users")
    op.drop_table("users")
