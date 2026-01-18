"""Content type classification for enrichment.

Per INGESTION_ARCHITECTURE_v1.0.md Section 9.4:
- Deterministically classify blocks using keyword matching and block type heuristics
- Types: rules, statblock, flavor, table, sidebar, etc.
- NO per-chunk LLM calls in MVP1

Requirements: FR-016, FR-017
"""

import logging
from typing import Optional

from nexus_core.ingestion.enrichment.rules_engine import EnrichmentRulesEngine
from nexus_core.ingestion.schemas.block import CanonicalBlock

logger = logging.getLogger(__name__)


class ContentClassifier:
    """Classifies content types for canonical blocks."""

    def __init__(self, rules_engine: EnrichmentRulesEngine):
        """Initialize content classifier.

        Args:
            rules_engine: Enrichment rules engine instance
        """
        self.rules_engine = rules_engine

    def classify_blocks(
        self,
        blocks: list[CanonicalBlock],
        system_id: Optional[str] = None,
    ) -> list[CanonicalBlock]:
        """Classify content types for blocks.

        Args:
            blocks: List of canonical blocks
            system_id: Optional system identifier for rules

        Returns:
            Blocks with content_type metadata added
        """
        if not system_id:
            # Use default classification without system rules
            return self._classify_generic(blocks)

        logger.debug(f"Classifying content types using {system_id} rules")

        for block in blocks:
            content_type = self.rules_engine.classify_content_type(
                text=block.text_content,
                block_type=block.block_type,
                system_id=system_id,
            )

            block.metadata["content_type"] = content_type

        return blocks

    def _classify_generic(
        self,
        blocks: list[CanonicalBlock],
    ) -> list[CanonicalBlock]:
        """Classify blocks using generic heuristics (no system rules).

        Args:
            blocks: List of canonical blocks

        Returns:
            Blocks with generic content_type assigned
        """
        logger.debug("Classifying content types (generic)")

        for block in blocks:
            # Simple heuristic based on block type
            content_type = self._infer_from_block_type(block.block_type)
            block.metadata["content_type"] = content_type

        return blocks

    def _infer_from_block_type(self, block_type: str) -> str:
        """Infer content type from canonical block type.

        Args:
            block_type: Canonical block type

        Returns:
            Content type
        """
        # Simple mapping
        type_mapping = {
            "title": "heading",
            "heading": "heading",
            "paragraph": "narrative",
            "list_item": "list",
            "table": "table",
            "image": "illustration",
            "formula": "mechanics",
        }

        return type_mapping.get(block_type, "general_text")
