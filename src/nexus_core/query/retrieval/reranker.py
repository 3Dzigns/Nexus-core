"""Result reranking for hybrid retrieval.

Combines keyword and vector scores using weighted normalization.

Reference: QUERY_POLICY_v1.0.md Section 4.3, FR-030
"""

import logging
from typing import Optional, Union

from nexus_core.query.retrieval.keyword import KeywordResult
from nexus_core.query.retrieval.vector import VectorResult

logger = logging.getLogger(__name__)


class RankedResult:
    """Reranked result with combined score."""

    def __init__(
        self,
        chunk_id: str,
        doc_id: str,
        tool_id: str,
        chunk_text: str,
        combined_score: float,
        system_id: Optional[str] = None,
        feedback_score: Optional[float] = None,
        keyword_score: Optional[float] = None,
        vector_score: Optional[float] = None,
    ):
        """Initialize ranked result.

        Args:
            chunk_id: Chunk identifier
            doc_id: Document identifier
            tool_id: Extraction tool identifier
            chunk_text: Chunk text content
            combined_score: Combined reranked score (0-1)
            keyword_score: Normalized keyword score (0-1)
            vector_score: Normalized vector score (0-1)
        """
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.tool_id = tool_id
        self.chunk_text = chunk_text
        self.combined_score = combined_score
        self.system_id = system_id
        self.feedback_score = feedback_score
        self.keyword_score = keyword_score
        self.vector_score = vector_score

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"RankedResult(chunk_id={self.chunk_id}, "
            f"combined={self.combined_score:.3f}, "
            f"keyword={self.keyword_score:.3f if self.keyword_score else 'N/A'}, "
            f"vector={self.vector_score:.3f if self.vector_score else 'N/A'})"
        )


class Reranker:
    """Reranks retrieval results using weighted score combination.

    Strategy (per QUERY_POLICY_v1.0.md Section 4.3):
    - Normalize keyword ranks to [0, 1]
    - Normalize vector similarities to [0, 1] (already normalized)
    - Combine: score = α * keyword + (1-α) * vector
    - Default α = 0.5 (equal weighting)
    """

    def __init__(self, alpha: float = 0.5):
        """Initialize reranker.

        Args:
            alpha: Keyword weight (0-1). Default 0.5 = equal weighting.
        """
        if not 0 <= alpha <= 1:
            raise ValueError(f"Alpha must be in [0, 1], got {alpha}")

        self.alpha = alpha
        self.vector_weight = 1 - alpha

        logger.info(f"Reranker initialized (α={alpha}, keyword={alpha}, vector={1-alpha})")

    def rerank(
        self,
        keyword_results: Optional[list[KeywordResult]] = None,
        vector_results: Optional[list[VectorResult]] = None,
    ) -> list[RankedResult]:
        """Rerank results using weighted combination.

        Args:
            keyword_results: Keyword retrieval results
            vector_results: Vector retrieval results

        Returns:
            Reranked results sorted by combined score (descending)
        """
        if not keyword_results and not vector_results:
            logger.warning("No results to rerank")
            return []

        # Normalize keyword ranks
        normalized_keyword = self._normalize_keyword_results(keyword_results or [])

        # Vector similarities are already normalized [0, 1]
        normalized_vector = self._normalize_vector_results(vector_results or [])

        # Combine scores
        combined = self._combine_scores(normalized_keyword, normalized_vector)

        # Sort by combined score (descending)
        ranked = sorted(combined, key=lambda x: x.combined_score, reverse=True)

        logger.info(
            f"Reranked {len(ranked)} results "
            f"(keyword={len(keyword_results or [])}, vector={len(vector_results or [])})"
        )

        for i, result in enumerate(ranked[:5]):  # Log top 5
            logger.debug(f"  {i+1}. {result}")

        return ranked

    def _normalize_keyword_results(
        self, results: list[KeywordResult]
    ) -> dict[str, float]:
        """Normalize keyword ranks to [0, 1].

        Args:
            results: Keyword results

        Returns:
            Mapping of chunk_id -> normalized score
        """
        if not results:
            return {}

        # Find min/max ranks for normalization
        ranks = [r.rank for r in results]
        min_rank = min(ranks)
        max_rank = max(ranks)

        # Normalize to [0, 1]
        if max_rank == min_rank:
            # All ranks equal, assign 1.0
            normalized = {r.chunk_id: 1.0 for r in results}
        else:
            normalized = {
                r.chunk_id: (r.rank - min_rank) / (max_rank - min_rank)
                for r in results
            }

        return normalized

    def _normalize_vector_results(self, results: list[VectorResult]) -> dict[str, float]:
        """Extract vector similarities (already normalized [0, 1]).

        Args:
            results: Vector results

        Returns:
            Mapping of chunk_id -> similarity score
        """
        return {r.chunk_id: r.similarity for r in results}

    def _combine_scores(
        self,
        keyword_scores: dict[str, float],
        vector_scores: dict[str, float],
    ) -> list[RankedResult]:
        """Combine keyword and vector scores.

        Note: This is a simplified version that doesn't include chunk metadata.
        The hybrid retriever will need to merge metadata from original results.

        Args:
            keyword_scores: Normalized keyword scores
            vector_scores: Normalized vector scores

        Returns:
            Combined ranked results (metadata populated by caller)
        """
        # Get all unique chunk_ids
        all_chunk_ids = set(keyword_scores.keys()) | set(vector_scores.keys())

        results = []
        for chunk_id in all_chunk_ids:
            k_score = keyword_scores.get(chunk_id, 0.0)
            v_score = vector_scores.get(chunk_id, 0.0)

            # Weighted combination
            combined_score = self.alpha * k_score + self.vector_weight * v_score

            results.append(
                RankedResult(
                    chunk_id=chunk_id,
                    doc_id="",  # Populated by hybrid retriever
                    tool_id="",  # Populated by hybrid retriever
                    chunk_text="",  # Populated by hybrid retriever
                    combined_score=combined_score,
                    system_id=None,
                    feedback_score=None,
                    keyword_score=k_score if k_score > 0 else None,
                    vector_score=v_score if v_score > 0 else None,
                )
            )

        return results
