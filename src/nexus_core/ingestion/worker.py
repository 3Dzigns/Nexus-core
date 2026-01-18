"""Ingestion worker service for Nexus Core.

Polls for approved sources and manages ingestion pipeline execution.

Per INGESTION_ARCHITECTURE_v1.0.md Section 6.3:
- Poll database for sources with status APPROVED
- Check job queue for new approvals (optimization)
- Transition APPROVED → INGESTING
- Trigger extraction pipeline (Phase 2 implementation)
- Handle errors and rollback on failure

Requirements: FR-004
"""

import asyncio
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import Settings, get_settings
from nexus_core.db.session import get_async_session_context
from nexus_core.governance.state_machine import (
    GovernanceStateMachine,
    IllegalTransitionError,
)
from nexus_core.ingestion.extraction_pipeline import ExtractionPipeline
from nexus_core.ingestion.normalization_enrichment_chunking_pipeline import (
    NormalizationEnrichmentChunkingPipeline,
)
from nexus_core.ingestion.queue import IngestionJob, get_ingestion_queue
from nexus_core.models.source import GovernanceStatus, Source

logger = logging.getLogger(__name__)


class IngestionWorker:
    """Worker service for ingestion pipeline.

    Responsibilities:
    - Poll for APPROVED sources in database
    - Process jobs from in-memory queue
    - Transition sources to INGESTING state
    - Trigger extraction pipeline (Phase 2+)
    - Handle errors and state transitions
    """

    def __init__(self, settings: Settings):
        """Initialize ingestion worker.

        Args:
            settings: Application settings with poll interval
        """
        self.settings = settings
        self.poll_interval = settings.ingestion_worker_poll_interval
        self.queue = get_ingestion_queue()
        self._running = False

    async def start(self) -> None:
        """Start worker polling loop.

        Runs until explicitly stopped or fatal error occurs.
        """
        self._running = True
        logger.info(
            f"Ingestion worker starting (poll interval: {self.poll_interval}s)"
        )

        while self._running:
            try:
                await self._process_cycle()
            except Exception as e:
                logger.error(f"Error in worker cycle: {e}", exc_info=True)
                # Continue running even if cycle fails
                await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop worker polling loop."""
        self._running = False
        logger.info("Ingestion worker stopping...")

    async def _process_cycle(self) -> None:
        """Execute one worker cycle.

        1. Check queue for new jobs (with short timeout)
        2. Poll database for APPROVED sources
        3. Process each approved source
        4. Sleep until next cycle
        """
        # Check queue first (optimization to reduce latency)
        job = await self.queue.dequeue(timeout=1.0)
        if job:
            logger.debug(f"Processing queued job: {job.doc_id}")
            async with get_async_session_context() as session:
                await self._process_source(session, job.doc_id)

        # Poll database for any APPROVED sources (fallback + handles restarts)
        async with get_async_session_context() as session:
            await self._poll_approved_sources(session)

        # Sleep until next cycle
        await asyncio.sleep(self.poll_interval)

    async def _poll_approved_sources(self, session: AsyncSession) -> None:
        """Poll database for sources with APPROVED status.

        Args:
            session: Database session
        """
        result = await session.execute(
            select(Source)
            .where(Source.status == GovernanceStatus.APPROVED)
            .order_by(Source.updated_at)
        )
        sources = result.scalars().all()

        if sources:
            logger.info(f"Found {len(sources)} approved source(s) ready for ingestion")

            for source in sources:
                try:
                    await self._process_source(session, source.doc_id)
                    # Commit after each source to avoid long-running transactions
                    await session.commit()
                except Exception as e:
                    logger.error(
                        f"Error processing source {source.doc_id}: {e}",
                        exc_info=True,
                    )
                    await session.rollback()
                    # Continue with next source

    async def _process_source(self, session: AsyncSession, doc_id: str) -> None:
        """Process a single approved source.

        Args:
            session: Database session
            doc_id: Document identifier to process

        Raises:
            Exception: On processing errors (caller handles rollback)
        """
        # Fetch source with lock
        result = await session.execute(
            select(Source).where(Source.doc_id == doc_id).with_for_update()
        )
        source = result.scalar_one_or_none()

        if source is None:
            logger.warning(f"Source not found: {doc_id}")
            return

        # Check if already in INGESTING or later state
        if source.status != GovernanceStatus.APPROVED:
            logger.debug(
                f"Source {doc_id} already processed (status: {source.status.value})"
            )
            return

        logger.info(f"Processing approved source: {doc_id}")

        # Transition to INGESTING
        state_machine = GovernanceStateMachine(session)
        try:
            await state_machine.transition(
                doc_id=doc_id,
                to_status=GovernanceStatus.INGESTING,
                triggered_by="ingestion_worker",
                metadata={
                    "worker_action": "start_ingestion",
                    "original_filename": source.original_filename,
                },
            )

            logger.info(f"Source transitioned to INGESTING: {doc_id}")

            # Trigger extraction pipeline (Phase 2)
            await self._run_extraction_pipeline(session, source)

        except IllegalTransitionError as e:
            logger.warning(
                f"Cannot transition {doc_id} to INGESTING: {e.message}"
            )
            # Source may have been processed by another worker instance
            return

    async def _run_extraction_pipeline(
        self, session: AsyncSession, source: Source
    ) -> None:
        """Run extraction pipeline for a source.

        Args:
            session: Database session
            source: Source record to process

        Workflow:
        1. Create extraction pipeline instance
        2. Execute dual extraction (Docling + Unstructured)
        3. Write artifacts to disk
        4. Create manifest database records
        5. On success: proceed to Phase 3 (normalization)
        6. On failure: artifacts rolled back, status → ERROR
        """
        # Phase 2: Extraction
        extraction_pipeline = ExtractionPipeline(session, self.settings)
        extraction_result = await extraction_pipeline.execute(source)

        if not extraction_result.success:
            logger.error(
                f"Extraction pipeline failed: {source.doc_id} - {extraction_result.error_message}"
            )
            # Pipeline already transitioned to ERROR state and rolled back artifacts
            return

        logger.info(
            f"Extraction pipeline succeeded: {source.doc_id} "
            f"(manifests: {len(extraction_result.manifests_created)})"
        )

        # Phase 3: Normalization, Enrichment, Chunking
        phase3_pipeline = NormalizationEnrichmentChunkingPipeline(session, self.settings)
        phase3_success = await phase3_pipeline.execute(source)

        if phase3_success:
            logger.info(f"Phase 3 pipeline succeeded: {source.doc_id}")
            # TODO: Phase 4 - Trigger storage and indexing
            logger.info(
                f"[Phase 4 TODO] Would start storage pipeline for: {source.doc_id}"
            )
        else:
            logger.error(f"Phase 3 pipeline failed: {source.doc_id}")
            # TODO: Handle Phase 3 failure (transition to ERROR?)


async def run_worker() -> None:
    """Main entry point for ingestion worker service.

    Run this function to start the worker in a dedicated process/container.

    Example:
        python -m nexus_core.ingestion.worker
    """
    settings = get_settings()
    worker = IngestionWorker(settings)

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        worker.stop()
    except Exception as e:
        logger.error(f"Fatal error in worker: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Allow running worker directly: python -m nexus_core.ingestion.worker
    asyncio.run(run_worker())
