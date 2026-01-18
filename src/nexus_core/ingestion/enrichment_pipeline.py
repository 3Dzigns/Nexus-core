"""Enrichment pipeline orchestrator.

Per INGESTION_ARCHITECTURE_v1.0.md Section 9:
- Apply rules engine, section path, content classification
- Output enriched manifests (dual, tool-separated)
- Record enrichment_rules_version

Requirements: FR-015, FR-016, FR-017, FR-018
"""

import json
import logging
from pathlib import Path
from typing import Optional

from nexus_core.ingestion.enrichment.content_classifier import ContentClassifier
from nexus_core.ingestion.enrichment.rules_engine import EnrichmentRulesEngine
from nexus_core.ingestion.enrichment.section_path import SectionPathAssigner
from nexus_core.ingestion.schemas.block import CanonicalBlock

logger = logging.getLogger(__name__)


class EnrichmentPipeline:
    """Orchestrates enrichment of normalized manifests."""

    def __init__(self, rules_dir: Optional[Path] = None):
        """Initialize enrichment pipeline.

        Args:
            rules_dir: Directory containing enrichment rules YAML files
        """
        self.rules_engine = EnrichmentRulesEngine(rules_dir)
        self.section_assigner = SectionPathAssigner()
        self.content_classifier = ContentClassifier(self.rules_engine)

    async def enrich(
        self,
        normalized_manifest_path: str,
        doc_id: str,
        system_id: Optional[str],
        artifacts_root: Path,
        tool_origin: str,
    ) -> str:
        """Enrich a normalized manifest.

        Args:
            normalized_manifest_path: Path to normalized manifest
            doc_id: Document identifier
            system_id: Optional system identifier for rules
            artifacts_root: Artifacts root directory
            tool_origin: Tool that produced manifest (docling or unstructured)

        Returns:
            Path to enriched manifest (relative to artifacts root)
        """
        logger.info(f"Enriching {tool_origin} manifest: {doc_id}")

        # Load normalized manifest
        with open(normalized_manifest_path, "r", encoding="utf-8") as f:
            normalized_data = json.load(f)

        # Convert blocks from dict to CanonicalBlock
        blocks = [
            CanonicalBlock.from_dict(block_dict)
            for block_dict in normalized_data.get("blocks", [])
        ]

        # Step 1: Assign section paths
        blocks = self.section_assigner.assign_section_path(blocks)

        # Step 2: Classify content types
        blocks = self.content_classifier.classify_blocks(blocks, system_id)

        # Step 3: Add system tags
        if system_id:
            system_tags = self.rules_engine.get_system_tags(system_id)
            for block in blocks:
                block.metadata["system_tags"] = system_tags

        # Get enrichment metadata
        enrichment_rules_version = (
            self.rules_engine.get_rules_version(system_id)
            if system_id
            else "none"
        )

        # Create enriched manifest
        enriched_data = {
            "doc_id": doc_id,
            "tool_origin": tool_origin,
            "extractor_version": normalized_data.get("extractor_version", "unknown"),
            "run_id": normalized_data.get("run_id", "unknown"),
            "system_id": system_id,
            "enrichment_rules_version": enrichment_rules_version,
            "block_count": len(blocks),
            "blocks": [block.to_dict() for block in blocks],
        }

        # Write enriched manifest
        enriched_dir = artifacts_root / "manifests" / doc_id / "enriched"
        enriched_dir.mkdir(parents=True, exist_ok=True)

        enriched_path = enriched_dir / f"{tool_origin}_enriched.json"
        with open(enriched_path, "w", encoding="utf-8") as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Enrichment complete: {doc_id} ({tool_origin}, {len(blocks)} blocks)"
        )

        return str(enriched_path.relative_to(artifacts_root))
