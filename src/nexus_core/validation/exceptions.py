"""Validation exceptions.

Per VALIDATION_PLAN_v1.0.md and INGESTION_VALIDATION_AGENT_PROMPT_v1.0.md:
- Validation failures must be explicit and actionable
- Different error types enable proper error handling
- All exceptions include context for debugging
"""


class ValidationError(Exception):
    """Base exception for all validation errors.

    This is the parent class for all validation-related exceptions.
    Catching this will catch all validation errors.
    """

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationPreconditionError(ValidationError):
    """Raised when validation preconditions are not met.

    Per VALIDATION_PLAN_v1.0.md Section 3:
    - Source must be in INGESTING state
    - No ingestion jobs running
    - Artifact directories must exist

    This is a non-retriable error - validation cannot proceed.
    """
    pass


class ValidationCheckError(ValidationError):
    """Raised when a validation check fails.

    This indicates ingestion produced incorrect or incomplete artifacts.
    The source should transition to ERROR state.
    """

    def __init__(self, check_name: str, message: str, details: dict | None = None):
        super().__init__(message, details)
        self.check_name = check_name


class ValidationReportError(ValidationError):
    """Raised when report generation fails.

    This is a system error - the validation checks may have passed,
    but the validator cannot write the results to disk.
    """
    pass


class ArtifactNotFoundError(ValidationError):
    """Raised when a required artifact is missing.

    Per ARTIFACT_CONTRACT_v1.0.md:
    - All required artifacts must exist
    - Missing artifacts indicate incomplete ingestion

    This is a common validation failure scenario.
    """

    def __init__(self, artifact_path: str, doc_id: str, details: dict | None = None):
        message = f"Required artifact not found: {artifact_path}"
        super().__init__(message, details)
        self.artifact_path = artifact_path
        self.doc_id = doc_id


class GovernanceIntegrityError(ValidationError):
    """Raised when governance state or transitions are invalid.

    Per GOVERNANCE_FLOW_v1.0.md:
    - Source must exist in governance
    - State transitions must follow allowed paths
    - No skipped or illegal transitions

    This indicates a serious problem with the ingestion pipeline.
    """

    def __init__(self, doc_id: str, message: str, details: dict | None = None):
        super().__init__(message, details)
        self.doc_id = doc_id
