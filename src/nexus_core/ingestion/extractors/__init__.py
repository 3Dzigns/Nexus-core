"""Extraction subsystem for Nexus Core ingestion.

Provides dual extraction pipeline using Docling and Unstructured.io libraries.
"""

from nexus_core.ingestion.extractors.asset_handler import AssetHandler
from nexus_core.ingestion.extractors.base import (
    ExtractionError,
    ExtractionResult,
    Extractor,
)
from nexus_core.ingestion.extractors.docling_extractor import DoclingExtractor
from nexus_core.ingestion.extractors.original_source import (
    write_original_source_artifact,
)
from nexus_core.ingestion.extractors.unstructured_extractor import UnstructuredExtractor

__all__ = [
    # Base
    "Extractor",
    "ExtractionResult",
    "ExtractionError",
    # Extractors
    "DoclingExtractor",
    "UnstructuredExtractor",
    # Utilities
    "AssetHandler",
    "write_original_source_artifact",
]
