"""Tests for individual validation checks.

Tests each of the 9 mandatory validation checks per VALIDATION_PLAN_v1.0.md Section 5.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from nexus_core.validation.checks import (
    GovernanceIntegrityCheck,
    ArtifactPresenceCheck,
    ProvenanceMetadataCheck,
    DualExtractorCheck,
    ChunkIntegrityCheck,
    StorageIndexCheck,
    ToolVersionCheck,
    DeactivationCheck,
    OrphanedArtifactCheck,
    CheckResult,
)
from nexus_core.validation.artifacts import get_artifact_structure
from nexus_core.models.source import GovernanceStatus, Source
from nexus_core.models.governance import GovernanceEvent


class TestGovernanceIntegrityCheck:
    """Test Check 1: Governance Integrity."""

    @pytest.mark.asyncio
    async def test_pass_when_source_in_ingesting_state(self, async_session):
        """Test that check passes when source is in INGESTING state."""
        doc_id = "test_doc__abc123"

        # Mock source in INGESTING state
        mock_source = MagicMock()
        mock_source.doc_id = doc_id
        mock_source.status = GovernanceStatus.INGESTING

        # Mock query result
        async_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_source)))

        check = GovernanceIntegrityCheck(session=async_session, doc_id=doc_id)
        result = await check.run()

        assert result.passed is True
        assert result.check_name == "GovernanceIntegrityCheck"
        assert "INGESTING" in result.message

    @pytest.mark.asyncio
    async def test_fail_when_source_not_found(self, async_session):
        """Test that check fails when source doesn't exist."""
        doc_id = "nonexistent_doc"

        # Mock no source found
        async_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        check = GovernanceIntegrityCheck(session=async_session, doc_id=doc_id)
        result = await check.run()

        assert result.passed is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_fail_when_source_in_wrong_state(self, async_session):
        """Test that check fails when source is not in INGESTING state."""
        doc_id = "test_doc__abc123"

        # Mock source in PENDING_APPROVAL state
        mock_source = MagicMock()
        mock_source.doc_id = doc_id
        mock_source.status = GovernanceStatus.PENDING_APPROVAL

        async_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_source)))

        check = GovernanceIntegrityCheck(session=async_session, doc_id=doc_id)
        result = await check.run()

        assert result.passed is False
        assert "INGESTING" in result.message


class TestArtifactPresenceCheck:
    """Test Check 2: Artifact Presence & Structure."""

    @pytest.mark.asyncio
    async def test_pass_when_all_artifacts_exist(self, tmp_path):
        """Test that check passes when all required artifacts exist."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        # Create all required artifacts
        paths.manifests_dir.mkdir(parents=True, exist_ok=True)
        paths.raw_dir.mkdir(parents=True, exist_ok=True)
        paths.normalized_dir.mkdir(parents=True, exist_ok=True)
        paths.enriched_dir.mkdir(parents=True, exist_ok=True)
        paths.chunks_dir.mkdir(parents=True, exist_ok=True)

        paths.original_source.write_text('{}')
        paths.docling_raw.write_text('{}')
        paths.unstructured_raw.write_text('{}')
        paths.docling_normalized.write_text('{}')
        paths.unstructured_normalized.write_text('{}')
        paths.docling_enriched.write_text('{}')
        paths.unstructured_enriched.write_text('{}')
        paths.docling_chunks.write_text('')
        paths.unstructured_chunks.write_text('')

        check = ArtifactPresenceCheck(artifact_paths=paths)
        result = await check.run()

        assert result.passed is True
        assert "9/9 artifacts present" in result.message

    @pytest.mark.asyncio
    async def test_fail_when_artifact_missing(self, tmp_path):
        """Test that check fails when any artifact is missing."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        # Create only some artifacts
        paths.manifests_dir.mkdir(parents=True, exist_ok=True)
        paths.raw_dir.mkdir(parents=True, exist_ok=True)
        paths.original_source.write_text('{}')
        paths.docling_raw.write_text('{}')
        # Missing unstructured_raw and others

        check = ArtifactPresenceCheck(artifact_paths=paths)
        result = await check.run()

        assert result.passed is False
        assert "missing" in result.message.lower()
        assert result.details["missing_count"] > 0


class TestProvenanceMetadataCheck:
    """Test Check 3: Provenance & Metadata."""

    @pytest.mark.asyncio
    async def test_pass_when_all_metadata_present(self, tmp_path):
        """Test that check passes when all required metadata is present."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        # Create artifacts with proper metadata
        paths.manifests_dir.mkdir(parents=True, exist_ok=True)
        paths.raw_dir.mkdir(parents=True, exist_ok=True)

        paths.original_source.write_text('{"doc_id": "test_doc__abc123", "source_sha256": "abc123"}')
        paths.docling_raw.write_text('{"doc_id": "test_doc__abc123", "source_sha256": "abc123", "tool_name": "docling", "tool_version": "2.0.0", "run_id": "run_001"}')
        paths.unstructured_raw.write_text('{"doc_id": "test_doc__abc123", "source_sha256": "abc123", "tool_name": "unstructured", "tool_version": "0.16.0", "run_id": "run_002"}')

        check = ProvenanceMetadataCheck(artifact_paths=paths, doc_id=doc_id)
        result = await check.run()

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_fail_when_doc_id_mismatch(self, tmp_path):
        """Test that check fails when doc_id doesn't match."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        paths.manifests_dir.mkdir(parents=True, exist_ok=True)
        paths.raw_dir.mkdir(parents=True, exist_ok=True)

        # Wrong doc_id in artifact
        paths.original_source.write_text('{"doc_id": "wrong_id", "source_sha256": "abc123"}')

        check = ProvenanceMetadataCheck(artifact_paths=paths, doc_id=doc_id)
        result = await check.run()

        assert result.passed is False
        assert "doc_id" in result.message.lower()


class TestDualExtractorCheck:
    """Test Check 4: Dual-Extractor Completeness."""

    @pytest.mark.asyncio
    async def test_pass_when_both_extractors_present(self, tmp_path):
        """Test that check passes when both extractors produced artifacts."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        # Create both extractor artifacts
        paths.raw_dir.mkdir(parents=True, exist_ok=True)
        paths.chunks_dir.mkdir(parents=True, exist_ok=True)

        paths.docling_raw.write_text('{}')
        paths.unstructured_raw.write_text('{}')
        paths.docling_chunks.write_text('')
        paths.unstructured_chunks.write_text('')

        check = DualExtractorCheck(artifact_paths=paths)
        result = await check.run()

        assert result.passed is True
        assert "both extractors" in result.message.lower()

    @pytest.mark.asyncio
    async def test_fail_when_docling_missing(self, tmp_path):
        """Test that check fails when Docling artifacts are missing."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        # Only unstructured artifacts
        paths.raw_dir.mkdir(parents=True, exist_ok=True)
        paths.chunks_dir.mkdir(parents=True, exist_ok=True)

        paths.unstructured_raw.write_text('{}')
        paths.unstructured_chunks.write_text('')

        check = DualExtractorCheck(artifact_paths=paths)
        result = await check.run()

        assert result.passed is False
        assert "docling" in result.message.lower()


class TestChunkIntegrityCheck:
    """Test Check 5: Chunk Integrity."""

    @pytest.mark.asyncio
    async def test_pass_when_chunks_valid(self, tmp_path):
        """Test that check passes when chunk files are valid."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        paths.chunks_dir.mkdir(parents=True, exist_ok=True)

        # Valid chunks
        paths.docling_chunks.write_text(
            '{"chunk_id": "test_doc__abc123::docling::abc123", "doc_id": "test_doc__abc123", "tool_origin": "docling", "chunk_text": "text", "section_title": "Section", "content_type": "text", "system_tag": "generic"}\n'
        )
        paths.unstructured_chunks.write_text(
            '{"chunk_id": "test_doc__abc123::unstructured::def456", "doc_id": "test_doc__abc123", "tool_origin": "unstructured", "chunk_text": "text", "section_title": "Section", "content_type": "text", "system_tag": "generic"}\n'
        )

        check = ChunkIntegrityCheck(artifact_paths=paths, doc_id=doc_id)
        result = await check.run()

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_fail_when_duplicate_chunk_ids(self, tmp_path):
        """Test that check fails when duplicate chunk IDs exist."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        paths.chunks_dir.mkdir(parents=True, exist_ok=True)

        # Duplicate chunk_id
        paths.docling_chunks.write_text(
            '{"chunk_id": "test_doc__abc123::docling::abc123", "doc_id": "test_doc__abc123", "tool_origin": "docling", "chunk_text": "text1", "section_title": "S1", "content_type": "text", "system_tag": "generic"}\n'
            '{"chunk_id": "test_doc__abc123::docling::abc123", "doc_id": "test_doc__abc123", "tool_origin": "docling", "chunk_text": "text2", "section_title": "S2", "content_type": "text", "system_tag": "generic"}\n'
        )
        paths.unstructured_chunks.write_text('')

        check = ChunkIntegrityCheck(artifact_paths=paths, doc_id=doc_id)
        result = await check.run()

        assert result.passed is False
        assert "duplicate" in result.message.lower()


class TestStorageIndexCheck:
    """Test Check 6: Storage & Index Verification."""

    @pytest.mark.asyncio
    async def test_pass_when_all_chunks_stored(self, async_session, tmp_path):
        """Test that check passes when all chunks are stored in DB."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        paths.chunks_dir.mkdir(parents=True, exist_ok=True)
        paths.docling_chunks.write_text(
            '{"chunk_id": "test_doc__abc123::docling::abc123", "doc_id": "test_doc__abc123", "tool_origin": "docling", "chunk_text": "text", "section_title": "S", "content_type": "text", "system_tag": "generic"}\n'
        )
        paths.unstructured_chunks.write_text('')

        # Mock database queries
        async_session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=1)))

        check = StorageIndexCheck(session=async_session, artifact_paths=paths, doc_id=doc_id)
        result = await check.run()

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_fail_when_chunks_missing_in_db(self, async_session, tmp_path):
        """Test that check fails when chunks are missing from DB."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        paths.chunks_dir.mkdir(parents=True, exist_ok=True)
        paths.docling_chunks.write_text(
            '{"chunk_id": "test_doc__abc123::docling::abc123", "doc_id": "test_doc__abc123", "tool_origin": "docling", "chunk_text": "text", "section_title": "S", "content_type": "text", "system_tag": "generic"}\n'
        )
        paths.unstructured_chunks.write_text('')

        # Mock no chunks in database
        async_session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=0)))

        check = StorageIndexCheck(session=async_session, artifact_paths=paths, doc_id=doc_id)
        result = await check.run()

        assert result.passed is False
        assert "database" in result.message.lower()


class TestToolVersionCheck:
    """Test Check 7: Tool Version Compatibility."""

    @pytest.mark.asyncio
    async def test_pass_when_versions_meet_requirements(self, tmp_path):
        """Test that check passes when tool versions meet minimums."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        paths.raw_dir.mkdir(parents=True, exist_ok=True)

        # Versions above minimums
        paths.docling_raw.write_text('{"tool_name": "docling", "tool_version": "2.0.0"}')
        paths.unstructured_raw.write_text('{"tool_name": "unstructured", "tool_version": "0.16.0"}')

        check = ToolVersionCheck(artifact_paths=paths)
        result = await check.run()

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_fail_when_version_below_minimum(self, tmp_path):
        """Test that check fails when tool version is below minimum."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        paths.raw_dir.mkdir(parents=True, exist_ok=True)

        # Version below minimum
        paths.docling_raw.write_text('{"tool_name": "docling", "tool_version": "1.0.0"}')
        paths.unstructured_raw.write_text('{"tool_name": "unstructured", "tool_version": "0.10.0"}')

        check = ToolVersionCheck(artifact_paths=paths)
        result = await check.run()

        assert result.passed is False
        assert "version" in result.message.lower()


class TestDeactivationCheck:
    """Test Check 8: Deactivation & Exclusion."""

    @pytest.mark.asyncio
    async def test_pass_when_source_active(self, async_session):
        """Test that check passes when source is active."""
        doc_id = "test_doc__abc123"

        # Mock active source
        mock_source = MagicMock()
        mock_source.doc_id = doc_id
        mock_source.status = GovernanceStatus.INGESTING

        async_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_source)))

        check = DeactivationCheck(session=async_session, doc_id=doc_id)
        result = await check.run()

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_pass_when_deactivated_chunks_inactive(self, async_session):
        """Test that check passes when deactivated source has inactive chunks."""
        doc_id = "test_doc__abc123"

        # Mock deactivated source
        mock_source = MagicMock()
        mock_source.doc_id = doc_id
        mock_source.status = GovernanceStatus.DEACTIVATED

        # Mock all chunks inactive
        async_session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_source),
            scalar=MagicMock(return_value=0)
        ))

        check = DeactivationCheck(session=async_session, doc_id=doc_id)
        result = await check.run()

        assert result.passed is True


class TestOrphanedArtifactCheck:
    """Test Check 9: Orphaned Artifact Detection."""

    @pytest.mark.asyncio
    async def test_pass_when_no_orphans(self, async_session, tmp_path):
        """Test that check passes when all artifacts have DB records."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        paths.manifests_dir.mkdir(parents=True, exist_ok=True)
        paths.raw_dir.mkdir(parents=True, exist_ok=True)

        paths.docling_raw.write_text('{}')
        paths.unstructured_raw.write_text('{}')

        # Mock all artifacts have DB records
        async_session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=2)))

        check = OrphanedArtifactCheck(session=async_session, artifact_paths=paths, doc_id=doc_id)
        result = await check.run()

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_fail_when_orphans_exist(self, async_session, tmp_path):
        """Test that check fails when orphaned artifacts exist."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        paths.manifests_dir.mkdir(parents=True, exist_ok=True)
        paths.raw_dir.mkdir(parents=True, exist_ok=True)

        paths.docling_raw.write_text('{}')
        paths.unstructured_raw.write_text('{}')

        # Mock only 1 artifact in DB (orphan exists)
        async_session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=1)))

        check = OrphanedArtifactCheck(session=async_session, artifact_paths=paths, doc_id=doc_id)
        result = await check.run()

        assert result.passed is False
        assert "orphaned" in result.message.lower()
