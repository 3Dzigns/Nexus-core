"""Tests for validation artifact loading and path resolution.

Tests ARTIFACT_CONTRACT_v1.0.md Section 3 compliance.
"""

import pytest
from pathlib import Path

from nexus_core.validation.artifacts import (
    get_artifact_structure,
    verify_artifact_exists,
    load_json_artifact,
    load_jsonl_artifact,
    get_required_artifact_paths,
    ArtifactNotFoundError,
)


class TestArtifactPathResolution:
    """Test artifact path resolution per ARTIFACT_CONTRACT_v1.0.md."""

    def test_get_artifact_structure_paths(self, tmp_path):
        """Test that artifact structure resolves correct paths."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        # Verify base paths
        assert paths.doc_id == doc_id
        assert paths.transfer_station_root == tmp_path

        # Verify manifest paths
        assert str(paths.manifests_dir) == str(tmp_path / "artifacts" / "manifests" / doc_id)
        assert str(paths.raw_dir) == str(tmp_path / "artifacts" / "manifests" / doc_id / "raw")
        assert str(paths.normalized_dir) == str(tmp_path / "artifacts" / "manifests" / doc_id / "normalized")
        assert str(paths.enriched_dir) == str(tmp_path / "artifacts" / "manifests" / doc_id / "enriched")

        # Verify chunk paths
        assert str(paths.chunks_dir) == str(tmp_path / "artifacts" / "chunks" / doc_id)
        assert str(paths.docling_chunks) == str(tmp_path / "artifacts" / "chunks" / doc_id / "docling_chunks.jsonl")

    def test_get_required_artifact_paths_list(self, tmp_path):
        """Test that all required artifacts are listed."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(tmp_path))

        required = get_required_artifact_paths(paths)

        # Should have 9 required artifacts per ARTIFACT_CONTRACT_v1.0.md
        assert len(required) == 9

        artifact_names = [name for name, _ in required]
        expected_names = [
            "original_source",
            "docling_raw_manifest",
            "unstructured_raw_manifest",
            "docling_normalized_manifest",
            "unstructured_normalized_manifest",
            "docling_enriched_manifest",
            "unstructured_enriched_manifest",
            "docling_chunks",
            "unstructured_chunks",
        ]

        for expected in expected_names:
            assert expected in artifact_names


class TestArtifactExistence:
    """Test artifact file existence checks."""

    def test_verify_artifact_exists_when_present(self, tmp_path):
        """Test that existing artifact is detected."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"key": "value"}')

        assert verify_artifact_exists(test_file) is True

    def test_verify_artifact_exists_when_missing(self, tmp_path):
        """Test that missing artifact is detected."""
        test_file = tmp_path / "nonexistent.json"

        assert verify_artifact_exists(test_file) is False

    def test_verify_artifact_exists_directory_returns_false(self, tmp_path):
        """Test that directories are not considered artifacts."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        assert verify_artifact_exists(test_dir) is False


class TestJSONArtifactLoading:
    """Test JSON artifact loading."""

    def test_load_json_artifact_success(self, tmp_path):
        """Test loading valid JSON artifact."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"doc_id": "test_doc", "key": "value"}')

        result = load_json_artifact(test_file, "test_doc")

        assert result["doc_id"] == "test_doc"
        assert result["key"] == "value"

    def test_load_json_artifact_not_found(self, tmp_path):
        """Test loading nonexistent artifact raises error."""
        test_file = tmp_path / "nonexistent.json"

        with pytest.raises(ArtifactNotFoundError) as exc_info:
            load_json_artifact(test_file, "test_doc")

        assert "test_doc" in str(exc_info.value)
        assert str(test_file) in exc_info.value.artifact_path

    def test_load_json_artifact_invalid_json(self, tmp_path):
        """Test loading invalid JSON raises error."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text('{"invalid": json}')  # Invalid JSON

        from nexus_core.validation.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            load_json_artifact(test_file, "test_doc")

        assert "parse" in str(exc_info.value).lower()


class TestJSONLArtifactLoading:
    """Test JSONL (JSON Lines) artifact loading."""

    def test_load_jsonl_artifact_success(self, tmp_path):
        """Test loading valid JSONL artifact."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"chunk_id": "c1", "text": "First"}\n'
            '{"chunk_id": "c2", "text": "Second"}\n'
        )

        result = load_jsonl_artifact(test_file, "test_doc")

        assert len(result) == 2
        assert result[0]["chunk_id"] == "c1"
        assert result[1]["chunk_id"] == "c2"

    def test_load_jsonl_artifact_with_empty_lines(self, tmp_path):
        """Test loading JSONL with empty lines (should skip)."""
        test_file = tmp_path / "test.jsonl"
        test_file.write_text(
            '{"chunk_id": "c1"}\n'
            '\n'  # Empty line
            '{"chunk_id": "c2"}\n'
        )

        result = load_jsonl_artifact(test_file, "test_doc")

        # Should only load non-empty lines
        assert len(result) == 2

    def test_load_jsonl_artifact_not_found(self, tmp_path):
        """Test loading nonexistent JSONL raises error."""
        test_file = tmp_path / "nonexistent.jsonl"

        with pytest.raises(ArtifactNotFoundError):
            load_jsonl_artifact(test_file, "test_doc")

    def test_load_jsonl_artifact_invalid_line(self, tmp_path):
        """Test loading JSONL with invalid line raises error."""
        test_file = tmp_path / "invalid.jsonl"
        test_file.write_text(
            '{"chunk_id": "c1"}\n'
            '{invalid json}\n'
        )

        from nexus_core.validation.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            load_jsonl_artifact(test_file, "test_doc")

        assert "line 2" in str(exc_info.value).lower()


class TestArtifactLoadingIntegration:
    """Integration tests with real fixture artifacts."""

    @pytest.fixture
    def fixture_path(self):
        """Path to test fixtures."""
        return Path(__file__).parent / "fixtures" / "validation" / "good_source"

    def test_load_all_good_source_artifacts(self, fixture_path):
        """Test loading all artifacts from good_source fixture."""
        doc_id = "test_doc__abc123"
        paths = get_artifact_structure(doc_id, str(fixture_path.parent.parent.parent))

        # Adjust paths to fixtures location
        paths.manifests_dir = fixture_path / "manifests" / doc_id
        paths.raw_dir = paths.manifests_dir / "raw"
        paths.normalized_dir = paths.manifests_dir / "normalized"
        paths.enriched_dir = paths.manifests_dir / "enriched"
        paths.chunks_dir = fixture_path / "chunks" / doc_id

        paths.original_source = paths.raw_dir / "original_source.json"
        paths.docling_raw = paths.raw_dir / "docling_manifest.json"
        paths.unstructured_raw = paths.raw_dir / "unstructured_manifest.json"
        paths.docling_normalized = paths.normalized_dir / "docling_normalized.json"
        paths.unstructured_normalized = paths.normalized_dir / "unstructured_normalized.json"
        paths.docling_enriched = paths.enriched_dir / "docling_enriched.json"
        paths.unstructured_enriched = paths.enriched_dir / "unstructured_enriched.json"
        paths.docling_chunks = paths.chunks_dir / "docling_chunks.jsonl"
        paths.unstructured_chunks = paths.chunks_dir / "unstructured_chunks.jsonl"

        # Load original source
        original = load_json_artifact(paths.original_source, doc_id)
        assert original["doc_id"] == doc_id
        assert original["source_sha256"] == "abc123def456"

        # Load raw manifests
        docling_raw = load_json_artifact(paths.docling_raw, doc_id)
        assert docling_raw["extractor_name"] == "docling"

        unstructured_raw = load_json_artifact(paths.unstructured_raw, doc_id)
        assert unstructured_raw["extractor_name"] == "unstructured"

        # Load chunks
        docling_chunks = load_jsonl_artifact(paths.docling_chunks, doc_id)
        assert len(docling_chunks) == 2
        assert all(chunk["tool_origin"] == "docling" for chunk in docling_chunks)

        unstructured_chunks = load_jsonl_artifact(paths.unstructured_chunks, doc_id)
        assert len(unstructured_chunks) == 2
        assert all(chunk["tool_origin"] == "unstructured" for chunk in unstructured_chunks)
