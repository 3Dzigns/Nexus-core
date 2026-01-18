"""Docling normalizer for converting raw manifests to canonical blocks.

Per ARTIFACT_CONTRACT_v1.0.md Section 5.3:
- Converts Docling raw manifest to canonical block schema
- Preserves tool metadata and provenance
- Outputs to: manifests/<doc_id>/normalized/docling_normalized.json

Requirements: FR-015
"""

import json
import logging
from pathlib import Path
from typing import Any

from nexus_core.ingestion.schemas.block import CanonicalBlock

logger = logging.getLogger(__name__)


class DoclingNormalizer:
    """Normalizes Docling raw manifests to canonical block format."""

    def __init__(self):
        """Initialize Docling normalizer."""
        self.tool_origin = "docling"

    async def normalize(
        self,
        raw_manifest_path: str,
        doc_id: str,
        artifacts_root: Path,
    ) -> str:
        """Normalize Docling raw manifest to canonical blocks.

        Args:
            raw_manifest_path: Path to raw Docling manifest
            doc_id: Document identifier
            artifacts_root: Artifacts root directory

        Returns:
            Path to normalized manifest (relative to artifacts root)

        Raises:
            FileNotFoundError: If raw manifest doesn't exist
            ValueError: If manifest format is invalid
        """
        logger.info(f"Normalizing Docling manifest: {doc_id}")

        # Load raw manifest
        with open(raw_manifest_path, "r", encoding="utf-8") as f:
            raw_manifest = json.load(f)

        # Convert to canonical blocks
        canonical_blocks = self._convert_to_canonical(raw_manifest, doc_id)

        # Create output directory
        normalized_dir = artifacts_root / "manifests" / doc_id / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)

        # Write normalized manifest
        normalized_path = normalized_dir / "docling_normalized.json"
        normalized_data = {
            "doc_id": doc_id,
            "tool_origin": self.tool_origin,
            "extractor_version": raw_manifest.get("extractor_version", "unknown"),
            "run_id": raw_manifest.get("run_id", "unknown"),
            "block_count": len(canonical_blocks),
            "blocks": [block.to_dict() for block in canonical_blocks],
        }

        with open(normalized_path, "w", encoding="utf-8") as f:
            json.dump(normalized_data, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Docling normalization complete: {doc_id} "
            f"({len(canonical_blocks)} blocks)"
        )

        return str(normalized_path.relative_to(artifacts_root))

    def _convert_to_canonical(
        self,
        raw_manifest: dict[str, Any],
        doc_id: str,
    ) -> list[CanonicalBlock]:
        """Convert Docling raw manifest to canonical blocks.

        Args:
            raw_manifest: Raw Docling manifest data
            doc_id: Document identifier

        Returns:
            List of canonical blocks
        """
        canonical_blocks = []
        order_index = 0

        # Extract pages from raw manifest
        pages = raw_manifest.get("pages", [])

        for page in pages:
            page_number = page.get("page_number", 1)
            blocks = page.get("blocks", [])

            for block in blocks:
                # Create canonical block
                canonical_block = CanonicalBlock(
                    block_id=block.get("block_id", f"{doc_id}::docling::block_{order_index}"),
                    block_type=block.get("block_type", "paragraph"),
                    text_content=block.get("text", ""),
                    page_number=page_number,
                    ocr_flag=block.get("ocr_flag", False),
                    tool_origin=self.tool_origin,
                    doc_id=doc_id,
                    order_index=order_index,
                    hierarchy_level=block.get("hierarchy_level", 0),
                    parent_block_id=block.get("parent_block_id"),
                    bbox=block.get("bbox"),
                    metadata={
                        "original_block_type": block.get("block_type"),
                        "docling_metadata": block.get("metadata", {}),
                    },
                )

                canonical_blocks.append(canonical_block)
                order_index += 1

        return canonical_blocks
