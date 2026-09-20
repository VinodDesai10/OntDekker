"""Initial guide service tables.

Creates all tables for the Guide Service in guide_db.

Table creation order respects FK dependencies:
    1. guide_profiles        (root aggregate — no intra-service FK dependencies)
    2. guide_applications    (no FK to guide_profiles — independent workflow)
    3. guide_locations       (FK → guide_profiles)
    4. guide_languages       (FK → guide_profiles)
    5. guide_availability    (FK → guide_profiles, one-to-one)
    6. guide_reviews         (FK → guide_profiles)
    7. travel_connections    (FK → guide_profiles)

PostgreSQL enums are created before tables via op.execute() to control
ordering precisely.  All sa.Enum() columns in op.create_table() use
postgresql.ENUM(create_type=False) to prevent SQLAlchemy from emitting
a duplicate CREATE TYPE statement after the manual op.execute() above.

Revision ID: 001
Revises    : (none — initial migration)
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Alembic revision identifiers
# ---------------------------------------------------------------------------
revision: str = "001"
down_revision = None          # root migration
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ------------------------------------------------------------------
    # Step 1 — Create PostgreSQL enum types
    # Enums must exist before the columns that reference them.
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TYPE verification_status_enum AS ENUM (
            'PENDING',
            'VERIFIED',
            'SUSPENDED',
            'REVOKED'
        )
    """)

    op.execute("""
        CREATE TYPE application_status_enum AS ENUM (
            'DRAFT',
            'SUBMITTED',
            'UNDER_REVIEW',
            'APPROVED',
            'REJECTED'
        )
    """)

    op.execute("""
        CREATE TYPE availability_status_enum AS ENUM (
            'AVAILABLE',
            'UNAVAILABLE',
            'VACATION',
            'BUSY'
        )
    """)

    # ------------------------------------------------------------------
    # Step 2 — Create tables in FK dependency order
    # ------------------------------------------------------------------

    # ── Table 1: guide_profiles ───────────────────────────────────────
    # Root aggregate. No intra-service FK dependencies.
    # External references (user_id) are plain UUIDs — NOT SQL FKs.
    # AuditMixin: created_at, updated_at, created_by, updated_by
    # SoftDeleteMixin: is_deleted, deleted_at, deleted_by
    op.create_table(
        "guide_profiles",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        # External service reference (no SQL FK to user_db)
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  nullable=False, unique=True,
                  comment="UUID ref to user_db.user_profiles. NOT a SQL FK."),

        # Profile content
        sa.Column("bio",               sa.Text,        nullable=True),
        sa.Column("profile_image_url", sa.String(500), nullable=True),
        sa.Column("cover_image_url",   sa.String(500), nullable=True),
        sa.Column("years_experience",  sa.Integer,     nullable=True),

        # Denormalised aggregate stats
        sa.Column("rating",       sa.Numeric(3, 2), nullable=True),
        sa.Column("review_count", sa.Integer,       nullable=False, server_default="0"),

        # Verification enum
        sa.Column("verification_status",
                  postgresql.ENUM("PENDING", "VERIFIED", "SUSPENDED", "REVOKED",
                                  name="verification_status_enum", create_type=False),
                  nullable=False, server_default="PENDING"),

        # AuditMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),

        # SoftDeleteMixin
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),

        # Constraints
        sa.CheckConstraint(
            "years_experience IS NULL OR years_experience >= 0",
            name="ck_guide_profile_years_experience_non_negative",
        ),
        sa.CheckConstraint(
            "rating IS NULL OR (rating >= 1.00 AND rating <= 5.00)",
            name="ck_guide_profile_rating_range",
        ),
        sa.CheckConstraint(
            "review_count >= 0",
            name="ck_guide_profile_review_count_non_negative",
        ),
    )

    op.create_index("ix_guide_profiles_user_id",             "guide_profiles", ["user_id"])
    op.create_index("ix_guide_profiles_verification_status", "guide_profiles", ["verification_status"])
    op.create_index("ix_guide_profiles_is_deleted",          "guide_profiles", ["is_deleted"])

    # ── Table 2: guide_applications ───────────────────────────────────
    # Independent of guide_profiles — applications precede profile creation.
    # External reference: user_id (no SQL FK to user_db).
    # TimestampMixin: created_at, updated_at
    op.create_table(
        "guide_applications",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        # External service reference (no SQL FK to user_db)
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  nullable=False,
                  comment="UUID ref to user_db.user_profiles. NOT a SQL FK."),

        # Application content
        sa.Column("biography",             sa.Text,        nullable=True),
        sa.Column("areas_covered",         sa.Text,        nullable=True),
        sa.Column("languages",             sa.Text,        nullable=True),
        sa.Column("experience_years",      sa.Integer,     nullable=True),
        sa.Column("certifications",        sa.Text,        nullable=True),
        sa.Column("identity_document_url", sa.String(500), nullable=True,
                  comment="MinIO private object URL for KYC document."),

        # Status
        sa.Column("status",
                  postgresql.ENUM("DRAFT", "SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED",
                                  name="application_status_enum", create_type=False),
                  nullable=False, server_default="DRAFT"),

        # Review metadata
        sa.Column("submitted_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by",   postgresql.UUID(as_uuid=True), nullable=True,
                  comment="UUID ref to admin user. NOT a SQL FK."),
        sa.Column("review_notes",  sa.Text, nullable=True),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        # Constraints
        sa.UniqueConstraint("user_id", name="uq_guide_application_user"),
    )

    op.create_index("ix_guide_applications_user_id", "guide_applications", ["user_id"])
    op.create_index("ix_guide_applications_status",  "guide_applications", ["status"])

    # ── Table 3: guide_locations ──────────────────────────────────────
    # FK → guide_profiles. CASCADE delete.
    # TimestampMixin: created_at, updated_at
    op.create_table(
        "guide_locations",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        sa.Column("guide_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("guide_profiles.id", ondelete="CASCADE"),
                  nullable=False),

        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("region",  sa.String(100), nullable=True),
        sa.Column("city",    sa.String(100), nullable=True),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        sa.UniqueConstraint(
            "guide_id", "country", "region", "city",
            name="uq_guide_location_guide_country_region_city",
        ),
    )

    op.create_index("ix_guide_locations_guide_id", "guide_locations", ["guide_id"])
    op.create_index("ix_guide_locations_country",  "guide_locations", ["country"])

    # ── Table 4: guide_languages ──────────────────────────────────────
    # FK → guide_profiles. CASCADE delete.
    # TimestampMixin: created_at, updated_at
    op.create_table(
        "guide_languages",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        sa.Column("guide_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("guide_profiles.id", ondelete="CASCADE"),
                  nullable=False),

        sa.Column("language", sa.String(80), nullable=False),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        sa.UniqueConstraint(
            "guide_id", "language",
            name="uq_guide_language_guide_language",
        ),
    )

    op.create_index("ix_guide_languages_guide_id", "guide_languages", ["guide_id"])
    op.create_index("ix_guide_languages_language",  "guide_languages", ["language"])

    # ── Table 5: guide_availability ───────────────────────────────────
    # FK → guide_profiles. CASCADE delete. One-to-one (guide_id UNIQUE).
    # TimestampMixin: created_at, updated_at
    op.create_table(
        "guide_availability",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        sa.Column("guide_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("guide_profiles.id", ondelete="CASCADE"),
                  nullable=False, unique=True,
                  comment="One-to-one link to guide_profiles."),

        sa.Column("status",
                  postgresql.ENUM("AVAILABLE", "UNAVAILABLE", "VACATION", "BUSY",
                                  name="availability_status_enum", create_type=False),
                  nullable=False, server_default="AVAILABLE"),

        sa.Column("note", sa.String(300), nullable=True),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_index("ix_guide_availability_guide_id", "guide_availability", ["guide_id"])
    op.create_index("ix_guide_availability_status",   "guide_availability", ["status"])

    # ── Table 6: guide_reviews ────────────────────────────────────────
    # FK → guide_profiles. CASCADE delete.
    # reviewer_id, expedition_id: external refs, no SQL FKs.
    # TimestampMixin: created_at, updated_at
    op.create_table(
        "guide_reviews",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        sa.Column("guide_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("guide_profiles.id", ondelete="CASCADE"),
                  nullable=False),

        # External service references (no SQL FKs)
        sa.Column("reviewer_id",   postgresql.UUID(as_uuid=True), nullable=False,
                  comment="UUID ref to user_db.user_profiles. NOT a SQL FK."),
        sa.Column("expedition_id", postgresql.UUID(as_uuid=True), nullable=True,
                  comment="UUID ref to trip_db.expeditions. NOT a SQL FK."),

        # Rating dimensions (SMALLINT, 1–5)
        sa.Column("rating_overall",        sa.SmallInteger, nullable=False),
        sa.Column("rating_knowledge",      sa.SmallInteger, nullable=False),
        sa.Column("rating_friendliness",   sa.SmallInteger, nullable=False),
        sa.Column("rating_communication",  sa.SmallInteger, nullable=False),
        sa.Column("rating_safety",         sa.SmallInteger, nullable=False),
        sa.Column("rating_professionalism",sa.SmallInteger, nullable=False),

        sa.Column("would_recommend", sa.Boolean, nullable=False),
        sa.Column("comment",         sa.Text,    nullable=True),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        # Constraints
        sa.UniqueConstraint(
            "guide_id", "reviewer_id",
            name="uq_guide_review_guide_reviewer",
        ),
        sa.CheckConstraint("guide_id != reviewer_id",
                           name="ck_guide_review_no_self_review"),
        sa.CheckConstraint("rating_overall         BETWEEN 1 AND 5",
                           name="ck_guide_review_overall"),
        sa.CheckConstraint("rating_knowledge       BETWEEN 1 AND 5",
                           name="ck_guide_review_knowledge"),
        sa.CheckConstraint("rating_friendliness    BETWEEN 1 AND 5",
                           name="ck_guide_review_friendliness"),
        sa.CheckConstraint("rating_communication   BETWEEN 1 AND 5",
                           name="ck_guide_review_communication"),
        sa.CheckConstraint("rating_safety          BETWEEN 1 AND 5",
                           name="ck_guide_review_safety"),
        sa.CheckConstraint("rating_professionalism BETWEEN 1 AND 5",
                           name="ck_guide_review_professionalism"),
    )

    op.create_index("ix_guide_reviews_guide_id",    "guide_reviews", ["guide_id"])
    op.create_index("ix_guide_reviews_reviewer_id", "guide_reviews", ["reviewer_id"])

    # ── Table 7: travel_connections ───────────────────────────────────
    # FK → guide_profiles. CASCADE delete.
    # traveler_id: external ref, no SQL FK.
    # TimestampMixin: created_at, updated_at
    op.create_table(
        "travel_connections",

        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False),

        sa.Column("guide_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("guide_profiles.id", ondelete="CASCADE"),
                  nullable=False),

        # External service reference (no SQL FK to user_db)
        sa.Column("traveler_id", postgresql.UUID(as_uuid=True),
                  nullable=False,
                  comment="UUID ref to user_db.user_profiles. NOT a SQL FK."),

        # Relationship timeline
        sa.Column("first_met",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_interaction", sa.DateTime(timezone=True), nullable=True),

        # Counters
        sa.Column("expeditions_together", sa.Integer, nullable=False, server_default="0"),
        sa.Column("conversation_count",   sa.Integer, nullable=False, server_default="0"),
        sa.Column("photos_shared",        sa.Integer, nullable=False, server_default="0"),

        sa.Column("bookmarked", sa.Boolean, nullable=False, server_default="false"),

        # TimestampMixin
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),

        # Constraints
        sa.UniqueConstraint(
            "guide_id", "traveler_id",
            name="uq_travel_connection_guide_traveler",
        ),
        sa.CheckConstraint("guide_id != traveler_id",
                           name="ck_travel_connection_no_self_connection"),
        sa.CheckConstraint("expeditions_together >= 0",
                           name="ck_travel_connection_expeditions_non_negative"),
        sa.CheckConstraint("conversation_count >= 0",
                           name="ck_travel_connection_conversations_non_negative"),
        sa.CheckConstraint("photos_shared >= 0",
                           name="ck_travel_connection_photos_non_negative"),
    )

    op.create_index("ix_travel_connections_guide_id",       "travel_connections", ["guide_id"])
    op.create_index("ix_travel_connections_traveler_id",    "travel_connections", ["traveler_id"])
    op.create_index("ix_travel_connections_traveler_guide", "travel_connections",
                    ["traveler_id", "guide_id"])


# ---------------------------------------------------------------------------
# downgrade — fully reverses upgrade() in reverse dependency order
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # ------------------------------------------------------------------
    # Step 1 — Drop tables in reverse FK dependency order.
    # Children first, then the root aggregate.
    # Indexes and constraints are dropped automatically with the table.
    # ------------------------------------------------------------------
    op.drop_table("travel_connections")
    op.drop_table("guide_reviews")
    op.drop_table("guide_availability")
    op.drop_table("guide_languages")
    op.drop_table("guide_locations")
    op.drop_table("guide_applications")
    op.drop_table("guide_profiles")

    # ------------------------------------------------------------------
    # Step 2 — Drop PostgreSQL enum types in reverse creation order.
    # Enums cannot be dropped while any column still references them.
    # ------------------------------------------------------------------
    op.execute("DROP TYPE availability_status_enum")
    op.execute("DROP TYPE application_status_enum")
    op.execute("DROP TYPE verification_status_enum")
