"""Extraction pipeline orchestrator for dual extraction.

Per ARTIFACT_CONTRACT_v1.0.md Section 6:
- Both Docling and Unstructured must succeed
- Failure of either blocks ingestion
- Artifacts written before state transitions
- Rollback deletes all artifacts on failure

Requirements: FR-011, FR-012
"""

import asyncio
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import Settings
from nexus_core.governance.state_machine import GovernanceStateMachine
from nexus_core.ingestion.extractors.asset_handler import AssetHandler
from nexus_core.ingestion.extractors.base import ExtractionError, ExtractionResult
from nexus_core.ingestion.extractors.docling_extractor import DoclingExtractor
from nexus_core.ingestion.extractors.original_source import (
    write_original_source_artifact,
)
from nexus_core.ingestion.extractors.unstructured_extractor import UnstructuredExtractor
from nexus_core.models.source import GovernanceStatus, Manifest, ManifestType, Source, ToolId

logger = logging.getLogger(__name__)


@dataclass
class ExtractionPipelineResult:
    """Result of extraction pipeline execution.

    Attributes:
        doc_id: Document identifier
        success: Whether pipeline succeeded
        docling_result: Docling extraction result (if succeeded)
        unstructured_result: Unstructured extraction result (if succeeded)
        error_message: Error message if pipeline failed
        manifests_created: List of manifest database records created
    """

    doc_id: str
    success: bool
    docling_result: Optional[ExtractionResult] = None
    unstructured_result: Optional[ExtractionResult] = None
    error_message: Optional[str] = None
    manifests_created: list[Manifest] = None

    def __post_init__(self):
        if self.manifests_created is None:
            self.manifests_created = []


class ExtractionPipeline:
    """Orchestrates dual extraction using Docling and Unstructured.

    Per INGESTION_ARCHITECTURE_v1.0.md Section 7:
    - Run both extractors in parallel
    - Both must succeed (dual-manifest rule)
    - Write original source artifact first
    - Create manifest database records
    - Rollback all artifacts on failure
    """

    def __init__(self, session: AsyncSession, settings: Settings):
        """Initialize extraction pipeline.

        Args:
            session: Database session
            settings: Application settings
        """
        self.session = session
        self.settings = settings
        self.artifacts_root = Path(settings.transfer_station_path) / "artifacts"

        # Initialize extractors
        self.docling = DoclingExtractor(version="1.0.0")
        self.unstructured = UnstructuredExtractor(version="0.10.0")

        # Initialize asset handler
        self.asset_handler = AssetHandler(self.artifacts_root / "assets")

    async def execute(self, source: Source) -> ExtractionPipelineResult:
        """Execute extraction pipeline for a source.

        Args:
            source: Source record from database

        Returns:
            ExtractionPipelineResult with extraction outcomes

        Workflow:
        1. Write original source artifact
        2. Run Docling and Unstructured extractors in parallel
        3. Verify both succeeded (dual-manifest rule)
        4. Create manifest database records
        5. On failure: rollback all artifacts and transition to ERROR state
        """
        doc_id = source.doc_id
        logger.info(f"Starting extraction pipeline: {doc_id}")

        try:
            # Step 1: Write original source artifact
            logger.info(f"Writing original source artifact: {doc_id}")
            original_artifact_path = write_original_source_artifact(
                doc_id=doc_id,
                source_sha256=source.source_sha256,
                original_filename=source.original_filename,
                current_path=source.current_path,
                discovery_timestamp=source.first_seen_at,
                artifacts_root=self.artifacts_root,
            )

            # Create manifest record for original source
            original_manifest = Manifest(
                doc_id=doc_id,
                tool_id=ToolId.DOCLING,  # Arbitrary choice for original source
                manifest_type=ManifestType.ORIGINAL_SOURCE,
                path=original_artifact_path,
                run_id="original_source",
            )
            self.session.add(original_manifest)

            # Step 2: Run dual extraction in parallel
            logger.info(f"Running dual extraction (parallel): {doc_id}")

            docling_task = self.docling.extract(
                source_path=source.current_path,
                doc_id=doc_id,
                source_sha256=source.source_sha256,
                artifacts_root=self.artifacts_root,
            )

            unstructured_task = self.unstructured.extract(
                source_path=source.current_path,
                doc_id=doc_id,
                source_sha256=source.source_sha256,
                artifacts_root=self.artifacts_root,
            )

            # Wait for both extractors to complete
            docling_result, unstructured_result = await asyncio.gather(
                docling_task, unstructured_task, return_exceptions=True
            )

            # Step 3: Check for extraction failures
            if isinstance(docling_result, Exception):
                raise ExtractionError(
                    message=f"Docling extraction failed: {str(docling_result)}",
                    doc_id=doc_id,
                    extractor="docling",
                )

            if isinstance(unstructured_result, Exception):
                raise ExtractionError(
                    message=f"Unstructured extraction failed: {str(unstructured_result)}",
                    doc_id=doc_id,
                    extractor="unstructured",
                )

            # Step 4: Create manifest database records
            manifests_created = []

            # Docling manifest
            docling_manifest = Manifest(
                doc_id=doc_id,
                tool_id=ToolId.DOCLING,
                manifest_type=ManifestType.RAW,
                path=docling_result.manifest_path,
                run_id=docling_result.run_id,
            )
            self.session.add(docling_manifest)
            manifests_created.append(docling_manifest)

            # Unstructured manifest
            unstructured_manifest = Manifest(
                doc_id=doc_id,
                tool_id=ToolId.UNSTRUCTURED,
                manifest_type=ManifestType.RAW,
                path=unstructured_result.manifest_path,
                run_id=unstructured_result.run_id,
            )
            self.session.add(unstructured_manifest)
            manifests_created.append(unstructured_manifest)

            # Commit database changes
            await self.session.commit()

            logger.info(
                f"Extraction pipeline complete: {doc_id} "
                f"(Docling: {len(docling_result.asset_paths)} assets, "
                f"Unstructured: {len(unstructured_result.asset_paths)} assets)"
            )

            return ExtractionPipelineResult(
                doc_id=doc_id,
                success=True,
                docling_result=docling_result,
                unstructured_result=unstructured_result,
                manifests_created=[original_manifest] + manifests_created,
            )

        except Exception as e:
            logger.error(f"Extraction pipeline failed for {doc_id}: {e}", exc_info=True)

            # Rollback: delete all artifacts
            await self._rollback_artifacts(doc_id)

            # Transition to ERROR state
            await self._transition_to_error(source, str(e))

            return ExtractionPipelineResult(
                doc_id=doc_id,
                success=False,
                error_message=str(e),
            )

    async def _rollback_artifacts(self, doc_id: str) -> None:
        """Delete all artifacts for a document on failure.

        Args:
            doc_id: Document identifier
        """
        logger.warning(f"Rolling back artifacts for {doc_id}")

        try:
            # Delete manifest directory
            manifest_dir = self.artifacts_root / "manifests" / doc_id
            if manifest_dir.exists():
                shutil.rmtree(manifest_dir)
                logger.info(f"Deleted manifests: {manifest_dir}")

            # Delete assets directory
            assets_dir = self.artifacts_root / "assets" / doc_id
            if assets_dir.exists():
                shutil.rmtree(assets_dir)
                logger.info(f"Deleted assets: {assets_dir}")

        except Exception as e:
            logger.error(f"Error during artifact rollback for {doc_id}: {e}")

    async def _transition_to_error(self, source: Source, error_message: str) -> None:
        """Transition source to ERROR state on extraction failure.

        Args:
            source: Source record
            error_message: Error message to include in metadata
        """
        try:
            state_machine = GovernanceStateMachine(self.session)
            await state_machine.transition(
                doc_id=source.doc_id,
                to_status=GovernanceStatus.ERROR,
                triggered_by="extraction_pipeline",
                metadata={
                    "error_type": "extraction_failure",
                    "error_message": error_message,
                },
            )
            await self.session.commit()
            logger.info(f"Source transitioned to ERROR: {source.doc_id}")
        except Exception as e:
            logger.error(
                f"Failed to transition {source.doc_id} to ERROR state: {e}"
            )
