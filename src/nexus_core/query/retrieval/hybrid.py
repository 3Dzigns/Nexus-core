"""Hybrid retrieval combining keyword and vector search.

Orchestrates both retrieval methods and reranks results.

Reference: QUERY_POLICY_v1.0.md Section 4.3, FR-030
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import get_settings
from nexus_core.feedback.scoring import apply_feedback_adjustment
from nexus_core.ingestion.embeddings.generator import EmbeddingGenerator
from nexus_core.query.retrieval.keyword import KeywordResult, KeywordRetriever
from nexus_core.query.retrieval.reranker import RankedResult, Reranker
from nexus_core.query.retrieval.vector import VectorResult, VectorRetriever
from nexus_core.query.scope.resolver import QueryScope

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid retrieval combining keyword FTS and vector similarity.

    Execution Strategy:
    1. Run keyword and vector retrieval in parallel
    2. Rerank results using weighted combination
    3. Deduplicate by chunk_id
    4. Return top-k ranked results
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        top_k: int = 10,
        alpha: float = 0.5,
    ):
        """Initialize hybrid retriever.

        Args:
            db: Database session
            embedding_generator: Embedding generator (defaults to new instance)
            top_k: Number of top results to return
            alpha: Keyword weight for reranking (0-1, default 0.5)
        """
        self.db = db
        self.top_k = top_k
        self.feedback_weight = get_settings().feedback_score_weight

        self.keyword_retriever = KeywordRetriever(db, top_k=top_k)
        self.vector_retriever = VectorRetriever(
            db, embedding_generator=embedding_generator, top_k=top_k
        )
        self.reranker = Reranker(alpha=alpha)

    async def retrieve(
        self, query_text: str, scope: QueryScope
    ) -> list[RankedResult]:
        """Retrieve and rerank results using hybrid approach.

        Args:
            query_text: Query text
            scope: Query scope

        Returns:
            Reranked results sorted by combined score
        """
        logger.info(f"Hybrid retrieval (query: {query_text[:100]}, top_k: {self.top_k})")

        # Run both retrievals in parallel
        # Note: Using await sequentially for MVP1
        # TODO: Use asyncio.gather for true parallelism
        keyword_results = await self.keyword_retriever.retrieve(query_text, scope)
        vector_results = await self.vector_retriever.retrieve(query_text, scope)

        # Rerank results
        ranked_results = self.reranker.rerank(keyword_results, vector_results)

        # Merge metadata from original results
        # Build lookup maps for efficient metadata retrieval
        keyword_map = {r.chunk_id: r for r in keyword_results}
        vector_map = {r.chunk_id: r for r in vector_results}

        # Populate metadata for ranked results
        for ranked in ranked_results:
            # Prefer keyword result metadata (arbitrary choice)
            if ranked.chunk_id in keyword_map:
                source = keyword_map[ranked.chunk_id]
                ranked.doc_id = source.doc_id
                ranked.tool_id = source.tool_id
                ranked.chunk_text = source.chunk_text
                ranked.system_id = source.system_id
                ranked.feedback_score = source.feedback_score
            elif ranked.chunk_id in vector_map:
                source = vector_map[ranked.chunk_id]
                ranked.doc_id = source.doc_id
                ranked.tool_id = source.tool_id
                ranked.chunk_text = source.chunk_text
                ranked.system_id = source.system_id
                ranked.feedback_score = source.feedback_score

        apply_feedback_adjustment(ranked_results, weight=self.feedback_weight)
        ranked_results = sorted(
            ranked_results, key=lambda x: x.combined_score, reverse=True
        )

        # Limit to top_k
        final_results = ranked_results[: self.top_k]

        logger.info(
            f"Hybrid retrieval complete: {len(final_results)} results "
            f"(keyword: {len(keyword_results)}, vector: {len(vector_results)})"
        )

        for i, result in enumerate(final_results[:5]):  # Log top 5
            logger.debug(f"  {i+1}. {result}")

        return final_results

    async def retrieve_keyword_only(
        self, query_text: str, scope: QueryScope
    ) -> list[RankedResult]:
        """Retrieve using keyword-only strategy.

        Used for short queries (<10 tokens).

        Args:
            query_text: Query text
            scope: Query scope

        Returns:
            Keyword results as ranked results
        """
        logger.info(f"Keyword-only retrieval (query: {query_text[:100]})")

        keyword_results = await self.keyword_retriever.retrieve(query_text, scope)

        # Convert to RankedResult format
        ranked_results = [
            RankedResult(
                chunk_id=r.chunk_id,
                doc_id=r.doc_id,
                tool_id=r.tool_id,
                chunk_text=r.chunk_text,
                combined_score=r.rank,  # Use rank as score
                system_id=r.system_id,
                feedback_score=r.feedback_score,
                keyword_score=r.rank,
                vector_score=None,
            )
            for r in keyword_results
        ]

        apply_feedback_adjustment(ranked_results, weight=self.feedback_weight)
        ranked_results = sorted(
            ranked_results, key=lambda x: x.combined_score, reverse=True
        )

        return ranked_results[: self.top_k]

    async def retrieve_vector_only(
        self, query_text: str, scope: QueryScope
    ) -> list[RankedResult]:
        """Retrieve using vector-only strategy.

        Used for long semantic queries.

        Args:
            query_text: Query text
            scope: Query scope

        Returns:
            Vector results as ranked results
        """
        logger.info(f"Vector-only retrieval (query: {query_text[:100]})")

        vector_results = await self.vector_retriever.retrieve(query_text, scope)

        # Convert to RankedResult format
        ranked_results = [
            RankedResult(
                chunk_id=r.chunk_id,
                doc_id=r.doc_id,
                tool_id=r.tool_id,
                chunk_text=r.chunk_text,
                combined_score=r.similarity,  # Use similarity as score
                system_id=r.system_id,
                feedback_score=r.feedback_score,
                keyword_score=None,
                vector_score=r.similarity,
            )
            for r in vector_results
        ]

        apply_feedback_adjustment(ranked_results, weight=self.feedback_weight)
        ranked_results = sorted(
            ranked_results, key=lambda x: x.combined_score, reverse=True
        )

        return ranked_results[: self.top_k]
