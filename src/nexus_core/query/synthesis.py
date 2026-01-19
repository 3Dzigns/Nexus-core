"""Query synthesis using OpenAI GPT-4.

Synthesizes responses from retrieved chunks using LLM.

Reference: QUERY_POLICY_v1.0.md Section 5, Phase 6.7
"""

import logging
from typing import Optional

from openai import AsyncOpenAI, OpenAIError

from nexus_core.config import get_settings
from nexus_core.query.retrieval.reranker import RankedResult

logger = logging.getLogger(__name__)


class SynthesisResult:
    """Result of query synthesis."""

    def __init__(
        self,
        response_text: str,
        chunks_used: list[RankedResult],
        model: str,
        tokens_used: Optional[int] = None,
    ):
        """Initialize synthesis result.

        Args:
            response_text: Synthesized response text
            chunks_used: Chunks used for synthesis
            model: Model used for synthesis
            tokens_used: Total tokens used (if available)
        """
        self.response_text = response_text
        self.chunks_used = chunks_used
        self.model = model
        self.tokens_used = tokens_used

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"SynthesisResult(model={self.model}, "
            f"chunks={len(self.chunks_used)}, tokens={self.tokens_used})"
        )


class QuerySynthesizer:
    """Synthesizes query responses using OpenAI GPT-4.

    Uses retrieved chunks as context for LLM synthesis.
    """

    # System prompt for synthesis
    SYSTEM_PROMPT = """You are an AI assistant helping users with tabletop RPG knowledge queries.

Your role:
- Synthesize accurate responses from provided source material
- Cite sources when making claims
- Stay faithful to the source content
- Acknowledge when information is incomplete or unavailable

Format rules:
- Use clear, concise language
- Structure responses with paragraphs or lists as appropriate
- Reference sources naturally in your response
- If sources don't contain the answer, say so clearly"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 500,
    ):
        """Initialize query synthesizer.

        Args:
            api_key: OpenAI API key (defaults to config)
            model: OpenAI chat model (defaults to config)
            max_tokens: Maximum tokens in response
        """
        settings = get_settings()

        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable."
            )

        self.model = model or settings.openai_chat_model
        self.max_tokens = max_tokens

        self.client = AsyncOpenAI(api_key=self.api_key)

        logger.info(f"Query synthesizer initialized (model: {self.model})")

    async def synthesize(
        self, query_text: str, chunks: list[RankedResult]
    ) -> SynthesisResult:
        """Synthesize response from query and retrieved chunks.

        Args:
            query_text: Original query text
            chunks: Retrieved and ranked chunks

        Returns:
            Synthesis result with response text

        Raises:
            OpenAIError: If synthesis fails
        """
        logger.info(f"Synthesizing response (query: {query_text[:100]}, chunks: {len(chunks)})")

        # Build context from chunks
        context = self._build_context(chunks)

        # Build user prompt
        user_prompt = self._build_user_prompt(query_text, context)

        # Call OpenAI API
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=0.7,
            )

            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None

            result = SynthesisResult(
                response_text=response_text,
                chunks_used=chunks,
                model=self.model,
                tokens_used=tokens_used,
            )

            logger.info(f"Synthesis complete: {result}")

            return result

        except OpenAIError as e:
            logger.error(f"Synthesis failed: {e}")
            raise

    def _build_context(self, chunks: list[RankedResult]) -> str:
        """Build context string from chunks.

        Args:
            chunks: Retrieved chunks

        Returns:
            Context string for LLM
        """
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            # Include chunk metadata for citation
            context_parts.append(
                f"[Source {i}: {chunk.doc_id} | {chunk.tool_id}]\n{chunk.chunk_text}\n"
            )

        context = "\n---\n".join(context_parts)

        logger.debug(f"Built context from {len(chunks)} chunks ({len(context)} chars)")

        return context

    def _build_user_prompt(self, query_text: str, context: str) -> str:
        """Build user prompt with query and context.

        Args:
            query_text: Original query
            context: Context from chunks

        Returns:
            User prompt for LLM
        """
        prompt = f"""Based on the following source material, please answer this question:

Question: {query_text}

Source Material:
{context}

Please provide a clear, accurate answer based only on the information in the sources. If the sources don't contain enough information to answer the question, say so."""

        return prompt
