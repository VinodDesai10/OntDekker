"""Add expedition_discussion_messages table.

Introduces the discussion table that stores messages posted by active
expedition participants (and organizers) within a trip's Discussion tab.

Key design choices:
  - expedition_id is a real FK → expeditions.id (ON DELETE CASCADE).
  - author_id is a plain UUID with no FK (mirrors the participant convention
    — identity is the JWT sub claim, resolved via user-service at read time).
  - content is TEXT; application layer enforces 2000-char limit.
  - CheckConstraint prevents blank content at the database level.
  - Composite index (expedition_id, created_at) supports the primary query
    pattern: "fetch all messages for trip X ordered oldest → newest".
  - No enums required for this table.

Revision ID: 003
Revises    : 002
Create Date: 2026-08-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Alembic revision identifiers
# ---------------------------------------------------------------------------
revision: str = "003"
down_revision: str = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Create expedition_discussion_messages table
    # ------------------------------------------------------------------
    op.create_table(
        "expedition_discussion_messages",

        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),

        # FK to expeditions in the same database
        sa.Column(
            "expedition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("expeditions.id", ondelete="CASCADE"),
            nullable=False,
        ),

        # Author — JWT sub, no SQL FK to user_db / auth_db
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="JWT sub claim (auth-service UUID). NOT a SQL FK.",
        ),

        # Message content
        sa.Column("content", sa.Text, nullable=False),

        # Timestamps (TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),

        # DB-level guard: content must not be blank/whitespace only
        sa.CheckConstraint(
            "LENGTH(TRIM(content)) > 0",
            name="ck_expedition_discussion_content_not_empty",
        ),
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    # Primary read path: all messages for an expedition ordered by time
    op.create_index(
        "ix_expedition_discussion_expedition_created",
        "expedition_discussion_messages",
        ["expedition_id", "created_at"],
    )

    # Secondary: lookup by author (future moderation / audit)
    op.create_index(
        "ix_expedition_discussion_author_id",
        "expedition_discussion_messages",
        ["author_id"],
    )


def downgrade() -> None:
    # Drop indexes before the table
    op.drop_index(
        "ix_expedition_discussion_author_id",
        table_name="expedition_discussion_messages",
    )
    op.drop_index(
        "ix_expedition_discussion_expedition_created",
        table_name="expedition_discussion_messages",
    )
    op.drop_table("expedition_discussion_messages")
