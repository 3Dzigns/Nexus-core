"""Artifact loading and path resolution for validation.

Per ARTIFACT_CONTRACT_v1.0.md Section 3:
- All artifacts reside under /transfer_station/artifacts/
- Directory structure is deterministic per doc_id
- Validation relies on file system evidence

This module provides utilities to:
- Resolve artifact paths for a given doc_id
- Load and parse JSON manifest files
- Load and parse JSONL chunk files
- Verify artifact existence
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nexus_core.validation.exceptions import ArtifactNotFoundError


@dataclass
class ArtifactPaths:
    """Resolved artifact paths for a doc_id.

    Per ARTIFACT_CONTRACT_v1.0.md Section 3, this represents
    the complete directory structure for a source's artifacts.
    """

    doc_id: str
    transfer_station_root: Path

    # Manifest directories
    manifests_dir: Path
    raw_dir: Path
    normalized_dir: Path
    enriched_dir: Path

    # Chunk directory
    chunks_dir: Path

    # Assets directory
    assets_dir: Path

    # Reports directory
    reports_dir: Path

    # Raw manifests
    original_source: Path
    docling_raw: Path
    unstructured_raw: Path

    # Normalized manifests
    docling_normalized: Path
    unstructured_normalized: Path

    # Enriched manifests
    docling_enriched: Path
    unstructured_enriched: Path

    # Chunk files
    docling_chunks: Path
    unstructured_chunks: Path


def get_artifact_structure(doc_id: str, transfer_station_path: str) -> ArtifactPaths:
    """Resolve all artifact paths for a doc_id.

    Per ARTIFACT_CONTRACT_v1.0.md Section 3, this builds the expected
    directory structure for validation to verify.

    Args:
        doc_id: Document identifier (format: <filename>__<sha256>)
        transfer_station_path: Root path to transfer station

    Returns:
        ArtifactPaths instance with all resolved paths

    Example:
        >>> paths = get_artifact_structure("test_doc__abc123", "/transfer_station")
        >>> paths.docling_raw
        Path('/transfer_station/artifacts/manifests/test_doc__abc123/raw/docling_manifest.json')
    """
    root = Path(transfer_station_path) / "artifacts"

    manifests_base = root / "manifests" / doc_id
    raw_dir = manifests_base / "raw"
    normalized_dir = manifests_base / "normalized"
    enriched_dir = manifests_base / "enriched"

    chunks_dir = root / "chunks" / doc_id
    assets_dir = root / "assets" / doc_id
    reports_dir = root / "reports" / doc_id

    return ArtifactPaths(
        doc_id=doc_id,
        transfer_station_root=Path(transfer_station_path),
        # Directories
        manifests_dir=manifests_base,
        raw_dir=raw_dir,
        normalized_dir=normalized_dir,
        enriched_dir=enriched_dir,
        chunks_dir=chunks_dir,
        assets_dir=assets_dir,
        reports_dir=reports_dir,
        # Raw manifests
        original_source=raw_dir / "original_source.json",
        docling_raw=raw_dir / "docling_manifest.json",
        unstructured_raw=raw_dir / "unstructured_manifest.json",
        # Normalized manifests
        docling_normalized=normalized_dir / "docling_normalized.json",
        unstructured_normalized=normalized_dir / "unstructured_normalized.json",
        # Enriched manifests
        docling_enriched=enriched_dir / "docling_enriched.json",
        unstructured_enriched=enriched_dir / "unstructured_enriched.json",
        # Chunk files
        docling_chunks=chunks_dir / "docling_chunks.jsonl",
        unstructured_chunks=chunks_dir / "unstructured_chunks.jsonl",
    )


def verify_artifact_exists(path: Path) -> bool:
    """Check if an artifact file exists.

    Args:
        path: Path to artifact file

    Returns:
        True if file exists, False otherwise
    """
    return path.exists() and path.is_file()


def load_json_artifact(path: Path, doc_id: str) -> dict[str, Any]:
    """Load and parse a JSON artifact file.

    Args:
        path: Path to JSON file
        doc_id: Document identifier (for error messages)

    Returns:
        Parsed JSON content as dictionary

    Raises:
        ArtifactNotFoundError: If file does not exist
        ValidationError: If file cannot be parsed as JSON
    """
    if not verify_artifact_exists(path):
        raise ArtifactNotFoundError(
            artifact_path=str(path),
            doc_id=doc_id,
            details={"expected_path": str(path), "exists": False},
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        from nexus_core.validation.exceptions import ValidationError

        raise ValidationError(
            message=f"Failed to parse JSON artifact: {path}",
            details={"path": str(path), "error": str(e), "doc_id": doc_id},
        ) from e
    except Exception as e:
        from nexus_core.validation.exceptions import ValidationError

        raise ValidationError(
            message=f"Failed to read artifact: {path}",
            details={"path": str(path), "error": str(e), "doc_id": doc_id},
        ) from e


def load_jsonl_artifact(path: Path, doc_id: str) -> list[dict[str, Any]]:
    """Load and parse a JSONL (JSON Lines) artifact file.

    JSONL format: One JSON object per line (used for chunks).

    Args:
        path: Path to JSONL file
        doc_id: Document identifier (for error messages)

    Returns:
        List of parsed JSON objects (one per line)

    Raises:
        ArtifactNotFoundError: If file does not exist
        ValidationError: If file cannot be parsed as JSONL
    """
    if not verify_artifact_exists(path):
        raise ArtifactNotFoundError(
            artifact_path=str(path),
            doc_id=doc_id,
            details={"expected_path": str(path), "exists": False},
        )

    try:
        chunks = []
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue  # Skip empty lines
                try:
                    chunks.append(json.loads(line))
                except json.JSONDecodeError as e:
                    from nexus_core.validation.exceptions import ValidationError

                    raise ValidationError(
                        message=f"Failed to parse JSONL line {line_num}: {path}",
                        details={
                            "path": str(path),
                            "line_number": line_num,
                            "error": str(e),
                            "doc_id": doc_id,
                        },
                    ) from e
        return chunks
    except Exception as e:
        if isinstance(e, ArtifactNotFoundError):
            raise
        from nexus_core.validation.exceptions import ValidationError

        if not isinstance(e, ValidationError):
            raise ValidationError(
                message=f"Failed to read JSONL artifact: {path}",
                details={"path": str(path), "error": str(e), "doc_id": doc_id},
            ) from e
        raise


def get_required_artifact_paths(paths: ArtifactPaths) -> list[tuple[str, Path]]:
    """Get list of all required artifacts for validation.

    Per ARTIFACT_CONTRACT_v1.0.md Section 5, all these artifacts
    must exist for validation to pass.

    Args:
        paths: Resolved artifact paths

    Returns:
        List of (artifact_name, path) tuples
    """
    return [
        ("original_source", paths.original_source),
        ("docling_raw_manifest", paths.docling_raw),
        ("unstructured_raw_manifest", paths.unstructured_raw),
        ("docling_normalized_manifest", paths.docling_normalized),
        ("unstructured_normalized_manifest", paths.unstructured_normalized),
        ("docling_enriched_manifest", paths.docling_enriched),
        ("unstructured_enriched_manifest", paths.unstructured_enriched),
        ("docling_chunks", paths.docling_chunks),
        ("unstructured_chunks", paths.unstructured_chunks),
    ]
