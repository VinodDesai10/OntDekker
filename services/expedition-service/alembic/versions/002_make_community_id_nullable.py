"""Make community_id nullable on expeditions table.

Personal trips (not associated with any community) require community_id
to be optional. This migration alters the column from NOT NULL → NULL.

Revision ID: 002
Revises    : 001
Create Date: 2026-08-07
"""

from alembic import op

revision: str = "002"
down_revision: str = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Allow community_id to be NULL — personal trips have no community
    op.alter_column(
        "expeditions",
        "community_id",
        nullable=True,
    )


def downgrade() -> None:
    # Revert to NOT NULL. Any NULL rows must be resolved before running this.
    op.alter_column(
        "expeditions",
        "community_id",
        nullable=False,
    )
