"""Canonical schemas for ingestion pipeline.

Per ARTIFACT_CONTRACT_v1.0.md Section 5.3:
- Normalized manifests use canonical internal schema
- Tool-separated but structurally consistent
- Enables downstream processing uniformity
"""

from nexus_core.ingestion.schemas.block import CanonicalBlock

__all__ = [
    "CanonicalBlock",
]
