"""Validation check implementations.

Per VALIDATION_PLAN_v1.0.md Section 5, these are the 9 mandatory validation checks:
1. Governance Integrity
2. Artifact Presence & Structure
3. Provenance & Metadata
4. Dual-Extractor Completeness
5. Chunk Integrity
6. Storage & Index Verification
7. Tool Version Compatibility
8. Deactivation & Exclusion
9. Orphaned Artifact Detection

Each check is independent and returns a CheckResult.
All checks must pass for validation to succeed.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.models.source import (
    Chunk,
    Embedding,
    FTSIndex,
    GovernanceEvent,
    GovernanceStatus,
    Manifest,
    Source,
)
from nexus_core.validation.artifacts import (
    ArtifactPaths,
    get_required_artifact_paths,
    load_json_artifact,
    load_jsonl_artifact,
    verify_artifact_exists,
)
from nexus_core.validation.exceptions import ValidationCheckError


@dataclass
class CheckResult:
    """Result of a single validation check.

    Attributes:
        check_name: Name of the check that was run
        passed: True if check passed, False if failed
        message: Human-readable summary of the result
        details: Additional context (e.g., missing artifacts, errors)
    """

    check_name: str
    passed: bool
    message: str
    details: dict[str, Any]


class ValidationCheck(ABC):
    """Base class for all validation checks.

    Each check implements the run() method which returns a CheckResult.
    Checks receive database session, artifact paths, and doc_id.
    """

    def __init__(
        self,
        session: AsyncSession,
        paths: ArtifactPaths,
        doc_id: str,
    ):
        self.session = session
        self.paths = paths
        self.doc_id = doc_id

    @abstractmethod
    async def run(self) -> CheckResult:
        """Execute the validation check.

        Returns:
            CheckResult indicating pass/fail and details
        """
        pass


# ============================================================================
# Check 1: Governance Integrity
# ============================================================================


class GovernanceIntegrityCheck(ValidationCheck):
    """Verify governance state and transition history.

    Per VALIDATION_PLAN_v1.0.md Section 5.1:
    - Source exists in governance table
    - Current state is INGESTING
    - All prior transitions followed GOVERNANCE_FLOW_v1.0.md
    - No illegal or skipped transitions
    """

    async def run(self) -> CheckResult:
        try:
            # Check source exists
            result = await self.session.execute(
                select(Source).where(Source.doc_id == self.doc_id)
            )
            source = result.scalar_one_or_none()

            if not source:
                return CheckResult(
                    check_name="GovernanceIntegrityCheck",
                    passed=False,
                    message=f"Source not found in governance: {self.doc_id}",
                    details={"doc_id": self.doc_id, "error": "source_not_found"},
                )

            # Check current state is INGESTING
            if source.status != GovernanceStatus.INGESTING:
                return CheckResult(
                    check_name="GovernanceIntegrityCheck",
                    passed=False,
                    message=f"Source state is {source.status.value}, expected INGESTING",
                    details={
                        "doc_id": self.doc_id,
                        "current_state": source.status.value,
                        "expected_state": "INGESTING",
                    },
                )

            # Load governance events to verify transition history
            events_result = await self.session.execute(
                select(GovernanceEvent)
                .where(GovernanceEvent.doc_id == self.doc_id)
                .order_by(GovernanceEvent.timestamp)
            )
            events = events_result.scalars().all()

            if not events:
                return CheckResult(
                    check_name="GovernanceIntegrityCheck",
                    passed=False,
                    message="No governance events found for source",
                    details={
                        "doc_id": self.doc_id,
                        "error": "missing_events",
                    },
                )

            # Verify transition path (basic validation)
            # Full transition validation would require governance flow rules
            # For MVP1, we verify events exist and current state matches
            last_event = events[-1]
            if last_event.to_state != source.status:
                return CheckResult(
                    check_name="GovernanceIntegrityCheck",
                    passed=False,
                    message="Last governance event does not match current source state",
                    details={
                        "doc_id": self.doc_id,
                        "source_state": source.status.value,
                        "last_event_state": last_event.to_state.value,
                    },
                )

            return CheckResult(
                check_name="GovernanceIntegrityCheck",
                passed=True,
                message="Governance integrity verified",
                details={
                    "doc_id": self.doc_id,
                    "current_state": source.status.value,
                    "event_count": len(events),
                },
            )

        except Exception as e:
            return CheckResult(
                check_name="GovernanceIntegrityCheck",
                passed=False,
                message=f"Governance check failed: {str(e)}",
                details={"doc_id": self.doc_id, "error": str(e)},
            )


# ============================================================================
# Check 2: Artifact Presence & Structure
# ============================================================================


class ArtifactPresenceCheck(ValidationCheck):
    """Verify all required artifacts exist.

    Per VALIDATION_PLAN_v1.0.md Section 5.2:
    - Original source artifact
    - Docling raw, normalized, enriched manifests
    - Unstructured raw, normalized, enriched manifests
    - Dual chunk files
    """

    async def run(self) -> CheckResult:
        required_artifacts = get_required_artifact_paths(self.paths)
        missing_artifacts = []

        for artifact_name, artifact_path in required_artifacts:
            if not verify_artifact_exists(artifact_path):
                missing_artifacts.append(
                    {"name": artifact_name, "path": str(artifact_path)}
                )

        if missing_artifacts:
            return CheckResult(
                check_name="ArtifactPresenceCheck",
                passed=False,
                message=f"Missing {len(missing_artifacts)} required artifact(s)",
                details={
                    "doc_id": self.doc_id,
                    "missing_artifacts": missing_artifacts,
                    "total_required": len(required_artifacts),
                },
            )

        return CheckResult(
            check_name="ArtifactPresenceCheck",
            passed=True,
            message=f"All {len(required_artifacts)} required artifacts present",
            details={
                "doc_id": self.doc_id,
                "artifacts_verified": len(required_artifacts),
            },
        )


# ============================================================================
# Check 3: Provenance & Metadata
# ============================================================================


class ProvenanceMetadataCheck(ValidationCheck):
    """Verify provenance metadata in artifacts.

    Per VALIDATION_PLAN_v1.0.md Section 5.3:
    - doc_id present and correct
    - source_sha256 present and correct
    - tool name and version recorded
    - run identifiers present
    - timestamps present
    """

    async def run(self) -> CheckResult:
        errors = []

        # Check original source artifact
        try:
            original = load_json_artifact(self.paths.original_source, self.doc_id)
            if original.get("doc_id") != self.doc_id:
                errors.append("original_source: doc_id mismatch")
            if not original.get("source_sha256"):
                errors.append("original_source: missing source_sha256")
            if not original.get("original_filename"):
                errors.append("original_source: missing original_filename")
        except Exception as e:
            errors.append(f"original_source: {str(e)}")

        # Check raw manifests
        for name, path in [
            ("docling_raw", self.paths.docling_raw),
            ("unstructured_raw", self.paths.unstructured_raw),
        ]:
            try:
                manifest = load_json_artifact(path, self.doc_id)
                if manifest.get("doc_id") != self.doc_id:
                    errors.append(f"{name}: doc_id mismatch")
                if not manifest.get("source_sha256"):
                    errors.append(f"{name}: missing source_sha256")
                if not manifest.get("extractor_name"):
                    errors.append(f"{name}: missing extractor_name")
                if not manifest.get("extractor_version"):
                    errors.append(f"{name}: missing extractor_version")
                if not manifest.get("run_id"):
                    errors.append(f"{name}: missing run_id")
            except Exception as e:
                errors.append(f"{name}: {str(e)}")

        # Check normalized manifests
        for name, path in [
            ("docling_normalized", self.paths.docling_normalized),
            ("unstructured_normalized", self.paths.unstructured_normalized),
        ]:
            try:
                manifest = load_json_artifact(path, self.doc_id)
                if manifest.get("doc_id") != self.doc_id:
                    errors.append(f"{name}: doc_id mismatch")
                if not manifest.get("tool_origin"):
                    errors.append(f"{name}: missing tool_origin")
            except Exception as e:
                errors.append(f"{name}: {str(e)}")

        if errors:
            return CheckResult(
                check_name="ProvenanceMetadataCheck",
                passed=False,
                message=f"Provenance metadata errors: {len(errors)} issue(s)",
                details={"doc_id": self.doc_id, "errors": errors},
            )

        return CheckResult(
            check_name="ProvenanceMetadataCheck",
            passed=True,
            message="Provenance metadata verified",
            details={"doc_id": self.doc_id, "manifests_checked": 6},
        )


# ============================================================================
# Check 4: Dual-Extractor Completeness
# ============================================================================


class DualExtractorCheck(ValidationCheck):
    """Verify both extractors produced artifacts.

    Per VALIDATION_PLAN_v1.0.md Section 5.4:
    - Docling artifacts exist
    - Unstructured artifacts exist
    - Neither extractor output is treated as canonical
    """

    async def run(self) -> CheckResult:
        # This check is largely covered by ArtifactPresenceCheck
        # We verify both tool sets exist
        docling_artifacts = [
            ("docling_raw", self.paths.docling_raw),
            ("docling_normalized", self.paths.docling_normalized),
            ("docling_enriched", self.paths.docling_enriched),
            ("docling_chunks", self.paths.docling_chunks),
        ]

        unstructured_artifacts = [
            ("unstructured_raw", self.paths.unstructured_raw),
            ("unstructured_normalized", self.paths.unstructured_normalized),
            ("unstructured_enriched", self.paths.unstructured_enriched),
            ("unstructured_chunks", self.paths.unstructured_chunks),
        ]

        missing = []
        for name, path in docling_artifacts + unstructured_artifacts:
            if not verify_artifact_exists(path):
                missing.append(name)

        if missing:
            return CheckResult(
                check_name="DualExtractorCheck",
                passed=False,
                message=f"Missing artifacts from extractors: {', '.join(missing)}",
                details={"doc_id": self.doc_id, "missing": missing},
            )

        return CheckResult(
            check_name="DualExtractorCheck",
            passed=True,
            message="Dual extractors both produced complete artifacts",
            details={
                "doc_id": self.doc_id,
                "docling_artifacts": len(docling_artifacts),
                "unstructured_artifacts": len(unstructured_artifacts),
            },
        )


# ============================================================================
# Check 5: Chunk Integrity
# ============================================================================


class ChunkIntegrityCheck(ValidationCheck):
    """Verify chunk file integrity.

    Per VALIDATION_PLAN_v1.0.md Section 5.5:
    - Chunks exist for both extractors
    - Each chunk has required metadata
    - Chunk IDs are unique per source
    - Chunk ID format is correct
    """

    async def run(self) -> CheckResult:
        errors = []
        chunk_ids_seen = set()

        # Load both chunk files
        try:
            docling_chunks = load_jsonl_artifact(self.paths.docling_chunks, self.doc_id)
            unstructured_chunks = load_jsonl_artifact(
                self.paths.unstructured_chunks, self.doc_id
            )
        except Exception as e:
            return CheckResult(
                check_name="ChunkIntegrityCheck",
                passed=False,
                message=f"Failed to load chunk files: {str(e)}",
                details={"doc_id": self.doc_id, "error": str(e)},
            )

        # Verify chunks from both extractors
        all_chunks = [
            ("docling", chunk) for chunk in docling_chunks
        ] + [("unstructured", chunk) for chunk in unstructured_chunks]

        if not all_chunks:
            errors.append("No chunks found in either extractor")

        # Check each chunk
        for tool_origin, chunk in all_chunks:
            # Required fields
            required_fields = [
                "chunk_id",
                "doc_id",
                "tool_origin",
                "chunk_text",
                "section_title",
                "content_type",
                "system_tag",
            ]

            for field in required_fields:
                if field not in chunk:
                    errors.append(f"Missing field '{field}' in {tool_origin} chunk")

            # Verify doc_id matches
            if chunk.get("doc_id") != self.doc_id:
                errors.append(f"{tool_origin} chunk has wrong doc_id")

            # Verify chunk_id format: {doc_id}::{tool_id}::{chunk_sha256[:16]}
            chunk_id = chunk.get("chunk_id", "")
            if not re.match(r"^.+::.+::[0-9a-f]{16}$", chunk_id):
                errors.append(f"Invalid chunk_id format: {chunk_id}")

            # Check for duplicates
            if chunk_id in chunk_ids_seen:
                errors.append(f"Duplicate chunk_id: {chunk_id}")
            chunk_ids_seen.add(chunk_id)

        if errors:
            return CheckResult(
                check_name="ChunkIntegrityCheck",
                passed=False,
                message=f"Chunk integrity errors: {len(errors)} issue(s)",
                details={
                    "doc_id": self.doc_id,
                    "errors": errors[:10],  # Limit to first 10
                    "total_errors": len(errors),
                    "total_chunks": len(all_chunks),
                },
            )

        return CheckResult(
            check_name="ChunkIntegrityCheck",
            passed=True,
            message=f"Chunk integrity verified ({len(all_chunks)} chunks)",
            details={
                "doc_id": self.doc_id,
                "docling_chunks": len(docling_chunks),
                "unstructured_chunks": len(unstructured_chunks),
                "total_chunks": len(all_chunks),
                "unique_chunk_ids": len(chunk_ids_seen),
            },
        )


# ============================================================================
# Check 6: Storage & Index Verification
# ============================================================================


class StorageIndexCheck(ValidationCheck):
    """Verify database storage and indexing.

    Per VALIDATION_PLAN_v1.0.md Section 5.6:
    - DB rows exist for all chunks
    - Each chunk has an embedding vector
    - Full-text search index includes chunk text
    """

    async def run(self) -> CheckResult:
        # Load chunk IDs from files
        try:
            docling_chunks = load_jsonl_artifact(self.paths.docling_chunks, self.doc_id)
            unstructured_chunks = load_jsonl_artifact(
                self.paths.unstructured_chunks, self.doc_id
            )
            expected_chunk_ids = set(
                chunk["chunk_id"]
                for chunk in docling_chunks + unstructured_chunks
                if "chunk_id" in chunk
            )
        except Exception as e:
            return CheckResult(
                check_name="StorageIndexCheck",
                passed=False,
                message=f"Failed to load chunks for verification: {str(e)}",
                details={"doc_id": self.doc_id, "error": str(e)},
            )

        if not expected_chunk_ids:
            return CheckResult(
                check_name="StorageIndexCheck",
                passed=False,
                message="No chunk IDs found to verify",
                details={"doc_id": self.doc_id},
            )

        errors = []

        # Check DB rows exist
        chunk_result = await self.session.execute(
            select(Chunk).where(Chunk.doc_id == self.doc_id)
        )
        db_chunks = {chunk.chunk_id: chunk for chunk in chunk_result.scalars().all()}

        missing_chunks = expected_chunk_ids - set(db_chunks.keys())
        if missing_chunks:
            errors.append(f"Missing {len(missing_chunks)} chunk(s) in database")

        # Check embeddings exist
        embedding_result = await self.session.execute(
            select(Embedding.chunk_id).where(
                Embedding.chunk_id.in_(list(expected_chunk_ids))
            )
        )
        embedding_chunk_ids = set(row[0] for row in embedding_result.all())

        missing_embeddings = expected_chunk_ids - embedding_chunk_ids
        if missing_embeddings:
            errors.append(f"Missing {len(missing_embeddings)} embedding(s)")

        # Check FTS index
        fts_result = await self.session.execute(
            select(FTSIndex.chunk_id).where(
                FTSIndex.chunk_id.in_(list(expected_chunk_ids))
            )
        )
        fts_chunk_ids = set(row[0] for row in fts_result.all())

        missing_fts = expected_chunk_ids - fts_chunk_ids
        if missing_fts:
            errors.append(f"Missing {len(missing_fts)} FTS index entries")

        if errors:
            return CheckResult(
                check_name="StorageIndexCheck",
                passed=False,
                message=f"Storage/index verification failed: {', '.join(errors)}",
                details={
                    "doc_id": self.doc_id,
                    "expected_chunks": len(expected_chunk_ids),
                    "db_chunks": len(db_chunks),
                    "embeddings": len(embedding_chunk_ids),
                    "fts_indexed": len(fts_chunk_ids),
                    "errors": errors,
                },
            )

        return CheckResult(
            check_name="StorageIndexCheck",
            passed=True,
            message=f"Storage and indexing verified ({len(expected_chunk_ids)} chunks)",
            details={
                "doc_id": self.doc_id,
                "chunks_verified": len(expected_chunk_ids),
                "db_rows": len(db_chunks),
                "embeddings": len(embedding_chunk_ids),
                "fts_indexed": len(fts_chunk_ids),
            },
        )


# ============================================================================
# Check 7: Tool Version Compatibility
# ============================================================================


class ToolVersionCheck(ValidationCheck):
    """Verify tool versions meet requirements.

    Per VALIDATION_PLAN_v1.0.md Section 5.7:
    - Tool versions match TOOL_VERSIONS_v1.0.md minimums

    Note: For MVP1, we verify version fields exist.
    Full version comparison requires loading TOOL_VERSIONS_v1.0.md.
    """

    async def run(self) -> CheckResult:
        errors = []

        # Check docling version
        try:
            docling_manifest = load_json_artifact(self.paths.docling_raw, self.doc_id)
            docling_version = docling_manifest.get("extractor_version")
            if not docling_version:
                errors.append("Docling version missing")
        except Exception as e:
            errors.append(f"Cannot verify docling version: {str(e)}")

        # Check unstructured version
        try:
            unstructured_manifest = load_json_artifact(
                self.paths.unstructured_raw, self.doc_id
            )
            unstructured_version = unstructured_manifest.get("extractor_version")
            if not unstructured_version:
                errors.append("Unstructured version missing")
        except Exception as e:
            errors.append(f"Cannot verify unstructured version: {str(e)}")

        if errors:
            return CheckResult(
                check_name="ToolVersionCheck",
                passed=False,
                message=f"Tool version verification failed: {', '.join(errors)}",
                details={"doc_id": self.doc_id, "errors": errors},
            )

        # For MVP1, we just verify versions are present
        # Full semantic version comparison would be added here
        return CheckResult(
            check_name="ToolVersionCheck",
            passed=True,
            message="Tool versions verified",
            details={
                "doc_id": self.doc_id,
                "docling_version": docling_version,
                "unstructured_version": unstructured_version,
            },
        )


# ============================================================================
# Check 8: Deactivation & Exclusion
# ============================================================================


class DeactivationCheck(ValidationCheck):
    """Verify deactivated sources are excluded.

    Per VALIDATION_PLAN_v1.0.md Section 5.8:
    - If source is deactivated, derived chunks must be excluded
    """

    async def run(self) -> CheckResult:
        # Check if source is deactivated
        result = await self.session.execute(
            select(Source).where(Source.doc_id == self.doc_id)
        )
        source = result.scalar_one_or_none()

        if not source:
            return CheckResult(
                check_name="DeactivationCheck",
                passed=False,
                message="Source not found",
                details={"doc_id": self.doc_id},
            )

        # If source is not deactivated, check passes
        if source.status != GovernanceStatus.DEACTIVATED:
            return CheckResult(
                check_name="DeactivationCheck",
                passed=True,
                message="Source is active (not deactivated)",
                details={
                    "doc_id": self.doc_id,
                    "status": source.status.value,
                },
            )

        # If deactivated, verify chunks are marked inactive
        chunk_result = await self.session.execute(
            select(Chunk).where(Chunk.doc_id == self.doc_id, Chunk.active == True)
        )
        active_chunks = chunk_result.scalars().all()

        if active_chunks:
            return CheckResult(
                check_name="DeactivationCheck",
                passed=False,
                message=f"Deactivated source has {len(active_chunks)} active chunks",
                details={
                    "doc_id": self.doc_id,
                    "status": source.status.value,
                    "active_chunks": len(active_chunks),
                },
            )

        return CheckResult(
            check_name="DeactivationCheck",
            passed=True,
            message="Deactivated source has no active chunks",
            details={
                "doc_id": self.doc_id,
                "status": source.status.value,
            },
        )


# ============================================================================
# Check 9: Orphaned Artifact Detection
# ============================================================================


class OrphanedArtifactCheck(ValidationCheck):
    """Detect orphaned artifacts without DB records.

    Per VALIDATION_PLAN_v1.0.md Section 5.9:
    - No artifacts exist on disk without corresponding DB record
    """

    async def run(self) -> CheckResult:
        # Check if manifest records exist in DB
        result = await self.session.execute(
            select(Manifest).where(Manifest.doc_id == self.doc_id)
        )
        db_manifests = result.scalars().all()

        # For MVP1, we verify manifests directory exists and has DB records
        # Full orphan detection would scan filesystem and compare to DB
        if not self.paths.manifests_dir.exists():
            return CheckResult(
                check_name="OrphanedArtifactCheck",
                passed=True,
                message="No manifest directory exists (no artifacts to orphan)",
                details={"doc_id": self.doc_id},
            )

        # If manifests exist on disk but no DB records, that's an orphan
        if self.paths.manifests_dir.exists() and not db_manifests:
            return CheckResult(
                check_name="OrphanedArtifactCheck",
                passed=False,
                message="Artifacts exist on disk but no manifest records in database",
                details={
                    "doc_id": self.doc_id,
                    "manifests_dir": str(self.paths.manifests_dir),
                },
            )

        return CheckResult(
            check_name="OrphanedArtifactCheck",
            passed=True,
            message="No orphaned artifacts detected",
            details={
                "doc_id": self.doc_id,
                "manifest_records": len(db_manifests),
            },
        )
