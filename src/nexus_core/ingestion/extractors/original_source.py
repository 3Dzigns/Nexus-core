"""Original source artifact writer.

Per ARTIFACT_CONTRACT_v1.0.md Section 5.1:
- Must write original_source.json to raw manifests directory
- Contains source file metadata and discovery information
- Required for traceability and audit trail

Requirements: ARTIFACT_CONTRACT_v1.0.md
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def write_original_source_artifact(
    doc_id: str,
    source_sha256: str,
    original_filename: str,
    current_path: str,
    discovery_timestamp: datetime,
    artifacts_root: Path,
) -> str:
    """Write original source artifact to disk.

    Per ARTIFACT_CONTRACT_v1.0.md Section 5.1:
    Location: /transfer_station/artifacts/manifests/<doc_id>/raw/original_source.json

    Args:
        doc_id: Document identifier
        source_sha256: SHA-256 hash of source file
        original_filename: Original filename
        current_path: Current file path in Transfer Station
        discovery_timestamp: When source was discovered
        artifacts_root: Artifacts root directory

    Returns:
        Path to written artifact (relative to artifacts root)
    """
    # Create raw manifests directory
    manifest_dir = artifacts_root / "manifests" / doc_id / "raw"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    # Construct original source metadata
    artifact_data = {
        "doc_id": doc_id,
        "source_sha256": source_sha256,
        "original_filename": original_filename,
        "current_path": current_path,
        "discovery_timestamp": discovery_timestamp.isoformat(),
        "artifact_created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Write to disk
    artifact_path = manifest_dir / "original_source.json"
    with open(artifact_path, "w", encoding="utf-8") as f:
        json.dump(artifact_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Original source artifact written: {doc_id}")

    # Return relative path
    return str(artifact_path.relative_to(artifacts_root))
