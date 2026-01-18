"""Source discovery scanner for Nexus Core ingestion pipeline.

Per INGESTION_ARCHITECTURE_v1.0.md Section 6.1:
- Scan /transfer_station/sources/ for new files
- Compute SHA-256 and check for duplicates
- Create governance records with PENDING_APPROVAL status
- Handle file errors gracefully

Requirements: FR-001, FR-002, FR-003
"""

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import Settings
from nexus_core.ingestion.hashing import compute_sha256, create_doc_id
from nexus_core.models.source import EventType, GovernanceEvent, GovernanceStatus, Source

logger = logging.getLogger(__name__)


class DiscoveryScanner:
    """Scanner for discovering new source files in Transfer Station."""

    def __init__(self, session: AsyncSession, settings: Settings):
        """Initialize discovery scanner.

        Args:
            session: Database session for querying and creating records
            settings: Application settings with transfer_station_path
        """
        self.session = session
        self.settings = settings
        self.sources_path = Path(settings.transfer_station_path) / "sources"

    async def scan(self) -> list[str]:
        """Scan sources directory for new files.

        Returns:
            List of doc_ids for newly discovered sources

        Raises:
            FileNotFoundError: If sources directory does not exist
        """
        if not self.sources_path.exists():
            logger.error(f"Sources directory does not exist: {self.sources_path}")
            raise FileNotFoundError(f"Sources directory not found: {self.sources_path}")

        if not self.sources_path.is_dir():
            logger.error(f"Sources path is not a directory: {self.sources_path}")
            raise NotADirectoryError(f"Sources path is not a directory: {self.sources_path}")

        discovered_doc_ids = []

        # Iterate through all files in sources directory
        for file_path in self.sources_path.iterdir():
            if not file_path.is_file():
                logger.debug(f"Skipping non-file: {file_path}")
                continue

            # Skip hidden files
            if file_path.name.startswith("."):
                logger.debug(f"Skipping hidden file: {file_path}")
                continue

            try:
                doc_id = await self._process_file(file_path)
                if doc_id:
                    discovered_doc_ids.append(doc_id)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                # Continue processing other files even if one fails
                continue

        logger.info(f"Discovery scan complete: {len(discovered_doc_ids)} new source(s)")
        return discovered_doc_ids

    async def _process_file(self, file_path: Path) -> Optional[str]:
        """Process a single file for discovery.

        Args:
            file_path: Path to file to process

        Returns:
            doc_id if file is new, None if already exists or error occurred
        """
        try:
            # Compute SHA-256 hash
            sha256 = compute_sha256(str(file_path))
        except (PermissionError, OSError) as e:
            logger.warning(f"Cannot read file {file_path}: {e}")
            return None

        # Check if SHA-256 already exists in governance table
        result = await self.session.execute(
            select(Source).where(Source.source_sha256 == sha256)
        )
        existing_source = result.scalar_one_or_none()

        if existing_source:
            # Duplicate detected: SHA-256 already exists
            # Create new source record with DUPLICATE_DETECTED status per FR-005
            original_filename = file_path.name
            doc_id = create_doc_id(original_filename, sha256)
            current_path = str(file_path.absolute())

            logger.warning(
                f"Duplicate detected: {file_path.name} matches existing source "
                f"{existing_source.doc_id} (SHA-256: {sha256[:16]}...)"
            )

            # Create Source record with DUPLICATE_DETECTED status
            source = Source(
                doc_id=doc_id,
                source_sha256=sha256,
                original_filename=original_filename,
                current_path=current_path,
                status=GovernanceStatus.DUPLICATE_DETECTED,
                state_version=1,
                owner_user_id="admin",  # Placeholder until admin context implemented
            )

            self.session.add(source)

            # Create governance event for duplicate detection
            event = GovernanceEvent(
                doc_id=doc_id,
                from_status=None,
                to_status=GovernanceStatus.DUPLICATE_DETECTED.value,
                event_type=EventType.STATUS_CHANGE,
                triggered_by="discovery_scanner",
                metadata_json={
                    "original_filename": original_filename,
                    "file_size_bytes": file_path.stat().st_size,
                    "current_path": current_path,
                    "duplicate_of_doc_id": existing_source.doc_id,
                    "duplicate_of_status": existing_source.status.value,
                },
            )

            self.session.add(event)

            # Commit transaction
            await self.session.commit()

            logger.info(
                f"Duplicate source recorded: {original_filename} "
                f"(doc_id: {doc_id}, duplicate_of: {existing_source.doc_id})"
            )

            return doc_id

        # Create new source record
        original_filename = file_path.name
        doc_id = create_doc_id(original_filename, sha256)
        current_path = str(file_path.absolute())

        # Create Source record with PENDING_APPROVAL status
        # Note: owner_user_id is required but admin context not yet implemented
        # For now, use "admin" as placeholder (will be replaced by admin UI)
        source = Source(
            doc_id=doc_id,
            source_sha256=sha256,
            original_filename=original_filename,
            current_path=current_path,
            status=GovernanceStatus.PENDING_APPROVAL,
            state_version=1,
            owner_user_id="admin",  # Placeholder until admin context implemented
        )

        self.session.add(source)

        # Create governance event for discovery
        event = GovernanceEvent(
            doc_id=doc_id,
            from_status=None,  # No previous status
            to_status=GovernanceStatus.PENDING_APPROVAL.value,
            event_type=EventType.STATUS_CHANGE,
            triggered_by="discovery_scanner",
            metadata_json={
                "original_filename": original_filename,
                "file_size_bytes": file_path.stat().st_size,
                "current_path": current_path,
            },
        )

        self.session.add(event)

        # Commit transaction
        await self.session.commit()

        logger.info(
            f"Discovered new source: {original_filename} "
            f"(doc_id: {doc_id}, SHA-256: {sha256[:16]}...)"
        )

        return doc_id


async def discover_sources(session: AsyncSession, settings: Settings) -> list[str]:
    """Convenience function to scan for new sources.

    Args:
        session: Database session
        settings: Application settings

    Returns:
        List of doc_ids for newly discovered sources
    """
    scanner = DiscoveryScanner(session, settings)
    return await scanner.scan()
