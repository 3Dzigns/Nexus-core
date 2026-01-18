"""Nexus Ingestion Worker - Main entry point.

Standalone service for processing approved sources through ingestion pipeline.

Per INGESTION_ARCHITECTURE_v1.0.md:
- Polls for APPROVED sources
- Transitions to INGESTING state
- Executes extraction, normalization, enrichment, chunking
- Triggers storage and validation

Usage:
    python -m nexus_worker.main

    or with uvicorn (for async):
    python src/nexus_worker/main.py
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from nexus_core.config import get_settings
from nexus_core.ingestion.worker import IngestionWorker

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global worker instance for signal handling
_worker: Optional[IngestionWorker] = None


def handle_signal(signum: int, frame) -> None:
    """Handle shutdown signals gracefully.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    if _worker:
        _worker.stop()


async def main() -> None:
    """Main entry point for ingestion worker service."""
    global _worker

    logger.info("=" * 60)
    logger.info("Nexus Ingestion Worker")
    logger.info("=" * 60)
    logger.info(f"Poll interval: {settings.ingestion_worker_poll_interval}s")
    logger.info(f"Transfer Station: {settings.transfer_station_path}")
    logger.info(f"Database: {settings.database_url.split('@')[-1]}")  # Hide credentials
    logger.info("=" * 60)

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Create and start worker
    _worker = IngestionWorker(settings)

    try:
        await _worker.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error in worker: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
