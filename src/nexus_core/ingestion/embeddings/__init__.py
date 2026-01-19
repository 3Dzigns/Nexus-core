"""Embeddings subsystem for ingestion pipeline.

Generates vector embeddings for chunks using sentence-transformers.
"""

from nexus_core.ingestion.embeddings.generator import EmbeddingGenerator

__all__ = [
    "EmbeddingGenerator",
]
