"""Normalization subsystem for ingestion pipeline.

Converts extractor-specific outputs to canonical block schema.
"""

from nexus_core.ingestion.normalization.docling_normalizer import DoclingNormalizer
from nexus_core.ingestion.normalization.unstructured_normalizer import (
    UnstructuredNormalizer,
)

__all__ = [
    "DoclingNormalizer",
    "UnstructuredNormalizer",
]
