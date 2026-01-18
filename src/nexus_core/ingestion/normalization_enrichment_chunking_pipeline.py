"""Phase 3 pipeline: Normalization, Enrichment, and Chunking.

Per INGESTION_ARCHITECTURE_v1.0.md Sections 8-10:
- Normalize raw manifests to canonical blocks
- Enrich with content-aware metadata
- Chunk into retrievable units
- Dual processing (Docling + Unstructured)

Requirements: FR-015, FR-016, FR-017, FR-018, FR-019, FR-020, NFR-010
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import Settings
from nexus_core.ingestion.chunking.chunker import Chunker, ChunkingConfig
from nexus_core.ingestion.enrichment_pipeline import EnrichmentPipeline
from nexus_core.ingestion.normalization.docling_normalizer import DoclingNormalizer
from nexus_core.ingestion.normalization.unstructured_normalizer import (
    UnstructuredNormalizer,
)
from nexus_core.models.source import Manifest, ManifestType, Source, ToolId

logger = logging.getLogger(__name__)


class NormalizationEnrichmentChunkingPipeline:
    """Phase 3 pipeline orchestrator.

    Coordinates normalization, enrichment, and chunking for both extractors.
    """

    def __init__(self, session: AsyncSession, settings: Settings):
        """Initialize Phase 3 pipeline.

        Args:
            session: Database session
            settings: Application settings
        """
        self.session = session
        self.settings = settings
        self.artifacts_root = Path(settings.transfer_station_path) / "artifacts"

        # Initialize components
        self.docling_normalizer = DoclingNormalizer()
        self.unstructured_normalizer = UnstructuredNormalizer()
        self.enrichment_pipeline = EnrichmentPipeline()
        self.chunker = Chunker(ChunkingConfig())

    async def execute(self, source: Source) -> bool:
        """Execute Phase 3 pipeline for a source.

        Args:
            source: Source record from database

        Returns:
            True if pipeline succeeded, False otherwise

        Workflow:
        1. Load raw manifests (from Phase 2)
        2. Normalize to canonical blocks (dual)
        3. Enrich with metadata (dual)
        4. Chunk into retrievable units (dual)
        5. Create manifest database records
        6. Return success status
        """
        doc_id = source.doc_id
        logger.info(f"Starting Phase 3 pipeline: {doc_id}")

        try:
            # Get raw manifest paths from database
            docling_raw_path = await self._get_manifest_path(
                doc_id, ToolId.DOCLING, ManifestType.RAW
            )
            unstructured_raw_path = await self._get_manifest_path(
                doc_id, ToolId.UNSTRUCTURED, ManifestType.RAW
            )

            if not docling_raw_path or not unstructured_raw_path:
                logger.error(f"Missing raw manifests for {doc_id}")
                return False

            # Run normalization, enrichment, and chunking for both tools in parallel
            docling_task = self._process_tool_pipeline(
                doc_id=doc_id,
                tool_origin="docling",
                tool_id=ToolId.DOCLING,
                raw_manifest_path=docling_raw_path,
                system_id=source.system_id,
            )

            unstructured_task = self._process_tool_pipeline(
                doc_id=doc_id,
                tool_origin="unstructured",
                tool_id=ToolId.UNSTRUCTURED,
                raw_manifest_path=unstructured_raw_path,
                system_id=source.system_id,
            )

            # Wait for both to complete
            docling_success, unstructured_success = await asyncio.gather(
                docling_task, unstructured_task, return_exceptions=True
            )

            # Check for failures
            if isinstance(docling_success, Exception):
                logger.error(f"Docling pipeline failed: {docling_success}")
                return False

            if isinstance(unstructured_success, Exception):
                logger.error(f"Unstructured pipeline failed: {unstructured_success}")
                return False

            logger.info(f"Phase 3 pipeline complete: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Phase 3 pipeline failed for {doc_id}: {e}", exc_info=True)
            return False

    async def _process_tool_pipeline(
        self,
        doc_id: str,
        tool_origin: str,
        tool_id: ToolId,
        raw_manifest_path: str,
        system_id: Optional[str],
    ) -> bool:
        """Process normalization → enrichment → chunking for one tool.

        Args:
            doc_id: Document identifier
            tool_origin: Tool name (docling or unstructured)
            tool_id: ToolId enum value
            raw_manifest_path: Path to raw manifest
            system_id: Optional system identifier

        Returns:
            True if successful
        """
        logger.info(f"Processing {tool_origin} pipeline for {doc_id}")

        # Step 1: Normalize
        if tool_origin == "docling":
            normalized_path = await self.docling_normalizer.normalize(
                raw_manifest_path, doc_id, self.artifacts_root
            )
        else:
            normalized_path = await self.unstructured_normalizer.normalize(
                raw_manifest_path, doc_id, self.artifacts_root
            )

        # Create manifest record
        normalized_manifest = Manifest(
            doc_id=doc_id,
            tool_id=tool_id,
            manifest_type=ManifestType.NORMALIZED,
            path=normalized_path,
            run_id=f"{tool_origin}_normalization",
        )
        self.session.add(normalized_manifest)

        # Step 2: Enrich
        enriched_path = await self.enrichment_pipeline.enrich(
            normalized_manifest_path=str(self.artifacts_root / normalized_path),
            doc_id=doc_id,
            system_id=system_id,
            artifacts_root=self.artifacts_root,
            tool_origin=tool_origin,
        )

        # Create manifest record
        enriched_manifest = Manifest(
            doc_id=doc_id,
            tool_id=tool_id,
            manifest_type=ManifestType.ENRICHED,
            path=enriched_path,
            run_id=f"{tool_origin}_enrichment",
        )
        self.session.add(enriched_manifest)

        # Step 3: Chunk
        chunks_path = await self.chunker.chunk(
            enriched_manifest_path=str(self.artifacts_root / enriched_path),
            doc_id=doc_id,
            artifacts_root=self.artifacts_root,
            tool_origin=tool_origin,
        )

        logger.info(f"{tool_origin} pipeline complete for {doc_id}")
        return True

    async def _get_manifest_path(
        self,
        doc_id: str,
        tool_id: ToolId,
        manifest_type: ManifestType,
    ) -> Optional[str]:
        """Get manifest path from database.

        Args:
            doc_id: Document identifier
            tool_id: Tool identifier
            manifest_type: Manifest type

        Returns:
            Absolute path to manifest, or None if not found
        """
        from sqlalchemy import select

        result = await self.session.execute(
            select(Manifest)
            .where(Manifest.doc_id == doc_id)
            .where(Manifest.tool_id == tool_id)
            .where(Manifest.manifest_type == manifest_type)
        )

        manifest = result.scalar_one_or_none()

        if manifest:
            return str(self.artifacts_root / manifest.path)

        return None
