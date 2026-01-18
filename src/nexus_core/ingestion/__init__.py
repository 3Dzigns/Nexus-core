"""Nexus Core ingestion subsystem.

This module handles source discovery, governance, and extraction.
"""

from nexus_core.ingestion.discovery import DiscoveryScanner, discover_sources
from nexus_core.ingestion.hashing import compute_sha256, create_doc_id, sanitize_filename
from nexus_core.ingestion.queue import (
    IngestionJob,
    IngestionQueue,
    enqueue_ingestion_job,
    get_ingestion_queue,
)
from nexus_core.ingestion.worker import IngestionWorker, run_worker

__all__ = [
    # Discovery
    "DiscoveryScanner",
    "discover_sources",
    # Hashing
    "compute_sha256",
    "create_doc_id",
    "sanitize_filename",
    # Queue
    "IngestionJob",
    "IngestionQueue",
    "get_ingestion_queue",
    "enqueue_ingestion_job",
    # Worker
    "IngestionWorker",
    "run_worker",
]
