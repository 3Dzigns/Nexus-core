"""Soft deactivation logic for removed sources.

Per INGESTION_ARCHITECTURE_v1.0.md Section 12 and CLEANUP_STRATEGY_v1.0.md:
- Set active=False on all chunks for deactivated source
- Set active=False on all embeddings for deactivated source
- Update FTS index to exclude deactivated chunks (handled via active flag in queries)
- Create REMOVAL_REQUEST governance event
- Atomic transaction for all updates

Requirements: FR-008, FR-009, FR-010
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.governance.state_machine import GovernanceStateMachine
from nexus_core.models.source import Chunk, Embedding, GovernanceStatus, Source

logger = logging.getLogger(__name__)


class DeactivationService:
    """Handles soft deactivation of sources and derived records."""

    def __init__(self, session: AsyncSession):
        """Initialize deactivation service.

        Args:
            session: Database session
        """
        self.session = session

    async def deactivate_source(
        self,
        doc_id: str,
        triggered_by: str = "system",
        previous_status: Optional[GovernanceStatus] = None,
    ) -> bool:
        """Soft deactivate a source and all derived records.

        Args:
            doc_id: Document identifier
            triggered_by: User or system triggering deactivation
            previous_status: Previous governance status before deactivation

        Returns:
            True if deactivation succeeded, False otherwise

        Workflow:
        1. Transition source to DEACTIVATED status
        2. Set active=False on all chunks for this doc_id
        3. Set active=False on all embeddings for this doc_id
        4. Create REMOVAL_REQUEST governance event
        5. Commit transaction (atomic)

        On failure: Rollback all changes
        """
        try:
            logger.info(f"Starting soft deactivation: {doc_id}")

            # Fetch source to verify existence
            result = await self.session.execute(
                select(Source).where(Source.doc_id == doc_id)
            )
            source = result.scalar_one_or_none()

            if source is None:
                logger.warning(f"Source not found for deactivation: {doc_id}")
                return False

            # Capture previous status
            if previous_status is None:
                previous_status = source.status

            # Step 1: Transition to DEACTIVATED
            state_machine = GovernanceStateMachine(self.session)
            await state_machine.transition(
                doc_id=doc_id,
                to_status=GovernanceStatus.DEACTIVATED,
                triggered_by=triggered_by,
                metadata={
                    "reason": "source_file_removed",
                    "previous_status": previous_status.value,
                    "removal_detected_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Step 2: Deactivate all chunks for this doc_id
            chunk_update_result = await self.session.execute(
                update(Chunk)
                .where(Chunk.doc_id == doc_id)
                .values(active=False)
            )
            chunks_deactivated = chunk_update_result.rowcount

            # Step 3: Deactivate all embeddings for this doc_id
            # (via subquery to find chunk_ids for this doc_id)
            embedding_update_result = await self.session.execute(
                update(Embedding)
                .where(
                    Embedding.chunk_id.in_(
                        select(Chunk.chunk_id).where(Chunk.doc_id == doc_id)
                    )
                )
                .values(active=False)
            )
            embeddings_deactivated = embedding_update_result.rowcount

            # Step 4: Create REMOVAL_REQUEST governance event
            # (already created by state machine transition above)

            # Commit atomic transaction
            await self.session.commit()

            logger.info(
                f"Soft deactivation complete: {doc_id} "
                f"({chunks_deactivated} chunks, {embeddings_deactivated} embeddings deactivated)"
            )

            return True

        except Exception as e:
            logger.error(f"Deactivation failed for {doc_id}: {e}", exc_info=True)
            await self.session.rollback()
            return False

    async def get_active_sources(self) -> list[Source]:
        """Get all sources that are currently active (INGESTED status).

        Returns:
            List of active sources

        Used for removal detection: compare active sources against filesystem.
        """
        result = await self.session.execute(
            select(Source).where(Source.status == GovernanceStatus.INGESTED)
        )
        return list(result.scalars().all())
