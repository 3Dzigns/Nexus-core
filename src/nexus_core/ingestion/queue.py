"""Ingestion job queue for Nexus Core.

Provides in-memory job queue for MVP1. Future versions may use Redis/Celery.

Per INGESTION_ARCHITECTURE_v1.0.md Section 6.2:
- Jobs are enqueued when sources are approved
- Worker polls queue for approved sources
- Job payload includes all necessary source metadata

Requirements: FR-004
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class IngestionJob:
    """Job payload for ingestion pipeline.

    Attributes:
        doc_id: Document identifier
        source_sha256: SHA-256 hash of source file
        original_filename: Original filename
        current_path: Current file path in Transfer Station
        system_id: Optional system identifier
        game_id: Optional game identifier
        owner_user_id: Owner user identifier
        enqueued_at: Timestamp when job was enqueued
    """

    doc_id: str
    source_sha256: str
    original_filename: str
    current_path: str
    system_id: Optional[str]
    game_id: Optional[str]
    owner_user_id: str
    enqueued_at: datetime


class IngestionQueue:
    """In-memory ingestion job queue for MVP1.

    Thread-safe async queue using asyncio.Queue.
    Future versions may replace with Redis/Celery for distributed processing.

    Note: Queue is not persistent - jobs are lost on restart.
    For MVP1, this is acceptable as worker polls database for APPROVED sources.
    Queue serves as notification mechanism to avoid polling delays.
    """

    def __init__(self, maxsize: int = 0):
        """Initialize ingestion queue.

        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self._queue: asyncio.Queue[IngestionJob] = asyncio.Queue(maxsize=maxsize)
        logger.info(f"Ingestion queue initialized (maxsize={maxsize or 'unlimited'})")

    async def enqueue(self, job: IngestionJob) -> None:
        """Add a job to the queue.

        Args:
            job: IngestionJob to enqueue

        Raises:
            asyncio.QueueFull: If queue is full (only if maxsize > 0)
        """
        await self._queue.put(job)
        logger.info(
            f"Job enqueued: {job.doc_id} (queue size: {self._queue.qsize()})"
        )

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[IngestionJob]:
        """Remove and return a job from the queue.

        Args:
            timeout: Maximum time to wait for a job (None = wait forever)

        Returns:
            IngestionJob if available, None if timeout expires

        Raises:
            asyncio.TimeoutError: If timeout expires (when timeout is specified)
        """
        try:
            if timeout is not None:
                job = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            else:
                job = await self._queue.get()

            logger.debug(
                f"Job dequeued: {job.doc_id} (remaining: {self._queue.qsize()})"
            )
            return job

        except asyncio.TimeoutError:
            return None

    def qsize(self) -> int:
        """Get current queue size.

        Returns:
            Number of jobs in queue
        """
        return self._queue.qsize()

    def empty(self) -> bool:
        """Check if queue is empty.

        Returns:
            True if queue is empty
        """
        return self._queue.empty()

    def full(self) -> bool:
        """Check if queue is full.

        Returns:
            True if queue is full (only if maxsize > 0)
        """
        return self._queue.full()


# Global queue instance (singleton for MVP1)
# Note: In production, this would be replaced with Redis/Celery
_global_queue: Optional[IngestionQueue] = None


def get_ingestion_queue() -> IngestionQueue:
    """Get global ingestion queue instance.

    Returns:
        Global IngestionQueue singleton

    Note:
        Creates queue on first call. For MVP1, uses in-memory queue.
        Future versions should replace with distributed queue (Redis/Celery).
    """
    global _global_queue
    if _global_queue is None:
        _global_queue = IngestionQueue(maxsize=0)  # Unlimited size for MVP1
    return _global_queue


async def enqueue_ingestion_job(
    doc_id: str,
    source_sha256: str,
    original_filename: str,
    current_path: str,
    system_id: Optional[str],
    game_id: Optional[str],
    owner_user_id: str,
) -> None:
    """Convenience function to enqueue an ingestion job.

    Args:
        doc_id: Document identifier
        source_sha256: SHA-256 hash
        original_filename: Original filename
        current_path: Current file path
        system_id: Optional system identifier
        game_id: Optional game identifier
        owner_user_id: Owner user identifier
    """
    queue = get_ingestion_queue()

    job = IngestionJob(
        doc_id=doc_id,
        source_sha256=source_sha256,
        original_filename=original_filename,
        current_path=current_path,
        system_id=system_id,
        game_id=game_id,
        owner_user_id=owner_user_id,
        enqueued_at=datetime.now(timezone.utc),
    )

    await queue.enqueue(job)
    logger.info(f"Ingestion job enqueued for {doc_id}")
