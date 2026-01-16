"""Validation API endpoints.

Provides REST API for triggering and monitoring validation runs.

Per INGESTION_VALIDATION_AGENT_PROMPT_v1.0.md:
- Validation can be triggered manually via API
- Returns validation status and report path
- Includes error handling for preconditions and failures
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import get_settings, Settings
from nexus_core.db.session import get_async_session
from nexus_core.models.source import ValidationStatus
from nexus_core.validation import Validator, ValidationPreconditionError, ValidationError

router = APIRouter(prefix="/validation", tags=["validation"])


# Response models
class ValidationResponse(BaseModel):
    """Validation API response.

    Attributes:
        doc_id: Document identifier that was validated
        run_id: Validation run identifier (UUID)
        status: PASS or FAIL
        message: Human-readable status message
        report_path: Path to JSON validation report
    """

    doc_id: str
    run_id: str
    status: str  # "PASS" or "FAIL"
    message: str
    report_path: str


class ErrorResponse(BaseModel):
    """Error response model.

    Attributes:
        error: Error type/category
        message: Human-readable error message
        details: Additional error context
    """

    error: str
    message: str
    details: dict | None = None


@router.post(
    "/{doc_id}",
    response_model=ValidationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Precondition failed"},
        404: {"model": ErrorResponse, "description": "Source not found"},
        500: {"model": ErrorResponse, "description": "Validation error"},
    },
    summary="Run validation for a source",
    description="""
    Trigger validation for a source document.

    Per VALIDATION_PLAN_v1.0.md, validation:
    - Verifies all 9 mandatory checks
    - Generates JSON + Markdown reports
    - Updates governance state (INGESTING → INGESTED or ERROR)
    - Returns validation status and report path

    **Preconditions:**
    - Source must exist in governance
    - Source state must be INGESTING
    - Artifact directories must exist

    **Status codes:**
    - 200: Validation completed (check status field for PASS/FAIL)
    - 400: Preconditions not met (e.g., source not in INGESTING state)
    - 404: Source not found
    - 500: Validation process error
    """,
)
async def validate_source(
    doc_id: str,
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
) -> ValidationResponse:
    """Run validation for a source.

    Args:
        doc_id: Document identifier to validate
        session: Async database session (injected)
        settings: Application settings (injected)

    Returns:
        ValidationResponse with status and report path

    Raises:
        HTTPException: On validation errors or precondition failures
    """
    try:
        # Create validator instance
        validator = Validator(session=session, settings=settings)

        # Run validation
        result = await validator.validate(doc_id)

        # Return success response
        return ValidationResponse(
            doc_id=result.doc_id,
            run_id=result.run_id,
            status=result.status.value,
            message=(
                "Validation passed: source certified as INGESTED"
                if result.status == ValidationStatus.PASS
                else f"Validation failed: {sum(1 for c in result.checks if not c.passed)} check(s) failed"
            ),
            report_path=result.report_path,
        )

    except ValidationPreconditionError as e:
        # Preconditions not met (400 Bad Request)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "precondition_failed",
                "message": e.message,
                "details": e.details,
            },
        )

    except ValidationError as e:
        # Validation process error (500 Internal Server Error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "validation_error",
                "message": e.message,
                "details": e.details,
            },
        )

    except Exception as e:
        # Unexpected error (500 Internal Server Error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": f"Unexpected error during validation: {str(e)}",
                "details": {"doc_id": doc_id, "error_type": type(e).__name__},
            },
        )
