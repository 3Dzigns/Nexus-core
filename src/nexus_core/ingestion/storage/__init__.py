"""Storage subsystem for ingestion pipeline.

Handles chunk storage, embedding generation, and indexing.
"""

from nexus_core.ingestion.storage.chunk_storage import ChunkStorage
from nexus_core.ingestion.storage.embedding_storage import EmbeddingStorage

__all__ = [
    "ChunkStorage",
    "EmbeddingStorage",
]
