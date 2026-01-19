"""Keyword-based retrieval using PostgreSQL full-text search.

Uses FTS index with ts_rank for relevance scoring.

Reference: QUERY_POLICY_v1.0.md Section 4.1, FR-029
"""

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.models.source import Chunk, FTSIndex, Source
from nexus_core.query.scope.resolver import QueryScope
from nexus_core.query.scope.source_filter import SourceFilter

logger = logging.getLogger(__name__)


class KeywordResult:
    """Keyword retrieval result."""

    def __init__(
        self,
        chunk_id: str,
        doc_id: str,
        tool_id: str,
        chunk_text: str,
        rank: float,
    ):
        """Initialize keyword result.

        Args:
            chunk_id: Chunk identifier
            doc_id: Document identifier
            tool_id: Extraction tool identifier
            chunk_text: Chunk text content
            rank: FTS rank score
        """
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.tool_id = tool_id
        self.chunk_text = chunk_text
        self.rank = rank

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"KeywordResult(chunk_id={self.chunk_id}, doc_id={self.doc_id}, "
            f"rank={self.rank:.3f})"
        )


class KeywordRetriever:
    """Keyword-based retrieval using PostgreSQL FTS.

    Uses ts_rank for relevance scoring.
    """

    def __init__(self, db: AsyncSession, top_k: int = 10):
        """Initialize keyword retriever.

        Args:
            db: Database session
            top_k: Number of top results to return
        """
        self.db = db
        self.top_k = top_k

    async def retrieve(
        self, query_text: str, scope: QueryScope
    ) -> list[KeywordResult]:
        """Retrieve chunks using keyword FTS.

        Args:
            query_text: Query text
            scope: Query scope

        Returns:
            List of keyword results sorted by rank (descending)
        """
        logger.info(f"Keyword retrieval (query: {query_text[:100]}, top_k: {self.top_k})")

        # Build FTS query using plainto_tsquery
        # This converts query text to tsquery format
        tsquery = func.plainto_tsquery("english", query_text)

        # Build scope-filtered query
        base_query = (
            select(
                Chunk.chunk_id,
                Chunk.doc_id,
                Chunk.tool_id,
                Chunk.chunk_text,
                func.ts_rank(FTSIndex.tsv, tsquery).label("rank"),
            )
            .select_from(Chunk)
            .join(FTSIndex, Chunk.chunk_id == FTSIndex.chunk_id)
            .join(Source, Chunk.doc_id == Source.doc_id)
            .where(FTSIndex.tsv.op("@@")(tsquery))  # FTS match operator
        )

        # Apply scope filters
        query = SourceFilter.build_chunk_query(scope, base_query)

        # Order by rank and limit
        query = query.order_by(func.ts_rank(FTSIndex.tsv, tsquery).desc()).limit(
            self.top_k
        )

        # Execute query
        result = await self.db.execute(query)
        rows = result.all()

        # Convert to KeywordResult objects
        results = [
            KeywordResult(
                chunk_id=row.chunk_id,
                doc_id=row.doc_id,
                tool_id=row.tool_id,
                chunk_text=row.chunk_text,
                rank=row.rank,
            )
            for row in rows
        ]

        logger.info(f"Keyword retrieval found {len(results)} results")

        for i, result in enumerate(results[:5]):  # Log top 5
            logger.debug(f"  {i+1}. {result}")

        return results
