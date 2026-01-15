"""Initial database schema for Nexus Core MVP1.

Creates all 12 tables with pgvector support, indexes, and cascade rules.

Reference:
- DATABASE_SCHEMA_v1.0.md
- DATABASE_CONSTRAINTS_v1.0.md
- GOVERNANCE_FLOW_v1.0.md

Revision ID: 001
Revises:
Create Date: 2026-01-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema.

    Tables (12 total):
    1. sources - Primary source records
    2. governance_events - Immutable audit log
    3. duplicate_decisions - Admin duplicate decisions
    4. manifests - Manifest metadata
    5. chunks - Chunk records
    6. embeddings - pgvector embeddings
    7. fts_index - Full-text search
    8. validation_reports - Validation metadata
    9. feedback - User feedback
    10. tier_limits - Tier definitions
    11. account_tiers - User tier assignments
    12. source_links - Additional access grants
    """
    # Enable required extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ==========================================================================
    # Create Enum types
    # ==========================================================================

    # GovernanceStatus enum (from GOVERNANCE_FLOW_v1.0.md Section 3)
    governance_status = postgresql.ENUM(
        "DISCOVERED",
        "PENDING_APPROVAL",
        "DUPLICATE_DETECTED",
        "DENIED",
        "APPROVED",
        "INGESTING",
        "INGESTED",
        "ERROR",
        "DEACTIVATED",
        name="governancestatus",
        create_type=True,
    )
    governance_status.create(op.get_bind(), checkfirst=True)

    # EventType enum
    event_type = postgresql.ENUM(
        "STATUS_CHANGE",
        "REMOVAL_REQUEST",
        name="eventtype",
        create_type=True,
    )
    event_type.create(op.get_bind(), checkfirst=True)

    # DuplicateDecisionType enum
    duplicate_decision_type = postgresql.ENUM(
        "IGNORE_DUPLICATE",
        "ALLOW_SEPARATE_INSTANCE",
        name="duplicatedecisiontype",
        create_type=True,
    )
    duplicate_decision_type.create(op.get_bind(), checkfirst=True)

    # ToolId enum
    tool_id = postgresql.ENUM(
        "docling",
        "unstructured",
        name="toolid",
        create_type=True,
    )
    tool_id.create(op.get_bind(), checkfirst=True)

    # ManifestType enum
    manifest_type = postgresql.ENUM(
        "raw",
        "normalized",
        "enriched",
        "original_source",
        name="manifesttype",
        create_type=True,
    )
    manifest_type.create(op.get_bind(), checkfirst=True)

    # ValidationStatus enum
    validation_status = postgresql.ENUM(
        "PASS",
        "FAIL",
        name="validationstatus",
        create_type=True,
    )
    validation_status.create(op.get_bind(), checkfirst=True)

    # FeedbackRating enum
    feedback_rating = postgresql.ENUM(
        "UP",
        "DOWN",
        name="feedbackrating",
        create_type=True,
    )
    feedback_rating.create(op.get_bind(), checkfirst=True)

    # Tier enum
    tier = postgresql.ENUM(
        "FREE",
        "BASIC",
        "PRO",
        name="tier",
        create_type=True,
    )
    tier.create(op.get_bind(), checkfirst=True)

    # ScopeType enum
    scope_type = postgresql.ENUM(
        "USER",
        "GAME",
        name="scopetype",
        create_type=True,
    )
    scope_type.create(op.get_bind(), checkfirst=True)

    # ==========================================================================
    # Table 1: sources (DATABASE_SCHEMA_v1.0.md Section 2.1)
    # ==========================================================================
    op.create_table(
        "sources",
        sa.Column("doc_id", sa.String(120), primary_key=True),
        sa.Column("source_sha256", sa.String(64), unique=True, nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("current_path", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "DISCOVERED",
                "PENDING_APPROVAL",
                "DUPLICATE_DETECTED",
                "DENIED",
                "APPROVED",
                "INGESTING",
                "INGESTED",
                "ERROR",
                "DEACTIVATED",
                name="governancestatus",
                create_type=False,
            ),
            nullable=False,
            server_default="DISCOVERED",
        ),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("system_id", sa.Text(), nullable=True),
        sa.Column("game_id", sa.Text(), nullable=True),
        sa.Column("owner_user_id", sa.Text(), nullable=False),
    )

    # Indexes for sources (B-tree indexes)
    op.create_index("ix_sources_status", "sources", ["status"])
    op.create_index("ix_sources_system_id", "sources", ["system_id"])
    op.create_index("ix_sources_game_id", "sources", ["game_id"])
    op.create_index("ix_sources_owner_user_id", "sources", ["owner_user_id"])

    # ==========================================================================
    # Table 2: governance_events (DATABASE_SCHEMA_v1.0.md Section 2.2)
    # ==========================================================================
    op.create_table(
        "governance_events",
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "doc_id",
            sa.String(120),
            sa.ForeignKey("sources.doc_id", ondelete="CASCADE", onupdate="RESTRICT"),
            nullable=False,
        ),
        sa.Column("from_status", sa.Text(), nullable=True),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column(
            "event_type",
            postgresql.ENUM(
                "STATUS_CHANGE",
                "REMOVAL_REQUEST",
                name="eventtype",
                create_type=False,
            ),
            nullable=False,
            server_default="STATUS_CHANGE",
        ),
        sa.Column("triggered_by", sa.Text(), nullable=False),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
    )

    op.create_index("ix_governance_events_doc_id", "governance_events", ["doc_id"])

    # ==========================================================================
    # Table 3: duplicate_decisions (DATABASE_SCHEMA_v1.0.md Section 2.3)
    # ==========================================================================
    op.create_table(
        "duplicate_decisions",
        sa.Column(
            "doc_id",
            sa.String(120),
            sa.ForeignKey("sources.doc_id", ondelete="CASCADE", onupdate="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "decision",
            postgresql.ENUM(
                "IGNORE_DUPLICATE",
                "ALLOW_SEPARATE_INSTANCE",
                name="duplicatedecisiontype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("decided_by", sa.Text(), nullable=False),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ==========================================================================
    # Table 4: manifests (DATABASE_SCHEMA_v1.0.md Section 3.1)
    # ==========================================================================
    op.create_table(
        "manifests",
        sa.Column(
            "manifest_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "doc_id",
            sa.String(120),
            sa.ForeignKey("sources.doc_id", ondelete="CASCADE", onupdate="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "tool_id",
            postgresql.ENUM("docling", "unstructured", name="toolid", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "manifest_type",
            postgresql.ENUM(
                "raw",
                "normalized",
                "enriched",
                "original_source",
                name="manifesttype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_manifests_doc_id", "manifests", ["doc_id"])
    op.create_index("ix_manifests_tool_id", "manifests", ["tool_id"])
    op.create_index("ix_manifests_manifest_type", "manifests", ["manifest_type"])

    # ==========================================================================
    # Table 5: chunks (DATABASE_SCHEMA_v1.0.md Section 3.2)
    # ==========================================================================
    op.create_table(
        "chunks",
        sa.Column("chunk_id", sa.Text(), primary_key=True),
        sa.Column(
            "doc_id",
            sa.String(120),
            sa.ForeignKey("sources.doc_id", ondelete="CASCADE", onupdate="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "tool_id",
            postgresql.ENUM("docling", "unstructured", name="toolid", create_type=False),
            nullable=False,
        ),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_sha256", sa.String(64), nullable=False),
        sa.Column("section_path", sa.Text(), nullable=True),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("system_id", sa.Text(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("doc_id", "tool_id", "chunk_sha256", name="uq_chunk_identity"),
    )

    op.create_index("ix_chunks_doc_id", "chunks", ["doc_id"])
    op.create_index("ix_chunks_tool_id", "chunks", ["tool_id"])
    op.create_index("ix_chunks_system_id", "chunks", ["system_id"])
    op.create_index("ix_chunks_active", "chunks", ["active"])

    # ==========================================================================
    # Table 6: embeddings (DATABASE_SCHEMA_v1.0.md Section 3.3)
    # pgvector with 384 dimensions (sentence-transformers/all-MiniLM-L6-v2)
    # ==========================================================================
    op.create_table(
        "embeddings",
        sa.Column(
            "chunk_id",
            sa.Text(),
            sa.ForeignKey("chunks.chunk_id", ondelete="CASCADE", onupdate="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Alter column to use vector type after table creation
    op.execute("ALTER TABLE embeddings ALTER COLUMN embedding TYPE vector(384) USING embedding::vector(384)")

    # Create HNSW index for vector similarity search
    op.execute(
        """
        CREATE INDEX ix_embeddings_embedding_hnsw ON embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )

    # ==========================================================================
    # Table 7: fts_index (DATABASE_SCHEMA_v1.0.md Section 3.4)
    # ==========================================================================
    op.create_table(
        "fts_index",
        sa.Column(
            "chunk_id",
            sa.Text(),
            sa.ForeignKey("chunks.chunk_id", ondelete="CASCADE", onupdate="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("tsv", postgresql.TSVECTOR(), nullable=False),
    )

    # GIN index for full-text search
    op.create_index(
        "ix_fts_index_tsv",
        "fts_index",
        ["tsv"],
        postgresql_using="gin",
    )

    # ==========================================================================
    # Table 8: validation_reports (DATABASE_SCHEMA_v1.0.md Section 4.1)
    # ==========================================================================
    op.create_table(
        "validation_reports",
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "doc_id",
            sa.String(120),
            sa.ForeignKey("sources.doc_id", ondelete="CASCADE", onupdate="RESTRICT"),
            nullable=False,
        ),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("PASS", "FAIL", name="validationstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("report_path", sa.Text(), nullable=False),
        sa.Column("report_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_validation_reports_doc_id", "validation_reports", ["doc_id"])

    # ==========================================================================
    # Table 9: feedback (DATABASE_SCHEMA_v1.0.md Section 5.1)
    # ==========================================================================
    op.create_table(
        "feedback",
        sa.Column(
            "feedback_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "doc_id",
            sa.String(120),
            sa.ForeignKey("sources.doc_id", ondelete="CASCADE", onupdate="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id",
            sa.Text(),
            sa.ForeignKey("chunks.chunk_id", ondelete="CASCADE", onupdate="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "rating",
            postgresql.ENUM("UP", "DOWN", name="feedbackrating", create_type=False),
            nullable=False,
        ),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_feedback_chunk_id", "feedback", ["chunk_id"])
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])

    # ==========================================================================
    # Table 10: tier_limits (DATABASE_SCHEMA_v1.0.md Section 5.2)
    # ==========================================================================
    op.create_table(
        "tier_limits",
        sa.Column(
            "tier",
            postgresql.ENUM("FREE", "BASIC", "PRO", name="tier", create_type=False),
            primary_key=True,
        ),
        sa.Column("max_sources", sa.Integer(), nullable=False),
        sa.Column("max_active_sources", sa.Integer(), nullable=False),
        sa.Column("max_games", sa.Integer(), nullable=False),
        sa.Column("max_storage_mb", sa.Integer(), nullable=False),
    )

    # Insert default tier limits
    op.execute(
        """
        INSERT INTO tier_limits (tier, max_sources, max_active_sources, max_games, max_storage_mb)
        VALUES
            ('FREE', 5, 3, 1, 100),
            ('BASIC', 25, 15, 5, 1000),
            ('PRO', 100, 50, 20, 10000)
        """
    )

    # ==========================================================================
    # Table 11: account_tiers (DATABASE_SCHEMA_v1.0.md Section 5.3)
    # ==========================================================================
    op.create_table(
        "account_tiers",
        sa.Column("user_id", sa.Text(), primary_key=True),
        sa.Column(
            "tier",
            postgresql.ENUM("FREE", "BASIC", "PRO", name="tier", create_type=False),
            nullable=False,
            server_default="FREE",
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ==========================================================================
    # Table 12: source_links (DATABASE_SCHEMA_v1.0.md Section 6.1)
    # ==========================================================================
    op.create_table(
        "source_links",
        sa.Column(
            "link_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "doc_id",
            sa.String(120),
            sa.ForeignKey("sources.doc_id", ondelete="CASCADE", onupdate="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "scope_type",
            postgresql.ENUM("USER", "GAME", name="scopetype", create_type=False),
            nullable=False,
        ),
        sa.Column("owner_user_id", sa.Text(), nullable=True),
        sa.Column("game_id", sa.Text(), nullable=True),
        sa.Column("gm_only", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.create_index("ix_source_links_doc_id", "source_links", ["doc_id"])
    op.create_index("ix_source_links_owner_user_id", "source_links", ["owner_user_id"])
    op.create_index("ix_source_links_game_id", "source_links", ["game_id"])


def downgrade() -> None:
    """Drop all tables and types in reverse order."""
    # Drop tables in reverse dependency order
    op.drop_table("source_links")
    op.drop_table("account_tiers")
    op.drop_table("tier_limits")
    op.drop_table("feedback")
    op.drop_table("validation_reports")
    op.drop_table("fts_index")
    op.drop_table("embeddings")
    op.drop_table("chunks")
    op.drop_table("manifests")
    op.drop_table("duplicate_decisions")
    op.drop_table("governance_events")
    op.drop_table("sources")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS scopetype")
    op.execute("DROP TYPE IF EXISTS tier")
    op.execute("DROP TYPE IF EXISTS feedbackrating")
    op.execute("DROP TYPE IF EXISTS validationstatus")
    op.execute("DROP TYPE IF EXISTS manifesttype")
    op.execute("DROP TYPE IF EXISTS toolid")
    op.execute("DROP TYPE IF EXISTS duplicatedecisiontype")
    op.execute("DROP TYPE IF EXISTS eventtype")
    op.execute("DROP TYPE IF EXISTS governancestatus")

    # Note: We don't drop the vector extension as it may be used by other schemas
