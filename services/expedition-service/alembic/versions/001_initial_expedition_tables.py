"""Initial expedition service tables.

Creates all tables for the Expedition Service in trip_db.

Table creation order respects FK dependencies:
    1. expeditions               (root aggregate — no FK dependencies)
    2. expedition_participants   (FK → expeditions)
    3. expedition_join_requests  (FK → expeditions)
    4. expedition_itinerary      (FK → expeditions)
    5. expedition_gallery        (FK → expeditions)
    6. gear_items                (FK → expeditions)
    7. expedition_reviews        (FK → expeditions)

PostgreSQL enums are created before the tables that use them and
dropped in reverse order during downgrade.

Revision ID: 001
Revises    : (none — initial migration)
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Alembic revision identifiers
# ---------------------------------------------------------------------------
revision: str = "001"
down_revision = None          # this is the root migration
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Enum type definitions
# These are created explicitly so that downgrade() can drop them cleanly.
# Using create_type=False in sa.Enum here because we manage creation
# manually via op.execute() to keep full control over ordering.
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ------------------------------------------------------------------
    # Step 1 — Create PostgreSQL enum types
    # Enums must exist before the columns that reference them.
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TYPE expedition_status_enum AS ENUM (
            'DRAFT',
            'PUBLISHED',
            'ACTIVE',
            'COMPLETED',
            'CANCELLED',
            'ARCHIVED'
        )
    """)

    op.execute("""
        CREATE TYPE expedition_visibility_enum AS ENUM (
            'PUBLIC',
            'PRIVATE'
        )
    """)

    op.execute("""
        CREATE TYPE participant_role_enum AS ENUM (
            'ORGANIZER',
            'CO_ORGANIZER',
            'PARTICIPANT'
        )
    """)

    op.execute("""
        CREATE TYPE participant_status_enum AS ENUM (
            'ACTIVE',
            'LEFT',
            'REMOVED'
        )
    """)

    op.execute("""
        CREATE TYPE join_request_status_enum AS ENUM (
            'PENDING',
            'APPROVED',
            'REJECTED',
            'CANCELLED'
        )
    """)

    op.execute("""
        CREATE TYPE gear_category_enum AS ENUM (
            'BASE_PACK',
            'CONSUMABLES',
            'WORN_GEAR'
        )
    """)

    # ------------------------------------------------------------------
    # Step 2 — Create tables in dependency order
    # ------------------------------------------------------------------

    # ── Table 1: expeditions ──────────────────────────────────────────
    # Root aggregate. No intra-service FK dependencies.
    # External references (community_id, organizer_id) are plain UUIDs
    # with NO SQL FK — they reference other microservices' databases.
    op.create_table(
        "expeditions",

        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        # External service references (no SQL FK constraints)
        sa.Column("community_id", postgresql.UUID(as_uuid=True),
                  nullable=False,
                  comment="UUID ref to community_db.communities. NOT a SQL FK."),
        sa.Column("organizer_id", postgresql.UUID(as_uuid=True),
                  nullable=False,
                  comment="UUID ref to user_db.user_profiles. NOT a SQL FK."),

        # Core details
        sa.Column("title",          sa.String(200),  nullable=False),
        sa.Column("destination",    sa.String(200),  nullable=False),
        sa.Column("description",    sa.Text,         nullable=True),
        sa.Column("meeting_point",  sa.String(300),  nullable=True),

        # Dates and capacity
        sa.Column("start_date",        sa.Date,    nullable=True),
        sa.Column("end_date",          sa.Date,    nullable=True),
        sa.Column("max_participants",  sa.Integer, nullable=False, server_default="10"),

        # Budget
        sa.Column("budget", sa.Numeric(12, 2), nullable=True),

        # Enums
        sa.Column("status",
                  postgresql.ENUM("DRAFT", "PUBLISHED", "ACTIVE", "COMPLETED",
                                  "CANCELLED", "ARCHIVED",
                                  name="expedition_status_enum", create_type=False),
                  nullable=False, server_default="DRAFT"),
        sa.Column("visibility",
                  postgresql.ENUM("PUBLIC", "PRIVATE",
                                  name="expedition_visibility_enum", create_type=False),
                  nullable=False, server_default="PUBLIC"),

        # Media
        sa.Column("cover_image_url", sa.String(500), nullable=True),

        # AuditMixin columns
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_by",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by",  postgresql.UUID(as_uuid=True), nullable=True),

        # SoftDeleteMixin columns
        sa.Column("is_deleted",  sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deleted_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by",  postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Indexes on expeditions
    op.create_index("ix_expeditions_community_id",    "expeditions", ["community_id"])
    op.create_index("ix_expeditions_organizer_id",    "expeditions", ["organizer_id"])
    op.create_index("ix_expeditions_status",          "expeditions", ["status"])
    op.create_index("ix_expeditions_is_deleted",      "expeditions", ["is_deleted"])
    op.create_index("ix_expeditions_community_start", "expeditions",
                    ["community_id", "start_date"])

    # ── Table 2: expedition_participants ──────────────────────────────
    op.create_table(
        "expedition_participants",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        # FK to expeditions in the same database
        sa.Column("expedition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("expeditions.id", ondelete="CASCADE"),
                  nullable=False),

        # External ref — no SQL FK to user_db
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  nullable=False,
                  comment="UUID ref to user_db.user_profiles. NOT a SQL FK."),

        sa.Column("role",
                  postgresql.ENUM("ORGANIZER", "CO_ORGANIZER", "PARTICIPANT",
                                  name="participant_role_enum", create_type=False),
                  nullable=False, server_default="PARTICIPANT"),
        sa.Column("status",
                  postgresql.ENUM("ACTIVE", "LEFT", "REMOVED",
                                  name="participant_status_enum", create_type=False),
                  nullable=False, server_default="ACTIVE"),

        sa.Column("joined_at",   sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        # TimestampMixin
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        # Unique constraint: one participation row per user per expedition
        sa.UniqueConstraint("expedition_id", "user_id",
                            name="uq_participant_expedition_user"),
    )

    op.create_index("ix_participants_expedition_id", "expedition_participants",
                    ["expedition_id"])
    op.create_index("ix_participants_user_id",       "expedition_participants",
                    ["user_id"])
    op.create_index("ix_participants_status",        "expedition_participants",
                    ["status"])

    # ── Table 3: expedition_join_requests ─────────────────────────────
    op.create_table(
        "expedition_join_requests",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        sa.Column("expedition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("expeditions.id", ondelete="CASCADE"),
                  nullable=False),

        # External ref — no SQL FK to user_db
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  nullable=False,
                  comment="UUID ref to user_db.user_profiles. NOT a SQL FK."),

        sa.Column("message", sa.Text, nullable=True),
        sa.Column("status",
                  postgresql.ENUM("PENDING", "APPROVED", "REJECTED", "CANCELLED",
                                  name="join_request_status_enum", create_type=False),
                  nullable=False, server_default="PENDING"),

        # Review audit fields
        sa.Column("reviewed_by",       postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejection_reason",  sa.String(500),                nullable=True),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        # Unique constraint: one request per user per expedition
        sa.UniqueConstraint("expedition_id", "user_id",
                            name="uq_join_request_expedition_user"),
    )

    op.create_index("ix_join_requests_expedition_id", "expedition_join_requests",
                    ["expedition_id"])
    op.create_index("ix_join_requests_user_id",       "expedition_join_requests",
                    ["user_id"])
    op.create_index("ix_join_requests_status",        "expedition_join_requests",
                    ["status"])

    # ── Table 4: expedition_itinerary ─────────────────────────────────
    op.create_table(
        "expedition_itinerary",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        sa.Column("expedition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("expeditions.id", ondelete="CASCADE"),
                  nullable=False),

        sa.Column("day_number",    sa.Integer,     nullable=False),
        sa.Column("title",         sa.String(200), nullable=False),
        sa.Column("description",   sa.Text,        nullable=True),
        sa.Column("location",      sa.String(300), nullable=True),
        sa.Column("activity_time", sa.Time,        nullable=True),
        sa.Column("notes",         sa.Text,        nullable=True),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        # Unique: one entry per day per expedition
        sa.UniqueConstraint("expedition_id", "day_number",
                            name="uq_itinerary_expedition_day"),
    )

    op.create_index("ix_itinerary_expedition_id", "expedition_itinerary",
                    ["expedition_id"])

    # ── Table 5: expedition_gallery ───────────────────────────────────
    op.create_table(
        "expedition_gallery",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        sa.Column("expedition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("expeditions.id", ondelete="CASCADE"),
                  nullable=False),

        # External ref — no SQL FK to user_db
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True),
                  nullable=False,
                  comment="UUID ref to user_db.user_profiles. NOT a SQL FK."),

        sa.Column("image_url",     sa.String(500), nullable=False),
        sa.Column("caption",       sa.Text,        nullable=True),
        sa.Column("display_order", sa.Integer,     nullable=False, server_default="0"),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_index("ix_gallery_expedition_id", "expedition_gallery",
                    ["expedition_id"])
    op.create_index("ix_gallery_uploaded_by",   "expedition_gallery",
                    ["uploaded_by"])

    # ── Table 6: gear_items ───────────────────────────────────────────
    op.create_table(
        "gear_items",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        sa.Column("expedition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("expeditions.id", ondelete="CASCADE"),
                  nullable=False),

        # External ref — no SQL FK to user_db
        sa.Column("added_by", postgresql.UUID(as_uuid=True),
                  nullable=False,
                  comment="UUID ref to user_db.user_profiles. NOT a SQL FK."),

        sa.Column("name",     sa.String(200), nullable=False),
        sa.Column("category",
                  postgresql.ENUM("BASE_PACK", "CONSUMABLES", "WORN_GEAR",
                                  name="gear_category_enum", create_type=False),
                  nullable=False, server_default="BASE_PACK"),
        sa.Column("weight_grams", sa.Integer, nullable=False, server_default="0"),
        sa.Column("quantity",     sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_packed",    sa.Boolean, nullable=False, server_default="false"),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        # Check constraints
        sa.CheckConstraint("weight_grams >= 0", name="ck_gear_weight_non_negative"),
        sa.CheckConstraint("quantity >= 1",     name="ck_gear_quantity_positive"),
    )

    op.create_index("ix_gear_items_expedition_id",      "gear_items",
                    ["expedition_id"])
    op.create_index("ix_gear_items_category",           "gear_items",
                    ["category"])
    op.create_index("ix_gear_items_expedition_category","gear_items",
                    ["expedition_id", "category"])

    # ── Table 7: expedition_reviews ───────────────────────────────────
    op.create_table(
        "expedition_reviews",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        sa.Column("expedition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("expeditions.id", ondelete="CASCADE"),
                  nullable=False),

        # External refs — no SQL FKs to user_db
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True),
                  nullable=False,
                  comment="UUID ref to user_db.user_profiles. NOT a SQL FK."),
        sa.Column("reviewee_id", postgresql.UUID(as_uuid=True),
                  nullable=False,
                  comment="UUID ref to user_db.user_profiles. NOT a SQL FK."),

        # Rating dimensions (SMALLINT, 1–5)
        sa.Column("rating_overall",        sa.SmallInteger, nullable=False),
        sa.Column("rating_communication",  sa.SmallInteger, nullable=False),
        sa.Column("rating_safety",         sa.SmallInteger, nullable=False),
        sa.Column("rating_punctuality",    sa.SmallInteger, nullable=False),
        sa.Column("rating_organisation",   sa.SmallInteger, nullable=False),
        sa.Column("rating_friendliness",   sa.SmallInteger, nullable=False),

        sa.Column("would_travel_again", sa.Boolean, nullable=False),
        sa.Column("comment",            sa.Text,    nullable=True),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        # Unique: one review per reviewer-reviewee pair per expedition
        sa.UniqueConstraint(
            "expedition_id", "reviewer_id", "reviewee_id",
            name="uq_review_expedition_reviewer_reviewee",
        ),

        # Check constraints
        sa.CheckConstraint("reviewer_id != reviewee_id",
                           name="ck_review_no_self_review"),
        sa.CheckConstraint("rating_overall       BETWEEN 1 AND 5",
                           name="ck_review_rating_overall"),
        sa.CheckConstraint("rating_communication BETWEEN 1 AND 5",
                           name="ck_review_rating_communication"),
        sa.CheckConstraint("rating_safety        BETWEEN 1 AND 5",
                           name="ck_review_rating_safety"),
        sa.CheckConstraint("rating_punctuality   BETWEEN 1 AND 5",
                           name="ck_review_rating_punctuality"),
        sa.CheckConstraint("rating_organisation  BETWEEN 1 AND 5",
                           name="ck_review_rating_organisation"),
        sa.CheckConstraint("rating_friendliness  BETWEEN 1 AND 5",
                           name="ck_review_rating_friendliness"),
    )

    op.create_index("ix_reviews_expedition_id", "expedition_reviews",
                    ["expedition_id"])
    op.create_index("ix_reviews_reviewer_id",   "expedition_reviews",
                    ["reviewer_id"])
    op.create_index("ix_reviews_reviewee_id",   "expedition_reviews",
                    ["reviewee_id"])


# ---------------------------------------------------------------------------
# downgrade — fully reverses upgrade() in reverse dependency order
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # ------------------------------------------------------------------
    # Step 1 — Drop tables in reverse dependency order
    # Children must be dropped before the parent (expeditions).
    # Indexes and constraints are dropped automatically with the table.
    # ------------------------------------------------------------------
    op.drop_table("expedition_reviews")
    op.drop_table("gear_items")
    op.drop_table("expedition_gallery")
    op.drop_table("expedition_itinerary")
    op.drop_table("expedition_join_requests")
    op.drop_table("expedition_participants")
    op.drop_table("expeditions")

    # ------------------------------------------------------------------
    # Step 2 — Drop PostgreSQL enum types in reverse creation order.
    # Enums cannot be dropped while any column still references them,
    # so tables must be gone first.
    # ------------------------------------------------------------------
    op.execute("DROP TYPE gear_category_enum")
    op.execute("DROP TYPE join_request_status_enum")
    op.execute("DROP TYPE participant_status_enum")
    op.execute("DROP TYPE participant_role_enum")
    op.execute("DROP TYPE expedition_visibility_enum")
    op.execute("DROP TYPE expedition_status_enum")
