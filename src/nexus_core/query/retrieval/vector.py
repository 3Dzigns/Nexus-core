"""Vector-based retrieval using pgvector similarity search.

Uses OpenAI embeddings and cosine similarity (1 - distance).

Reference: QUERY_POLICY_v1.0.md Section 4.2, FR-029
"""

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.ingestion.embeddings.generator import EmbeddingGenerator
from nexus_core.models.source import Chunk, Embedding, Source
from nexus_core.query.scope.resolver import QueryScope
from nexus_core.query.scope.source_filter import SourceFilter

logger = logging.getLogger(__name__)


class VectorResult:
    """Vector retrieval result."""

    def __init__(
        self,
        chunk_id: str,
        doc_id: str,
        tool_id: str,
        chunk_text: str,
        similarity: float,
    ):
        """Initialize vector result.

        Args:
            chunk_id: Chunk identifier
            doc_id: Document identifier
            tool_id: Extraction tool identifier
            chunk_text: Chunk text content
            similarity: Cosine similarity score (0-1)
        """
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.tool_id = tool_id
        self.chunk_text = chunk_text
        self.similarity = similarity

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"VectorResult(chunk_id={self.chunk_id}, doc_id={self.doc_id}, "
            f"similarity={self.similarity:.3f})"
        )


class VectorRetriever:
    """Vector-based retrieval using pgvector.

    Uses cosine similarity for semantic search.
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        top_k: int = 10,
    ):
        """Initialize vector retriever.

        Args:
            db: Database session
            embedding_generator: Embedding generator (defaults to new instance)
            top_k: Number of top results to return
        """
        self.db = db
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.top_k = top_k

    async def retrieve(
        self, query_text: str, scope: QueryScope
    ) -> list[VectorResult]:
        """Retrieve chunks using vector similarity.

        Args:
            query_text: Query text
            scope: Query scope

        Returns:
            List of vector results sorted by similarity (descending)
        """
        logger.info(f"Vector retrieval (query: {query_text[:100]}, top_k: {self.top_k})")

        # Generate query embedding
        query_embedding = await self.embedding_generator.generate_embedding(query_text)
        if not query_embedding:
            logger.warning("Failed to generate query embedding")
            return []

        logger.debug(f"Generated query embedding ({len(query_embedding)} dimensions)")

        # Build pgvector similarity query
        # <=> is the cosine distance operator (0 = identical, 2 = opposite)
        # similarity = 1 - distance
        distance_expr = Embedding.embedding.cosine_distance(query_embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        base_query = (
            select(
                Chunk.chunk_id,
                Chunk.doc_id,
                Chunk.tool_id,
                Chunk.chunk_text,
                similarity_expr,
            )
            .select_from(Chunk)
            .join(Embedding, Chunk.chunk_id == Embedding.chunk_id)
            .join(Source, Chunk.doc_id == Source.doc_id)
        )

        # Apply scope filters
        query = SourceFilter.build_chunk_query(scope, base_query)

        # Order by similarity (descending) and limit
        query = query.order_by(similarity_expr.desc()).limit(self.top_k)

        # Execute query
        result = await self.db.execute(query)
        rows = result.all()

        # Convert to VectorResult objects
        results = [
            VectorResult(
                chunk_id=row.chunk_id,
                doc_id=row.doc_id,
                tool_id=row.tool_id,
                chunk_text=row.chunk_text,
                similarity=row.similarity,
            )
            for row in rows
        ]

        logger.info(f"Vector retrieval found {len(results)} results")

        for i, result in enumerate(results[:5]):  # Log top 5
            logger.debug(f"  {i+1}. {result}")

        return results
