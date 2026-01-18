"""Chunking subsystem for ingestion pipeline.

Splits enriched manifests into chunks for storage and retrieval.
"""

from nexus_core.ingestion.chunking.chunker import Chunker, ChunkingConfig

__all__ = [
    "Chunker",
    "ChunkingConfig",
]
