"""seed_system_roles

Idempotent data migration that inserts the four system roles required by
the Authentication Service:

  USER        — standard registered user
  GUIDE       — verified local guide
  MODERATOR   — platform content moderator
  ADMIN       — platform administrator

Uses INSERT ... ON CONFLICT DO NOTHING so it is safe to run multiple times
(e.g., in CI, local development, or fresh deployments). The role IDs are
stable UUIDs defined here — they will be the same on every environment,
which makes foreign-key references in fixtures and seeds predictable.

The downgrade removes only these four seeded rows; it does not drop the
roles table (schema DDL is managed by the previous migration).

Revision ID: a1b2c3d4e5f6
Revises: e68bf9f20fc7
Create Date: 2026-07-23 17:00:00.000000+00:00
"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e68bf9f20fc7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Stable UUIDs for the four system roles.
# Fixed values ensure every environment has the same role IDs,
# making fixtures, integration tests, and cross-environment consistency reliable.
ROLE_USER_ID      = "00000000-0000-0000-0000-000000000001"
ROLE_GUIDE_ID     = "00000000-0000-0000-0000-000000000002"
ROLE_MODERATOR_ID = "00000000-0000-0000-0000-000000000003"
ROLE_ADMIN_ID     = "00000000-0000-0000-0000-000000000004"

NOW = datetime.now(timezone.utc).isoformat()


def upgrade() -> None:
    """Insert the four system roles idempotently."""
    # UUIDs and timestamp are embedded as literals because they are
    # compile-time constants, not user input — no injection risk.
    # asyncpg correctly infers the types from the PostgreSQL cast syntax
    # when values are inline literals.
    op.execute(sa.text(f"""
        INSERT INTO roles (id, name, created_at, updated_at)
        VALUES
            ('{ROLE_USER_ID}'::uuid,      'USER',      '{NOW}'::timestamptz, '{NOW}'::timestamptz),
            ('{ROLE_GUIDE_ID}'::uuid,     'GUIDE',     '{NOW}'::timestamptz, '{NOW}'::timestamptz),
            ('{ROLE_MODERATOR_ID}'::uuid, 'MODERATOR', '{NOW}'::timestamptz, '{NOW}'::timestamptz),
            ('{ROLE_ADMIN_ID}'::uuid,     'ADMIN',     '{NOW}'::timestamptz, '{NOW}'::timestamptz)
        ON CONFLICT (name) DO NOTHING
    """))


def downgrade() -> None:
    """Remove the four seeded system roles."""
    op.execute(
        sa.text(
            "DELETE FROM roles WHERE name IN ('USER', 'GUIDE', 'MODERATOR', 'ADMIN')"
        )
    )
