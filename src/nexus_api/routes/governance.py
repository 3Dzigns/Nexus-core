"""Governance API endpoints for admin source management.

Provides REST API for admin actions on source governance workflow.

Per GOVERNANCE_FLOW_v1.0.md and INGESTION_ARCHITECTURE_v1.0.md:
- Approve/deny sources for ingestion
- Handle duplicate decisions (IGNORE_DUPLICATE | ALLOW_SEPARATE_INSTANCE)
- Reopen denied sources for reconsideration
- All transitions validated via governance state machine

Requirements: FR-004, FR-006, FR-007
"""

import logging
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.db.session import get_async_session
from nexus_core.governance.state_machine import (
    GovernanceStateMachine,
    IllegalTransitionError,
    OptimisticLockError,
)
from nexus_core.ingestion.queue import enqueue_ingestion_job
from nexus_core.models.source import (
    DuplicateDecision,
    DuplicateDecisionType,
    GovernanceStatus,
    Source,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/governance", tags=["governance"])


# Request/Response models
class ApproveRequest(BaseModel):
    """Request to approve a source for ingestion."""

    admin_user_id: str  # Admin identifier for audit trail
    expected_version: int | None = None  # For optimistic locking


class DenyRequest(BaseModel):
    """Request to deny a source."""

    admin_user_id: str
    reason: str | None = None  # Optional denial reason
    expected_version: int | None = None


class ReopenRequest(BaseModel):
    """Request to reopen a denied source."""

    admin_user_id: str
    expected_version: int | None = None


class DuplicateDecisionRequest(BaseModel):
    """Request to make a duplicate decision."""

    admin_user_id: str
    decision: DuplicateDecisionType
    expected_version: int | None = None


class GovernanceResponse(BaseModel):
    """Response for governance actions."""

    doc_id: str
    status: str  # Current governance status
    state_version: int  # Current version for optimistic locking
    message: str


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    message: str
    details: dict | None = None


@router.post(
    "/{doc_id}/approve",
    response_model=GovernanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Source not found"},
        409: {"model": ErrorResponse, "description": "Illegal transition or concurrent modification"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Approve source for ingestion",
    description="""
    Approve a source for ingestion processing.

    Per FR-004, sources require explicit admin approval before ingestion.
    Valid transitions:
    - PENDING_APPROVAL → APPROVED
    - DUPLICATE_DETECTED → APPROVED (via ALLOW_SEPARATE_INSTANCE decision)

    **Preconditions:**
    - Source must be in PENDING_APPROVAL or DUPLICATE_DETECTED status
    - Admin must have approval permissions

    **Status codes:**
    - 200: Approval successful
    - 404: Source not found
    - 409: Illegal transition or concurrent modification
    - 500: Internal error
    """,
)
async def approve_source(
    doc_id: str,
    request: ApproveRequest,
    session: AsyncSession = Depends(get_async_session),
) -> GovernanceResponse:
    """Approve a source for ingestion.

    Args:
        doc_id: Document identifier
        request: Approval request with admin_user_id
        session: Database session (injected)

    Returns:
        GovernanceResponse with updated status

    Raises:
        HTTPException: On validation errors or state machine violations
    """
    try:
        state_machine = GovernanceStateMachine(session)

        # Execute transition to APPROVED
        source = await state_machine.transition(
            doc_id=doc_id,
            to_status=GovernanceStatus.APPROVED,
            triggered_by=request.admin_user_id,
            expected_version=request.expected_version,
            metadata={"action": "approve", "admin_user_id": request.admin_user_id},
        )

        await session.commit()

        # Enqueue ingestion job for worker processing
        await enqueue_ingestion_job(
            doc_id=source.doc_id,
            source_sha256=source.source_sha256,
            original_filename=source.original_filename,
            current_path=source.current_path,
            system_id=source.system_id,
            game_id=source.game_id,
            owner_user_id=source.owner_user_id,
        )

        logger.info(
            f"Source approved: {doc_id} by {request.admin_user_id} "
            f"(version: {source.state_version})"
        )

        return GovernanceResponse(
            doc_id=source.doc_id,
            status=source.status.value,
            state_version=source.state_version,
            message="Source approved for ingestion",
        )

    except ValueError as e:
        # Source not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "source_not_found",
                "message": str(e),
                "details": {"doc_id": doc_id},
            },
        )

    except IllegalTransitionError as e:
        # Illegal state transition
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "illegal_transition",
                "message": e.message,
                "details": {
                    "doc_id": doc_id,
                    "from_status": e.from_status.value if e.from_status else None,
                    "to_status": e.to_status.value,
                },
            },
        )

    except OptimisticLockError as e:
        # Concurrent modification detected
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "concurrent_modification",
                "message": e.message,
                "details": {
                    "doc_id": e.doc_id,
                    "expected_version": e.expected_version,
                    "actual_version": e.actual_version,
                },
            },
        )

    except Exception as e:
        logger.error(f"Error approving source {doc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": f"Unexpected error during approval: {str(e)}",
                "details": {"doc_id": doc_id},
            },
        )


@router.post(
    "/{doc_id}/deny",
    response_model=GovernanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Source not found"},
        409: {"model": ErrorResponse, "description": "Illegal transition or concurrent modification"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Deny source ingestion",
    description="""
    Deny a source from being ingested.

    Per FR-007, denied sources remain visible for audit and can be reopened.
    Valid transition: PENDING_APPROVAL → DENIED

    **Preconditions:**
    - Source must be in PENDING_APPROVAL status
    - Admin must have denial permissions

    **Status codes:**
    - 200: Denial successful
    - 404: Source not found
    - 409: Illegal transition or concurrent modification
    - 500: Internal error
    """,
)
async def deny_source(
    doc_id: str,
    request: DenyRequest,
    session: AsyncSession = Depends(get_async_session),
) -> GovernanceResponse:
    """Deny a source from ingestion.

    Args:
        doc_id: Document identifier
        request: Denial request with admin_user_id and optional reason
        session: Database session (injected)

    Returns:
        GovernanceResponse with updated status

    Raises:
        HTTPException: On validation errors or state machine violations
    """
    try:
        state_machine = GovernanceStateMachine(session)

        # Execute transition to DENIED
        metadata = {
            "action": "deny",
            "admin_user_id": request.admin_user_id,
        }
        if request.reason:
            metadata["denial_reason"] = request.reason

        source = await state_machine.transition(
            doc_id=doc_id,
            to_status=GovernanceStatus.DENIED,
            triggered_by=request.admin_user_id,
            expected_version=request.expected_version,
            metadata=metadata,
        )

        await session.commit()

        logger.info(
            f"Source denied: {doc_id} by {request.admin_user_id} "
            f"(reason: {request.reason or 'not specified'})"
        )

        return GovernanceResponse(
            doc_id=source.doc_id,
            status=source.status.value,
            state_version=source.state_version,
            message=f"Source denied: {request.reason or 'No reason provided'}",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "source_not_found",
                "message": str(e),
                "details": {"doc_id": doc_id},
            },
        )

    except IllegalTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "illegal_transition",
                "message": e.message,
                "details": {
                    "doc_id": doc_id,
                    "from_status": e.from_status.value if e.from_status else None,
                    "to_status": e.to_status.value,
                },
            },
        )

    except OptimisticLockError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "concurrent_modification",
                "message": e.message,
                "details": {
                    "doc_id": e.doc_id,
                    "expected_version": e.expected_version,
                    "actual_version": e.actual_version,
                },
            },
        )

    except Exception as e:
        logger.error(f"Error denying source {doc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": f"Unexpected error during denial: {str(e)}",
                "details": {"doc_id": doc_id},
            },
        )


@router.post(
    "/{doc_id}/reopen",
    response_model=GovernanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Source not found"},
        409: {"model": ErrorResponse, "description": "Illegal transition or concurrent modification"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Reopen denied source",
    description="""
    Reopen a denied source for reconsideration.

    Per FR-007, denied sources can be reopened to allow admin to reconsider.
    Valid transition: DENIED → PENDING_APPROVAL

    **Preconditions:**
    - Source must be in DENIED status
    - Admin must have reopen permissions

    **Status codes:**
    - 200: Reopen successful
    - 404: Source not found
    - 409: Illegal transition or concurrent modification
    - 500: Internal error
    """,
)
async def reopen_source(
    doc_id: str,
    request: ReopenRequest,
    session: AsyncSession = Depends(get_async_session),
) -> GovernanceResponse:
    """Reopen a denied source for reconsideration.

    Args:
        doc_id: Document identifier
        request: Reopen request with admin_user_id
        session: Database session (injected)

    Returns:
        GovernanceResponse with updated status

    Raises:
        HTTPException: On validation errors or state machine violations
    """
    try:
        state_machine = GovernanceStateMachine(session)

        # Execute transition to PENDING_APPROVAL
        source = await state_machine.transition(
            doc_id=doc_id,
            to_status=GovernanceStatus.PENDING_APPROVAL,
            triggered_by=request.admin_user_id,
            expected_version=request.expected_version,
            metadata={"action": "reopen", "admin_user_id": request.admin_user_id},
        )

        await session.commit()

        logger.info(
            f"Source reopened: {doc_id} by {request.admin_user_id} "
            f"(version: {source.state_version})"
        )

        return GovernanceResponse(
            doc_id=source.doc_id,
            status=source.status.value,
            state_version=source.state_version,
            message="Source reopened for reconsideration",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "source_not_found",
                "message": str(e),
                "details": {"doc_id": doc_id},
            },
        )

    except IllegalTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "illegal_transition",
                "message": e.message,
                "details": {
                    "doc_id": doc_id,
                    "from_status": e.from_status.value if e.from_status else None,
                    "to_status": e.to_status.value,
                },
            },
        )

    except OptimisticLockError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "concurrent_modification",
                "message": e.message,
                "details": {
                    "doc_id": e.doc_id,
                    "expected_version": e.expected_version,
                    "actual_version": e.actual_version,
                },
            },
        )

    except Exception as e:
        logger.error(f"Error reopening source {doc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": f"Unexpected error during reopen: {str(e)}",
                "details": {"doc_id": doc_id},
            },
        )


@router.post(
    "/{doc_id}/duplicate-decision",
    response_model=GovernanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Source not found"},
        409: {"model": ErrorResponse, "description": "Illegal transition or concurrent modification"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Make duplicate decision",
    description="""
    Make an admin decision on a duplicate source.

    Per FR-005, duplicate sources require explicit admin decision:
    - IGNORE_DUPLICATE: Transition to PENDING_APPROVAL (treat as regular source)
    - ALLOW_SEPARATE_INSTANCE: Transition to APPROVED (allow as separate copy)

    Valid transition: DUPLICATE_DETECTED → (PENDING_APPROVAL | APPROVED)

    **Preconditions:**
    - Source must be in DUPLICATE_DETECTED status
    - Admin must have duplicate decision permissions

    **Status codes:**
    - 200: Decision recorded successfully
    - 404: Source not found
    - 409: Illegal transition or concurrent modification
    - 500: Internal error
    """,
)
async def make_duplicate_decision(
    doc_id: str,
    request: DuplicateDecisionRequest,
    session: AsyncSession = Depends(get_async_session),
) -> GovernanceResponse:
    """Make an admin decision on a duplicate source.

    Args:
        doc_id: Document identifier
        request: Duplicate decision request
        session: Database session (injected)

    Returns:
        GovernanceResponse with updated status

    Raises:
        HTTPException: On validation errors or state machine violations
    """
    try:
        state_machine = GovernanceStateMachine(session)

        # Determine target status based on decision
        if request.decision == DuplicateDecisionType.IGNORE_DUPLICATE:
            target_status = GovernanceStatus.PENDING_APPROVAL
        elif request.decision == DuplicateDecisionType.ALLOW_SEPARATE_INSTANCE:
            target_status = GovernanceStatus.APPROVED
        else:
            raise ValueError(f"Invalid duplicate decision: {request.decision}")

        # Execute transition
        source = await state_machine.transition(
            doc_id=doc_id,
            to_status=target_status,
            triggered_by=request.admin_user_id,
            expected_version=request.expected_version,
            metadata={
                "action": "duplicate_decision",
                "admin_user_id": request.admin_user_id,
                "decision": request.decision.value,
            },
        )

        # Record duplicate decision in separate table
        duplicate_decision = DuplicateDecision(
            doc_id=doc_id,
            decision=request.decision,
            decided_by=request.admin_user_id,
        )
        session.add(duplicate_decision)

        await session.commit()

        # If ALLOW_SEPARATE_INSTANCE, enqueue ingestion job
        if request.decision == DuplicateDecisionType.ALLOW_SEPARATE_INSTANCE:
            await enqueue_ingestion_job(
                doc_id=source.doc_id,
                source_sha256=source.source_sha256,
                original_filename=source.original_filename,
                current_path=source.current_path,
                system_id=source.system_id,
                game_id=source.game_id,
                owner_user_id=source.owner_user_id,
            )

        logger.info(
            f"Duplicate decision recorded: {doc_id} → {request.decision.value} "
            f"by {request.admin_user_id} (new status: {target_status.value})"
        )

        return GovernanceResponse(
            doc_id=source.doc_id,
            status=source.status.value,
            state_version=source.state_version,
            message=f"Duplicate decision: {request.decision.value}",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "source_not_found",
                "message": str(e),
                "details": {"doc_id": doc_id},
            },
        )

    except IllegalTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "illegal_transition",
                "message": e.message,
                "details": {
                    "doc_id": doc_id,
                    "from_status": e.from_status.value if e.from_status else None,
                    "to_status": e.to_status.value,
                },
            },
        )

    except OptimisticLockError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "concurrent_modification",
                "message": e.message,
                "details": {
                    "doc_id": e.doc_id,
                    "expected_version": e.expected_version,
                    "actual_version": e.actual_version,
                },
            },
        )

    except Exception as e:
        logger.error(f"Error processing duplicate decision for {doc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": f"Unexpected error during duplicate decision: {str(e)}",
                "details": {"doc_id": doc_id},
            },
        )
