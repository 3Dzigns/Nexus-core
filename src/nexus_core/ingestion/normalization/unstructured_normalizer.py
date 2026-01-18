"""Unstructured normalizer for converting raw manifests to canonical blocks.

Per ARTIFACT_CONTRACT_v1.0.md Section 5.3:
- Converts Unstructured raw manifest to canonical block schema
- Preserves tool metadata and provenance
- Outputs to: manifests/<doc_id>/normalized/unstructured_normalized.json

Requirements: FR-015
"""

import json
import logging
from pathlib import Path
from typing import Any

from nexus_core.ingestion.schemas.block import CanonicalBlock

logger = logging.getLogger(__name__)


class UnstructuredNormalizer:
    """Normalizes Unstructured raw manifests to canonical block format."""

    def __init__(self):
        """Initialize Unstructured normalizer."""
        self.tool_origin = "unstructured"

    async def normalize(
        self,
        raw_manifest_path: str,
        doc_id: str,
        artifacts_root: Path,
    ) -> str:
        """Normalize Unstructured raw manifest to canonical blocks.

        Args:
            raw_manifest_path: Path to raw Unstructured manifest
            doc_id: Document identifier
            artifacts_root: Artifacts root directory

        Returns:
            Path to normalized manifest (relative to artifacts root)

        Raises:
            FileNotFoundError: If raw manifest doesn't exist
            ValueError: If manifest format is invalid
        """
        logger.info(f"Normalizing Unstructured manifest: {doc_id}")

        # Load raw manifest
        with open(raw_manifest_path, "r", encoding="utf-8") as f:
            raw_manifest = json.load(f)

        # Convert to canonical blocks
        canonical_blocks = self._convert_to_canonical(raw_manifest, doc_id)

        # Create output directory
        normalized_dir = artifacts_root / "manifests" / doc_id / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)

        # Write normalized manifest
        normalized_path = normalized_dir / "unstructured_normalized.json"
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
            f"Unstructured normalization complete: {doc_id} "
            f"({len(canonical_blocks)} blocks)"
        )

        return str(normalized_path.relative_to(artifacts_root))

    def _convert_to_canonical(
        self,
        raw_manifest: dict[str, Any],
        doc_id: str,
    ) -> list[CanonicalBlock]:
        """Convert Unstructured raw manifest to canonical blocks.

        Args:
            raw_manifest: Raw Unstructured manifest data
            doc_id: Document identifier

        Returns:
            List of canonical blocks
        """
        canonical_blocks = []
        order_index = 0

        # Extract elements from raw manifest
        elements = raw_manifest.get("elements", [])

        for element in elements:
            # Map Unstructured element types to canonical block types
            element_type = element.get("element_type", "NarrativeText")
            block_type = self._map_element_type(element_type)

            # Create canonical block
            canonical_block = CanonicalBlock(
                block_id=element.get("element_id", f"{doc_id}::unstructured::elem_{order_index}"),
                block_type=block_type,
                text_content=element.get("text", ""),
                page_number=element.get("page_number"),
                ocr_flag=element.get("ocr_flag", False),
                tool_origin=self.tool_origin,
                doc_id=doc_id,
                order_index=order_index,
                hierarchy_level=self._infer_hierarchy(element_type),
                parent_block_id=element.get("parent_id"),
                bbox=None,  # Unstructured may not provide bbox
                metadata={
                    "original_element_type": element_type,
                    "unstructured_metadata": element.get("metadata", {}),
                },
            )

            canonical_blocks.append(canonical_block)
            order_index += 1

        return canonical_blocks

    def _map_element_type(self, element_type: str) -> str:
        """Map Unstructured element type to canonical block type.

        Args:
            element_type: Unstructured element type

        Returns:
            Canonical block type
        """
        # Mapping from Unstructured types to canonical types
        type_mapping = {
            "Title": "title",
            "NarrativeText": "paragraph",
            "Text": "paragraph",
            "ListItem": "list_item",
            "Table": "table",
            "Header": "heading",
            "Footer": "footer",
            "PageBreak": "page_break",
            "Image": "image",
            "Formula": "formula",
        }

        return type_mapping.get(element_type, "paragraph")

    def _infer_hierarchy(self, element_type: str) -> int:
        """Infer hierarchy level from element type.

        Args:
            element_type: Unstructured element type

        Returns:
            Hierarchy level (0 = root)
        """
        # Simple hierarchy inference
        # Title/Header = level 0
        # Everything else = level 1
        if element_type in ("Title", "Header"):
            return 0
        return 1
