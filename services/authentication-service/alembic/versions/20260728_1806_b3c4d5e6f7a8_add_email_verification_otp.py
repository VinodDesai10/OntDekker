"""add_email_verification_otp

Extends the Authentication Service schema with the database foundation
required for OTP-based email verification:

  1. users.verified_at  — nullable timestamp set when email is confirmed.
  2. email_verification_otps — new table storing hashed OTP records.

Design notes:
  - users.verified_at is nullable; NULL means the account has not yet been
    verified. Non-null means verified and records the verification timestamp.
  - users.is_verified was already present (initial migration). This
    migration only adds the companion verified_at column.
  - otp_hash stores a hashed digest of the raw OTP — the plaintext OTP is
    never persisted, consistent with the token_hash pattern used by all
    other token tables in this service.
  - email_verification_otps is hard-deleted (no soft-delete columns),
    consistent with the "Hard Deletes reserved for Temporary Tokens"
    architecture decision.
  - Indexes on user_id and expires_at support the two primary access
    patterns: looking up active OTPs per user and cleaning up expired rows.

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-07-28 18:06:00.000000+00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    1. Add verified_at to users.
    2. Create email_verification_otps table with indexes.
    """

    # ------------------------------------------------------------------
    # 1. users — add verified_at
    # Nullable: NULL until the user completes email verification.
    # ------------------------------------------------------------------
    op.add_column(
        "users",
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # ------------------------------------------------------------------
    # 2. email_verification_otps
    # Stores hashed OTP records issued for email verification.
    # Hard-deleted; no soft-delete columns.
    # ------------------------------------------------------------------
    op.create_table(
        "email_verification_otps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Hashed digest of the raw OTP — never stored as plaintext.
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        # Number of failed verification attempts against this record.
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index: look up active OTP records for a given user.
    op.create_index(
        "ix_email_verification_otps_user_id",
        "email_verification_otps",
        ["user_id"],
    )
    # Index: cleanup job — find all expired OTP records efficiently.
    op.create_index(
        "ix_email_verification_otps_expires_at",
        "email_verification_otps",
        ["expires_at"],
    )


def downgrade() -> None:
    """
    Reverse in the opposite order of upgrade:
    1. Drop email_verification_otps (indexes first, then table).
    2. Drop users.verified_at.
    """

    # ------------------------------------------------------------------
    # 1. Drop email_verification_otps
    # ------------------------------------------------------------------
    op.drop_index(
        "ix_email_verification_otps_expires_at",
        table_name="email_verification_otps",
    )
    op.drop_index(
        "ix_email_verification_otps_user_id",
        table_name="email_verification_otps",
    )
    op.drop_table("email_verification_otps")

    # ------------------------------------------------------------------
    # 2. Remove verified_at from users
    # ------------------------------------------------------------------
    op.drop_column("users", "verified_at")
