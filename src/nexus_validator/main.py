"""Nexus Validator Worker Service.

Polls for sources in INGESTING state and runs validation automatically.

Per INGESTION_VALIDATION_AGENT_PROMPT_v1.0.md:
- Validator runs automatically after ingestion completes
- Polls database for sources in INGESTING state
- Runs validation and updates governance state
- Configurable poll interval

Usage:
    python -m nexus_validator.main
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from nexus_core.config import get_settings
from nexus_core.db.session import get_async_session_context
from nexus_core.models.source import GovernanceStatus, Source
from nexus_core.validation import Validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_validator_worker():
    """Main validator worker loop.

    Polls for sources in INGESTING state and validates them.
    Runs continuously until interrupted.
    """
    settings = get_settings()
    poll_interval = getattr(settings, "validator_poll_interval", 30)  # Default 30 seconds

    logger.info("Nexus Validator Worker starting...")
    logger.info(f"Poll interval: {poll_interval} seconds")
    logger.info(f"Transfer station: {settings.transfer_station_path}")

    while True:
        try:
            async with get_async_session_context() as session:
                # Find sources in INGESTING state
                result = await session.execute(
                    select(Source)
                    .where(Source.status == GovernanceStatus.INGESTING)
                    .order_by(Source.updated_at)
                )
                sources = result.scalars().all()

                if sources:
                    logger.info(f"Found {len(sources)} source(s) ready for validation")

                    for source in sources:
                        doc_id = source.doc_id
                        logger.info(f"Validating: {doc_id}")

                        try:
                            validator = Validator(session=session, settings=settings)
                            validation_result = await validator.validate(doc_id)

                            if validation_result.status.value == "PASS":
                                logger.info(
                                    f"✅ Validation PASSED: {doc_id} → INGESTED"
                                )
                            else:
                                failed_checks = sum(
                                    1 for check in validation_result.checks
                                    if not check.passed
                                )
                                logger.warning(
                                    f"❌ Validation FAILED: {doc_id} → ERROR "
                                    f"({failed_checks} check(s) failed)"
                                )

                        except Exception as e:
                            logger.error(
                                f"❌ Validation error for {doc_id}: {str(e)}",
                                exc_info=True,
                            )

                else:
                    logger.debug("No sources in INGESTING state")

        except Exception as e:
            logger.error(f"Worker loop error: {str(e)}", exc_info=True)

        # Wait before next poll
        await asyncio.sleep(poll_interval)


async def main():
    """Entry point for validator worker."""
    try:
        await run_validator_worker()
    except KeyboardInterrupt:
        logger.info("Validator worker shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
