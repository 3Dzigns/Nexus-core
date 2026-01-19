"""Chunk storage layer for database insertion.

Per INGESTION_ARCHITECTURE_v1.0.md Section 11:
- Insert chunks into chunks table
- Use UPSERT to ensure idempotency
- Batch insert for performance
- Set active=True for new chunks

Requirements: FR-021
"""

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.models.source import Chunk, ToolId

logger = logging.getLogger(__name__)


class ChunkStorage:
    """Handles chunk database storage operations."""

    def __init__(self, session: AsyncSession):
        """Initialize chunk storage.

        Args:
            session: Database session
        """
        self.session = session

    async def store_chunks(
        self,
        chunks_file_path: Path,
        doc_id: str,
        tool_id: ToolId,
    ) -> int:
        """Store chunks from JSONL file to database.

        Args:
            chunks_file_path: Path to chunks JSONL file
            doc_id: Document identifier
            tool_id: Tool identifier (DOCLING or UNSTRUCTURED)

        Returns:
            Number of chunks stored

        Uses UPSERT to ensure idempotency:
        - If chunk_id exists: update fields
        - If chunk_id new: insert record
        """
        logger.info(f"Storing chunks from {chunks_file_path} (doc_id: {doc_id})")

        chunks_data = self._load_chunks_from_jsonl(chunks_file_path)

        if not chunks_data:
            logger.warning(f"No chunks found in {chunks_file_path}")
            return 0

        # Convert to database records
        chunk_records = [
            self._create_chunk_record(chunk_data, tool_id)
            for chunk_data in chunks_data
        ]

        # Batch UPSERT
        await self._batch_upsert(chunk_records)

        logger.info(f"Stored {len(chunk_records)} chunks for {doc_id} ({tool_id.value})")

        return len(chunk_records)

    def _load_chunks_from_jsonl(self, chunks_file_path: Path) -> list[dict[str, Any]]:
        """Load chunks from JSONL file.

        Args:
            chunks_file_path: Path to JSONL file

        Returns:
            List of chunk dictionaries
        """
        chunks = []

        with open(chunks_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    chunk = json.loads(line)
                    chunks.append(chunk)
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Invalid JSON at line {line_num} in {chunks_file_path}: {e}"
                    )
                    continue

        return chunks

    def _create_chunk_record(
        self,
        chunk_data: dict[str, Any],
        tool_id: ToolId,
    ) -> dict[str, Any]:
        """Create chunk database record from chunk data.

        Args:
            chunk_data: Chunk dictionary from JSONL
            tool_id: Tool identifier

        Returns:
            Dictionary ready for database insertion
        """
        return {
            "chunk_id": chunk_data["chunk_id"],
            "doc_id": chunk_data["doc_id"],
            "tool_id": tool_id,
            "chunk_text": chunk_data["chunk_text"],
            "chunk_sha256": chunk_data["chunk_sha256"],
            "section_path": chunk_data.get("section_path"),
            "content_type": chunk_data.get("content_type"),
            "system_id": chunk_data.get("system_id"),
            "chunk_index": chunk_data["chunk_index"],
            "active": True,  # New chunks are active by default
            "metadata_json": chunk_data.get("metadata", {}),
        }

    async def _batch_upsert(self, chunk_records: list[dict[str, Any]]) -> None:
        """Batch upsert chunks to database.

        Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE for idempotency.

        Args:
            chunk_records: List of chunk records to upsert
        """
        # PostgreSQL UPSERT (INSERT ... ON CONFLICT DO UPDATE)
        stmt = insert(Chunk).values(chunk_records)

        # On conflict (chunk_id exists), update all fields
        stmt = stmt.on_conflict_do_update(
            index_elements=["chunk_id"],
            set_={
                "chunk_text": stmt.excluded.chunk_text,
                "chunk_sha256": stmt.excluded.chunk_sha256,
                "section_path": stmt.excluded.section_path,
                "content_type": stmt.excluded.content_type,
                "system_id": stmt.excluded.system_id,
                "chunk_index": stmt.excluded.chunk_index,
                "active": stmt.excluded.active,
                "metadata_json": stmt.excluded.metadata_json,
            },
        )

        await self.session.execute(stmt)
        # Note: Commit handled by caller (transaction boundary)

    async def deactivate_chunks(self, doc_id: str) -> int:
        """Deactivate all chunks for a document.

        Used when source is removed (soft delete).

        Args:
            doc_id: Document identifier

        Returns:
            Number of chunks deactivated
        """
        from sqlalchemy import update

        stmt = update(Chunk).where(Chunk.doc_id == doc_id).values(active=False)

        result = await self.session.execute(stmt)
        count = result.rowcount

        logger.info(f"Deactivated {count} chunks for {doc_id}")

        return count
