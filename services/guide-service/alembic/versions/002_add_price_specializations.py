"""Add price_per_day to guide_profiles and create guide_specializations table.

Revision ID: 002
Revises    : 001
Create Date: 2026-08-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Alembic revision identifiers
# ---------------------------------------------------------------------------
revision: str = "002"
down_revision: str = "001"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ------------------------------------------------------------------
    # Step 1 — Add price_per_day column to guide_profiles
    # ------------------------------------------------------------------
    op.add_column(
        "guide_profiles",
        sa.Column(
            "price_per_day",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Guide's daily rate in USD (nullable until set by guide).",
        ),
    )

    op.create_check_constraint(
        "ck_guide_profile_price_non_negative",
        "guide_profiles",
        "price_per_day IS NULL OR price_per_day >= 0",
    )

    # ------------------------------------------------------------------
    # Step 2 — Create guide_specializations table
    # FK → guide_profiles. CASCADE delete.
    # TimestampMixin: created_at, updated_at
    # ------------------------------------------------------------------
    op.create_table(
        "guide_specializations",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        sa.Column("guide_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("guide_profiles.id", ondelete="CASCADE"),
                  nullable=False),

        # Category is a free-form text tag (e.g. "alpine", "sea kayaking")
        sa.Column("category", sa.String(100), nullable=False),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        # A guide cannot have the same category twice
        sa.UniqueConstraint(
            "guide_id", "category",
            name="uq_guide_specialization_guide_category",
        ),
    )

    op.create_index(
        "ix_guide_specializations_guide_id",
        "guide_specializations",
        ["guide_id"],
    )
    op.create_index(
        "ix_guide_specializations_category",
        "guide_specializations",
        ["category"],
    )


# ---------------------------------------------------------------------------
# downgrade — fully reverses upgrade() in reverse order
# ---------------------------------------------------------------------------

def downgrade() -> None:
    op.drop_table("guide_specializations")

    op.drop_constraint(
        "ck_guide_profile_price_non_negative",
        "guide_profiles",
        type_="check",
    )

    op.drop_column("guide_profiles", "price_per_day")
