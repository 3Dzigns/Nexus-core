"""Response assembly and formatting.

Assembles query responses with citations per OPENAPI_v1.0.md schema.

Reference: OPENAPI_v1.0.md POST /query response, FR-031
"""

import logging
from typing import Optional

from nexus_core.query.classification.classifier import ClassificationResult
from nexus_core.query.classification.rules import RulePath
from nexus_core.query.retrieval.reranker import RankedResult
from nexus_core.query.schemas import QueryResponse, SourceCitation
from nexus_core.query.synthesis import SynthesisResult

logger = logging.getLogger(__name__)


class ResponseBuilder:
    """Builds QueryResponse objects with proper formatting and citations.

    Handles all response types:
    - No sources (friendly message)
    - Direct commands (local execution)
    - Single chunk (direct return)
    - Synthesis (LLM response with citations)
    """

    @staticmethod
    def build_no_sources_response(
        classification: ClassificationResult,
    ) -> QueryResponse:
        """Build response for no-sources scenario.

        Args:
            classification: Classification result

        Returns:
            Query response with friendly message
        """
        response_text = (
            "No authoritative sources are currently available in your context. "
            "Please add sources to your game or user library to enable queries."
        )

        logger.info("Built no-sources response")

        return QueryResponse(
            response_text=response_text,
            sources=[],
            classification=classification.classification,
            rule_path=classification.rule_path.value,
        )

    @staticmethod
    def build_direct_command_response(
        classification: ClassificationResult,
        doc_ids: list[str],
    ) -> QueryResponse:
        """Build response for direct command execution.

        Args:
            classification: Classification result
            doc_ids: List of accessible doc_ids

        Returns:
            Query response with source list
        """
        if not doc_ids:
            response_text = "No sources found."
        else:
            response_text = f"Active sources ({len(doc_ids)}):\n"
            for doc_id in doc_ids:
                response_text += f"  - {doc_id}\n"

        # Create citations for listed sources
        citations = [
            SourceCitation(doc_id=doc_id, chunk_id="", tool_id="")
            for doc_id in doc_ids
        ]

        logger.info(f"Built direct command response ({len(doc_ids)} sources)")

        return QueryResponse(
            response_text=response_text,
            sources=citations,
            classification=classification.classification,
            rule_path=classification.rule_path.value,
        )

    @staticmethod
    def build_single_chunk_response(
        classification: ClassificationResult,
        chunk: RankedResult,
    ) -> QueryResponse:
        """Build response for single high-confidence chunk.

        Args:
            classification: Classification result
            chunk: Single retrieved chunk

        Returns:
            Query response with chunk text and citation
        """
        response_text = chunk.chunk_text

        citation = SourceCitation(
            doc_id=chunk.doc_id,
            chunk_id=chunk.chunk_id,
            tool_id=chunk.tool_id,
        )

        logger.info(f"Built single-chunk response (chunk: {chunk.chunk_id})")

        return QueryResponse(
            response_text=response_text,
            sources=[citation],
            classification=classification.classification,
            rule_path=classification.rule_path.value,
        )

    @staticmethod
    def build_synthesis_response(
        classification: ClassificationResult,
        synthesis: SynthesisResult,
    ) -> QueryResponse:
        """Build response from synthesis result.

        Args:
            classification: Classification result
            synthesis: Synthesis result

        Returns:
            Query response with synthesized text and citations
        """
        response_text = synthesis.response_text

        # Create citations from chunks used in synthesis
        citations = [
            SourceCitation(
                doc_id=chunk.doc_id,
                chunk_id=chunk.chunk_id,
                tool_id=chunk.tool_id,
            )
            for chunk in synthesis.chunks_used
        ]

        logger.info(
            f"Built synthesis response "
            f"({len(citations)} sources, {synthesis.tokens_used} tokens)"
        )

        return QueryResponse(
            response_text=response_text,
            sources=citations,
            classification=classification.classification,
            rule_path=classification.rule_path.value,
        )

    @staticmethod
    def build_retrieval_response(
        classification: ClassificationResult,
        chunks: list[RankedResult],
    ) -> QueryResponse:
        """Build response from retrieval results (no synthesis).

        Returns top chunks as response.

        Args:
            classification: Classification result
            chunks: Retrieved chunks

        Returns:
            Query response with top chunks
        """
        if not chunks:
            response_text = "No relevant information found."
            citations = []
        else:
            # Format top chunks
            response_text = "Top results:\n\n"
            for i, chunk in enumerate(chunks[:3], 1):  # Top 3
                response_text += f"{i}. {chunk.chunk_text[:200]}...\n\n"

            # Create citations
            citations = [
                SourceCitation(
                    doc_id=chunk.doc_id,
                    chunk_id=chunk.chunk_id,
                    tool_id=chunk.tool_id,
                )
                for chunk in chunks
            ]

        logger.info(f"Built retrieval response ({len(chunks)} chunks)")

        return QueryResponse(
            response_text=response_text,
            sources=citations,
            classification=classification.classification,
            rule_path=classification.rule_path.value,
        )
