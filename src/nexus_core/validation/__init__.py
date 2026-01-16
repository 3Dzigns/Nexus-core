"""Nexus Core validation subsystem.

This module implements the Ingestion Validation Agent per:
- INGESTION_VALIDATION_AGENT_PROMPT_v1.0.md (agent role and responsibilities)
- VALIDATION_PLAN_v1.0.md (validation requirements and checks)
- ARTIFACT_CONTRACT_v1.0.md (artifact structure and expectations)

The validator is an independent auditor that verifies ingestion correctness
before certifying sources as INGESTED.

Key principles:
- Non-destructive: Reads artifacts, never modifies them
- All-or-nothing: Partial success is forbidden
- Evidence-based: Validation relies on observable artifacts
- Deterministic: Same artifacts → same result
- Hard gate: Validation is the only path to INGESTED status
"""

from nexus_core.validation.exceptions import (
    ArtifactNotFoundError,
    GovernanceIntegrityError,
    ValidationCheckError,
    ValidationError,
    ValidationPreconditionError,
    ValidationReportError,
)
from nexus_core.validation.validator import ValidationResult, Validator

__all__ = [
    # Exceptions
    "ValidationError",
    "ValidationPreconditionError",
    "ValidationCheckError",
    "ValidationReportError",
    "ArtifactNotFoundError",
    "GovernanceIntegrityError",
    # Core
    "Validator",
    "ValidationResult",
]
