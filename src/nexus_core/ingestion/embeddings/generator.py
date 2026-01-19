"""Embedding generation using OpenAI API.

Per INGESTION_ARCHITECTURE_v1.0.md Section 11.2:
- Use OpenAI text-embedding-3-small (1536 dimensions)
- Generate embeddings for chunk_text
- Batch processing for efficiency (up to 100 texts per request)
- Retry logic (max 3 attempts)
- Skip empty text chunks

Requirements: FR-021, TOOL_VERSIONS_v1.0.md
"""

import logging
from typing import Optional

from openai import AsyncOpenAI, OpenAIError

from nexus_core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates vector embeddings for text chunks using OpenAI API.

    Uses text-embedding-3-small model (1536 dimensions).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        batch_size: int = 100,
        max_retries: int = 3,
    ):
        """Initialize embedding generator.

        Args:
            api_key: OpenAI API key (defaults to config)
            model: OpenAI embedding model (defaults to config)
            batch_size: Batch size for processing (max 100 for OpenAI)
            max_retries: Maximum retry attempts on failure
        """
        settings = get_settings()

        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable."
            )

        self.model = model or settings.openai_embedding_model
        self.batch_size = min(batch_size, 100)  # OpenAI API limit
        self.max_retries = max_retries
        self.dimensions = settings.embedding_dimensions

        self.client = AsyncOpenAI(api_key=self.api_key)

        logger.info(
            f"Embedding generator initialized "
            f"(model: {self.model}, dimensions: {self.dimensions})"
        )

    async def generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1536 dimensions), or None if text is empty

        Raises:
            OpenAIError: If embedding generation fails after retries
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        for attempt in range(self.max_retries):
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=text,
                    encoding_format="float"
                )

                embedding = response.data[0].embedding

                logger.debug(
                    f"Generated embedding for text (length: {len(text)}, "
                    f"dimensions: {len(embedding)})"
                )

                return embedding

            except OpenAIError as e:
                logger.warning(
                    f"Embedding generation failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt == self.max_retries - 1:
                    raise

        return None

    async def generate_embeddings_batch(
        self,
        texts: list[str],
    ) -> list[Optional[list[float]]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (one per text)

        Note:
            OpenAI API supports up to 100 texts per request.
            Larger batches are automatically split.
        """
        if not texts:
            return []

        # Filter out empty texts but maintain original indices
        text_map = {}  # index -> text
        for i, text in enumerate(texts):
            if text and text.strip():
                text_map[i] = text

        if not text_map:
            return [None] * len(texts)

        # Process in batches of up to batch_size
        indices = list(text_map.keys())
        embeddings_map = {}  # index -> embedding

        for batch_start in range(0, len(indices), self.batch_size):
            batch_indices = indices[batch_start : batch_start + self.batch_size]
            batch_texts = [text_map[i] for i in batch_indices]

            for attempt in range(self.max_retries):
                try:
                    response = await self.client.embeddings.create(
                        model=self.model,
                        input=batch_texts,
                        encoding_format="float"
                    )

                    # Map embeddings back to original indices
                    for i, embedding_data in enumerate(response.data):
                        original_idx = batch_indices[i]
                        embeddings_map[original_idx] = embedding_data.embedding

                    logger.debug(
                        f"Generated {len(batch_texts)} embeddings "
                        f"(batch {batch_start // self.batch_size + 1})"
                    )

                    break  # Success, exit retry loop

                except OpenAIError as e:
                    logger.warning(
                        f"Batch embedding failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    if attempt == self.max_retries - 1:
                        raise

        # Reconstruct full list with Nones for empty texts
        result = [embeddings_map.get(i) for i in range(len(texts))]

        return result
