"""Base extractor interface for Nexus Core ingestion.

Per ARTIFACT_CONTRACT_v1.0.md:
- Each extractor produces independent raw manifest
- Metadata must include tool provenance (name, version, run_id)
- OCR flag required per block
- Extracted assets saved to dedicated directory

Requirements: FR-011, FR-012, FR-013, FR-014
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class ExtractionResult:
    """Result of document extraction.

    Attributes:
        doc_id: Document identifier
        source_sha256: SHA-256 hash of source
        manifest_path: Path to raw manifest JSON
        asset_paths: List of paths to extracted assets (images, etc.)
        run_id: Extraction run identifier
        extractor_name: Name of extraction tool
        extractor_version: Version of extraction tool
        start_timestamp: Extraction start time
        end_timestamp: Extraction end time
        success: Whether extraction succeeded
        error_message: Error message if extraction failed
    """

    doc_id: str
    source_sha256: str
    manifest_path: str
    asset_paths: list[str]
    run_id: str
    extractor_name: str
    extractor_version: str
    start_timestamp: datetime
    end_timestamp: datetime
    success: bool
    error_message: Optional[str] = None


class ExtractionError(Exception):
    """Exception raised when extraction fails.

    Attributes:
        message: Error message
        doc_id: Document identifier that failed
        extractor: Name of extractor that failed
        details: Additional error context
    """

    def __init__(
        self,
        message: str,
        doc_id: str,
        extractor: str,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.doc_id = doc_id
        self.extractor = extractor
        self.details = details or {}
        super().__init__(self.message)


class Extractor(ABC):
    """Base class for document extractors.

    All extractors must implement the extract() method to produce
    a raw manifest following ARTIFACT_CONTRACT_v1.0.md requirements.
    """

    @abstractmethod
    async def extract(
        self,
        source_path: str,
        doc_id: str,
        source_sha256: str,
        artifacts_root: Path,
    ) -> ExtractionResult:
        """Extract document content and metadata.

        Args:
            source_path: Path to source document
            doc_id: Document identifier
            source_sha256: SHA-256 hash of source
            artifacts_root: Root directory for artifacts (/transfer_station/artifacts)

        Returns:
            ExtractionResult with manifest and asset paths

        Raises:
            ExtractionError: If extraction fails

        Contract Requirements:
        - Must write raw manifest to: artifacts_root/manifests/<doc_id>/raw/<tool>_manifest.json
        - Must write assets to: artifacts_root/assets/<doc_id>/images/
        - Manifest must include all required metadata per ARTIFACT_CONTRACT_v1.0.md
        - Must set OCR flag per block if OCR was used
        - Extraction must be idempotent (same input → same output)
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get extractor name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Get extractor version."""
        pass
