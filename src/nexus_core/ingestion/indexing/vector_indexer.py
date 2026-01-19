"""Vector index creation for embeddings.

Per INGESTION_ARCHITECTURE_v1.0.md Section 11.5:
- Create HNSW index on embeddings.embedding column
- Configure index parameters (m=16, ef_construction=64)
- Fallback to IVFFLAT if HNSW unavailable

Requirements: FR-021
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class VectorIndexer:
    """Handles vector index creation for embeddings."""

    def __init__(self, session: AsyncSession):
        """Initialize vector indexer.

        Args:
            session: Database session
        """
        self.session = session

    async def create_hnsw_index(
        self,
        index_name: str = "ix_embeddings_hnsw",
        m: int = 16,
        ef_construction: int = 64,
    ) -> bool:
        """Create HNSW index on embeddings table.

        Args:
            index_name: Name for the index
            m: HNSW parameter (connections per node)
            ef_construction: HNSW parameter (search width during construction)

        Returns:
            True if HNSW index created successfully

        HNSW (Hierarchical Navigable Small World):
        - Fast approximate nearest neighbor search
        - Better recall than IVFFLAT
        - Requires pgvector extension
        """
        try:
            logger.info(
                f"Creating HNSW index: {index_name} "
                f"(m={m}, ef_construction={ef_construction})"
            )

            # Create HNSW index if not exists
            # Uses vector_cosine_ops for cosine distance
            await self.session.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    "ON embeddings USING hnsw (embedding vector_cosine_ops) "
                    f"WITH (m = {m}, ef_construction = {ef_construction})"
                )
            )

            logger.info(f"HNSW index created successfully: {index_name}")
            return True

        except Exception as e:
            logger.warning(f"HNSW index creation failed: {e}")
            return False

    async def create_ivfflat_index(
        self,
        index_name: str = "ix_embeddings_ivfflat",
        lists: int = 100,
    ) -> bool:
        """Create IVFFLAT index on embeddings table (fallback).

        Args:
            index_name: Name for the index
            lists: Number of inverted lists (clusters)

        Returns:
            True if IVFFLAT index created successfully

        IVFFLAT (Inverted File with Flat compression):
        - Faster indexing than HNSW
        - Slightly lower recall
        - Good for smaller datasets
        """
        try:
            logger.info(
                f"Creating IVFFLAT index: {index_name} (lists={lists})"
            )

            # Create IVFFLAT index if not exists
            await self.session.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    "ON embeddings USING ivfflat (embedding vector_cosine_ops) "
                    f"WITH (lists = {lists})"
                )
            )

            logger.info(f"IVFFLAT index created successfully: {index_name}")
            return True

        except Exception as e:
            logger.error(f"IVFFLAT index creation failed: {e}")
            return False

    async def create_vector_index(self) -> bool:
        """Create vector index with automatic fallback.

        Tries HNSW first, falls back to IVFFLAT if unavailable.

        Returns:
            True if any index created successfully
        """
        # Try HNSW first (preferred)
        if await self.create_hnsw_index():
            return True

        # Fallback to IVFFLAT
        logger.warning("HNSW unavailable, falling back to IVFFLAT")
        return await self.create_ivfflat_index()
