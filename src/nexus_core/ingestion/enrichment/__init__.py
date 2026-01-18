"""Enrichment subsystem for ingestion pipeline.

Applies content-aware metadata to normalized blocks.
"""

from nexus_core.ingestion.enrichment.content_classifier import ContentClassifier
from nexus_core.ingestion.enrichment.rules_engine import EnrichmentRulesEngine
from nexus_core.ingestion.enrichment.section_path import SectionPathAssigner

__all__ = [
    "EnrichmentRulesEngine",
    "SectionPathAssigner",
    "ContentClassifier",
]
