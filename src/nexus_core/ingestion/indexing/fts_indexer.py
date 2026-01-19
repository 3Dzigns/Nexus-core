"""Full-text search indexing for chunks.

Per INGESTION_ARCHITECTURE_v1.0.md Section 11.4:
- Create tsvector from chunk_text
- Insert into fts_index table
- Create GIN index if not exists

Requirements: FR-022
"""

import logging

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.models.source import FTSIndex

logger = logging.getLogger(__name__)


class FTSIndexer:
    """Handles full-text search indexing for chunks."""

    def __init__(self, session: AsyncSession):
        """Initialize FTS indexer.

        Args:
            session: Database session
        """
        self.session = session

    async def index_chunk(self, chunk_id: str, chunk_text: str) -> None:
        """Create FTS index entry for a chunk.

        Args:
            chunk_id: Chunk identifier
            chunk_text: Text content to index

        Uses PostgreSQL to_tsvector() for text vectorization.
        """
        # PostgreSQL UPSERT with tsvector generation
        stmt = insert(FTSIndex).values(
            chunk_id=chunk_id,
            tsv=text(f"to_tsvector('english', :text)"),
        )

        # On conflict, update tsvector
        stmt = stmt.on_conflict_do_update(
            index_elements=["chunk_id"],
            set_={"tsv": text(f"to_tsvector('english', :text)")},
        )

        await self.session.execute(stmt, {"text": chunk_text})

    async def index_chunks_batch(
        self,
        chunks_data: list[tuple[str, str]],
    ) -> int:
        """Index multiple chunks in batch.

        Args:
            chunks_data: List of (chunk_id, chunk_text) tuples

        Returns:
            Number of chunks indexed
        """
        if not chunks_data:
            return 0

        logger.info(f"Indexing {len(chunks_data)} chunks for FTS")

        # Process in batches to avoid large SQL statements
        for chunk_id, chunk_text in chunks_data:
            await self.index_chunk(chunk_id, chunk_text)

        logger.info(f"Indexed {len(chunks_data)} chunks for FTS")

        return len(chunks_data)

    async def ensure_gin_index(self) -> None:
        """Ensure GIN index exists on fts_index.tsv column.

        Creates index if it doesn't exist.
        Uses IF NOT EXISTS to avoid errors on subsequent runs.
        """
        # Check if index exists
        index_name = "ix_fts_index_tsv"

        # Create GIN index if not exists
        await self.session.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS {index_name} "
                "ON fts_index USING gin(tsv)"
            )
        )

        logger.info(f"GIN index ensured: {index_name}")
