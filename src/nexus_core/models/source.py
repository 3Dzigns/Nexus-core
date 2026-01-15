"""Database models for Nexus Core MVP1.

Reference: DATABASE_SCHEMA_v1.0.md
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexus_core.models.base import Base


# =============================================================================
# Enums (from DATABASE_SCHEMA_v1.0.md)
# =============================================================================


class GovernanceStatus(str, enum.Enum):
    """Governance states from GOVERNANCE_FLOW_v1.0.md Section 3."""

    DISCOVERED = "DISCOVERED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    DUPLICATE_DETECTED = "DUPLICATE_DETECTED"
    DENIED = "DENIED"
    APPROVED = "APPROVED"
    INGESTING = "INGESTING"
    INGESTED = "INGESTED"
    ERROR = "ERROR"
    DEACTIVATED = "DEACTIVATED"


class EventType(str, enum.Enum):
    """Governance event types."""

    STATUS_CHANGE = "STATUS_CHANGE"
    REMOVAL_REQUEST = "REMOVAL_REQUEST"


class DuplicateDecisionType(str, enum.Enum):
    """Duplicate decision options."""

    IGNORE_DUPLICATE = "IGNORE_DUPLICATE"
    ALLOW_SEPARATE_INSTANCE = "ALLOW_SEPARATE_INSTANCE"


class ToolId(str, enum.Enum):
    """Extraction tool identifiers."""

    DOCLING = "docling"
    UNSTRUCTURED = "unstructured"


class ManifestType(str, enum.Enum):
    """Manifest types."""

    RAW = "raw"
    NORMALIZED = "normalized"
    ENRICHED = "enriched"
    ORIGINAL_SOURCE = "original_source"


class ValidationStatus(str, enum.Enum):
    """Validation result status."""

    PASS = "PASS"
    FAIL = "FAIL"


class FeedbackRating(str, enum.Enum):
    """Feedback rating options."""

    UP = "UP"
    DOWN = "DOWN"


class Tier(str, enum.Enum):
    """User tier levels."""

    FREE = "FREE"
    BASIC = "BASIC"
    PRO = "PRO"


class ScopeType(str, enum.Enum):
    """Source link scope types."""

    USER = "USER"
    GAME = "GAME"


# =============================================================================
# Core Tables (Section 2 of DATABASE_SCHEMA_v1.0.md)
# =============================================================================


class Source(Base):
    """Primary record for each ingested document.

    Reference: DATABASE_SCHEMA_v1.0.md Section 2.1
    """

    __tablename__ = "sources"

    # Primary key: doc_id format is <original_filename>__<sha256>
    doc_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    source_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    current_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[GovernanceStatus] = mapped_column(
        Enum(GovernanceStatus), nullable=False, default=GovernanceStatus.DISCOVERED
    )
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    system_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    game_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    governance_events: Mapped[list["GovernanceEvent"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    manifests: Mapped[list["Manifest"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    validation_reports: Mapped[list["ValidationReport"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    feedback_items: Mapped[list["Feedback"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    source_links: Mapped[list["SourceLink"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sources_status", "status"),
        Index("ix_sources_system_id", "system_id"),
        Index("ix_sources_game_id", "game_id"),
        Index("ix_sources_owner_user_id", "owner_user_id"),
    )


class GovernanceEvent(Base):
    """Immutable event log for governance state transitions.

    Reference: DATABASE_SCHEMA_v1.0.md Section 2.2
    """

    __tablename__ = "governance_events"

    event_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    doc_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("sources.doc_id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    to_status: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType), nullable=False, default=EventType.STATUS_CHANGE
    )
    triggered_by: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    source: Mapped["Source"] = relationship(back_populates="governance_events")

    __table_args__ = (Index("ix_governance_events_doc_id", "doc_id"),)


class DuplicateDecision(Base):
    """Admin decisions for duplicate detection.

    Reference: DATABASE_SCHEMA_v1.0.md Section 2.3
    """

    __tablename__ = "duplicate_decisions"

    doc_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("sources.doc_id", ondelete="CASCADE"), primary_key=True
    )
    decision: Mapped[DuplicateDecisionType] = mapped_column(
        Enum(DuplicateDecisionType), nullable=False
    )
    decided_by: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# =============================================================================
# Artifact Metadata (Section 3 of DATABASE_SCHEMA_v1.0.md)
# =============================================================================


class Manifest(Base):
    """Metadata about manifests stored on disk.

    Reference: DATABASE_SCHEMA_v1.0.md Section 3.1
    """

    __tablename__ = "manifests"

    manifest_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    doc_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("sources.doc_id", ondelete="CASCADE"), nullable=False
    )
    tool_id: Mapped[ToolId] = mapped_column(Enum(ToolId), nullable=False)
    manifest_type: Mapped[ManifestType] = mapped_column(Enum(ManifestType), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    run_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    source: Mapped["Source"] = relationship(back_populates="manifests")

    __table_args__ = (
        Index("ix_manifests_doc_id", "doc_id"),
        Index("ix_manifests_tool_id", "tool_id"),
        Index("ix_manifests_manifest_type", "manifest_type"),
    )


class Chunk(Base):
    """Chunk records for retrieval.

    Reference: DATABASE_SCHEMA_v1.0.md Section 3.2
    """

    __tablename__ = "chunks"

    chunk_id: Mapped[str] = mapped_column(Text, primary_key=True)
    doc_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("sources.doc_id", ondelete="CASCADE"), nullable=False
    )
    tool_id: Mapped[ToolId] = mapped_column(Enum(ToolId), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    section_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    source: Mapped["Source"] = relationship(back_populates="chunks")
    embedding: Mapped[Optional["Embedding"]] = relationship(
        back_populates="chunk", cascade="all, delete-orphan", uselist=False
    )
    fts_entry: Mapped[Optional["FTSIndex"]] = relationship(
        back_populates="chunk", cascade="all, delete-orphan", uselist=False
    )
    feedback_items: Mapped[list["Feedback"]] = relationship(
        back_populates="chunk", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("doc_id", "tool_id", "chunk_sha256", name="uq_chunk_identity"),
        Index("ix_chunks_doc_id", "doc_id"),
        Index("ix_chunks_tool_id", "tool_id"),
        Index("ix_chunks_system_id", "system_id"),
        Index("ix_chunks_active", "active"),
    )


class Embedding(Base):
    """Vector embeddings per chunk.

    Reference: DATABASE_SCHEMA_v1.0.md Section 3.3
    """

    __tablename__ = "embeddings"

    chunk_id: Mapped[str] = mapped_column(
        Text, ForeignKey("chunks.chunk_id", ondelete="CASCADE"), primary_key=True
    )
    embedding: Mapped[list] = mapped_column(Vector(384), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    chunk: Mapped["Chunk"] = relationship(back_populates="embedding")


class FTSIndex(Base):
    """Full-text search index support.

    Reference: DATABASE_SCHEMA_v1.0.md Section 3.4
    """

    __tablename__ = "fts_index"

    chunk_id: Mapped[str] = mapped_column(
        Text, ForeignKey("chunks.chunk_id", ondelete="CASCADE"), primary_key=True
    )
    tsv: Mapped[str] = mapped_column(TSVECTOR, nullable=False)

    # Relationships
    chunk: Mapped["Chunk"] = relationship(back_populates="fts_entry")

    __table_args__ = (Index("ix_fts_index_tsv", "tsv", postgresql_using="gin"),)


# =============================================================================
# Validation (Section 4 of DATABASE_SCHEMA_v1.0.md)
# =============================================================================


class ValidationReport(Base):
    """Metadata for validation reports on disk.

    Reference: DATABASE_SCHEMA_v1.0.md Section 4.1
    """

    __tablename__ = "validation_reports"

    report_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    doc_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("sources.doc_id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ValidationStatus] = mapped_column(Enum(ValidationStatus), nullable=False)
    report_path: Mapped[str] = mapped_column(Text, nullable=False)
    report_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    source: Mapped["Source"] = relationship(back_populates="validation_reports")

    __table_args__ = (Index("ix_validation_reports_doc_id", "doc_id"),)


# =============================================================================
# Query and Feedback (Section 5 of DATABASE_SCHEMA_v1.0.md)
# =============================================================================


class Feedback(Base):
    """User feedback per chunk.

    Reference: DATABASE_SCHEMA_v1.0.md Section 5.1
    """

    __tablename__ = "feedback"

    feedback_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    doc_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("sources.doc_id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[str] = mapped_column(
        Text, ForeignKey("chunks.chunk_id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[FeedbackRating] = mapped_column(Enum(FeedbackRating), nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    source: Mapped["Source"] = relationship(back_populates="feedback_items")
    chunk: Mapped["Chunk"] = relationship(back_populates="feedback_items")

    __table_args__ = (
        Index("ix_feedback_chunk_id", "chunk_id"),
        Index("ix_feedback_user_id", "user_id"),
    )


class TierLimit(Base):
    """Tier limit definitions.

    Reference: DATABASE_SCHEMA_v1.0.md Section 5.2
    """

    __tablename__ = "tier_limits"

    tier: Mapped[Tier] = mapped_column(Enum(Tier), primary_key=True)
    max_sources: Mapped[int] = mapped_column(Integer, nullable=False)
    max_active_sources: Mapped[int] = mapped_column(Integer, nullable=False)
    max_games: Mapped[int] = mapped_column(Integer, nullable=False)
    max_storage_mb: Mapped[int] = mapped_column(Integer, nullable=False)


class AccountTier(Base):
    """Assigned tier per user.

    Reference: DATABASE_SCHEMA_v1.0.md Section 5.3
    """

    __tablename__ = "account_tiers"

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    tier: Mapped[Tier] = mapped_column(Enum(Tier), nullable=False, default=Tier.FREE)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# =============================================================================
# Access and Scope (Section 6 of DATABASE_SCHEMA_v1.0.md)
# =============================================================================


class SourceLink(Base):
    """Additional access grants beyond primary ownership.

    Reference: DATABASE_SCHEMA_v1.0.md Section 6.1
    """

    __tablename__ = "source_links"

    link_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    doc_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("sources.doc_id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[ScopeType] = mapped_column(Enum(ScopeType), nullable=False)
    owner_user_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    game_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gm_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    source: Mapped["Source"] = relationship(back_populates="source_links")

    __table_args__ = (
        Index("ix_source_links_doc_id", "doc_id"),
        Index("ix_source_links_owner_user_id", "owner_user_id"),
        Index("ix_source_links_game_id", "game_id"),
    )
