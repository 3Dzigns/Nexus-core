"""Embedding storage layer for database insertion.

Per INGESTION_ARCHITECTURE_v1.0.md Section 11.3:
- Insert embeddings into embeddings table
- Use pgvector type for vector column
- Link to chunks via chunk_id

Requirements: FR-021
"""

import logging
from typing import Optional

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.models.source import Embedding

logger = logging.getLogger(__name__)


class EmbeddingStorage:
    """Handles embedding database storage operations."""

    def __init__(self, session: AsyncSession):
        """Initialize embedding storage.

        Args:
            session: Database session
        """
        self.session = session

    async def store_embedding(
        self,
        chunk_id: str,
        embedding_vector: list[float],
    ) -> None:
        """Store a single embedding.

        Args:
            chunk_id: Chunk identifier
            embedding_vector: Embedding vector (384 dimensions)

        Uses UPSERT to ensure idempotency.
        """
        # PostgreSQL UPSERT
        stmt = insert(Embedding).values(
            chunk_id=chunk_id,
            embedding=embedding_vector,
        )

        # On conflict (chunk_id exists), update embedding
        stmt = stmt.on_conflict_do_update(
            index_elements=["chunk_id"],
            set_={"embedding": stmt.excluded.embedding},
        )

        await self.session.execute(stmt)

    async def store_embeddings_batch(
        self,
        embeddings_data: list[tuple[str, list[float]]],
    ) -> int:
        """Store multiple embeddings in batch.

        Args:
            embeddings_data: List of (chunk_id, embedding_vector) tuples

        Returns:
            Number of embeddings stored
        """
        if not embeddings_data:
            return 0

        logger.info(f"Storing {len(embeddings_data)} embeddings in batch")

        # Prepare records
        records = [
            {"chunk_id": chunk_id, "embedding": embedding}
            for chunk_id, embedding in embeddings_data
        ]

        # Batch UPSERT
        stmt = insert(Embedding).values(records)

        stmt = stmt.on_conflict_do_update(
            index_elements=["chunk_id"],
            set_={"embedding": stmt.excluded.embedding},
        )

        await self.session.execute(stmt)

        logger.info(f"Stored {len(embeddings_data)} embeddings")

        return len(embeddings_data)

    async def deactivate_embeddings(self, doc_id: str) -> int:
        """Deactivate embeddings for a document.

        Note: Embeddings table doesn't have 'active' flag.
        Instead, we rely on chunks.active flag.
        This method is here for consistency with chunk storage.

        Args:
            doc_id: Document identifier

        Returns:
            Number of embeddings affected (always 0 for now)
        """
        # Embeddings are deactivated implicitly when chunks are deactivated
        # No action needed here
        logger.debug(f"Embeddings deactivation for {doc_id} handled via chunks.active")
        return 0
