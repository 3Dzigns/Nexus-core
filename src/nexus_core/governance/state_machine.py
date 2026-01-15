"""Governance state machine implementation for Nexus Core.

Reference:
- GOVERNANCE_FLOW_v1.0.md
- PHASE_0_INITIALIZATION_PROMPT_v1.0.md

Task ID: PHASE0-INIT-007

Implements:
- State transition validation
- Optimistic locking (state_version field)
- Governance event logging
- Illegal transition rejection
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.governance.transitions import (
    FORBIDDEN_TRANSITIONS,
    get_allowed_transitions,
    is_transition_allowed,
)
from nexus_core.models.source import (
    EventType,
    GovernanceEvent,
    GovernanceStatus,
    Source,
)

logger = logging.getLogger(__name__)


class GovernanceError(Exception):
    """Base exception for governance errors."""

    pass


class IllegalTransitionError(GovernanceError):
    """Raised when an illegal state transition is attempted."""

    def __init__(
        self,
        from_status: GovernanceStatus | None,
        to_status: GovernanceStatus,
        message: Optional[str] = None,
    ):
        self.from_status = from_status
        self.to_status = to_status
        self.message = message or f"Illegal transition: {from_status} -> {to_status}"
        super().__init__(self.message)


class OptimisticLockError(GovernanceError):
    """Raised when optimistic locking detects a concurrent modification."""

    def __init__(self, doc_id: str, expected_version: int, actual_version: int):
        self.doc_id = doc_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        self.message = (
            f"Concurrent modification detected for {doc_id}: "
            f"expected version {expected_version}, found {actual_version}"
        )
        super().__init__(self.message)


class GovernanceStateMachine:
    """Governance state machine with validation and event logging.

    Reference: GOVERNANCE_FLOW_v1.0.md Section 7

    Enforcement rules:
    - All transitions are validated at runtime
    - State changes are logged with full context
    - Illegal transitions fail fast
    - Optimistic locking prevents concurrent modifications
    """

    def __init__(self, session: AsyncSession):
        """Initialize state machine with database session.

        Args:
            session: AsyncSession for database operations.
        """
        self.session = session

    async def transition(
        self,
        doc_id: str,
        to_status: GovernanceStatus,
        triggered_by: str,
        expected_version: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> Source:
        """Execute a state transition with validation and logging.

        Args:
            doc_id: Document identifier.
            to_status: Target status.
            triggered_by: Identifier of the triggering component/user.
            expected_version: Expected state_version for optimistic locking.
            metadata: Optional metadata to include in the governance event.

        Returns:
            Updated Source object.

        Raises:
            IllegalTransitionError: If the transition is not allowed.
            OptimisticLockError: If concurrent modification is detected.
            ValueError: If the source doesn't exist.
        """
        # Fetch current source state
        result = await self.session.execute(
            select(Source).where(Source.doc_id == doc_id).with_for_update()
        )
        source = result.scalar_one_or_none()

        if source is None:
            raise ValueError(f"Source not found: {doc_id}")

        from_status = source.status
        current_version = source.state_version

        # Check optimistic lock if version provided
        if expected_version is not None and current_version != expected_version:
            logger.warning(
                f"Optimistic lock failure for {doc_id}: "
                f"expected {expected_version}, found {current_version}"
            )
            raise OptimisticLockError(doc_id, expected_version, current_version)

        # Validate transition
        if not is_transition_allowed(from_status, to_status):
            logger.warning(
                f"Illegal transition attempted for {doc_id}: {from_status} -> {to_status}"
            )
            # Log the attempt as a governance event (rejected)
            await self._log_rejected_transition(
                doc_id, from_status, to_status, triggered_by, metadata
            )
            raise IllegalTransitionError(from_status, to_status)

        # Execute transition
        new_version = current_version + 1
        await self.session.execute(
            update(Source)
            .where(Source.doc_id == doc_id)
            .where(Source.state_version == current_version)  # Optimistic lock
            .values(
                status=to_status,
                state_version=new_version,
                updated_at=datetime.now(timezone.utc),
            )
        )

        # Log governance event
        await self._log_transition(
            doc_id, from_status, to_status, triggered_by, metadata
        )

        # Refresh and return source
        await self.session.refresh(source)
        logger.info(
            f"Transition successful: {doc_id} {from_status} -> {to_status} "
            f"(version {current_version} -> {new_version})"
        )

        return source

    async def create_source(
        self,
        doc_id: str,
        source_sha256: str,
        original_filename: str,
        current_path: str,
        owner_user_id: str,
        triggered_by: str,
        system_id: Optional[str] = None,
        game_id: Optional[str] = None,
    ) -> Source:
        """Create a new source with DISCOVERED status.

        Args:
            doc_id: Document identifier.
            source_sha256: SHA-256 hash of source file.
            original_filename: Original filename.
            current_path: Current file path.
            owner_user_id: Owner user identifier.
            triggered_by: Identifier of the triggering component.
            system_id: Optional system identifier.
            game_id: Optional game identifier.

        Returns:
            Created Source object.

        Raises:
            IllegalTransitionError: If creation is not allowed.
        """
        # Validate that None -> DISCOVERED is allowed
        if not is_transition_allowed(None, GovernanceStatus.DISCOVERED):
            raise IllegalTransitionError(None, GovernanceStatus.DISCOVERED)

        # Create source
        source = Source(
            doc_id=doc_id,
            source_sha256=source_sha256,
            original_filename=original_filename,
            current_path=current_path,
            status=GovernanceStatus.DISCOVERED,
            state_version=1,
            owner_user_id=owner_user_id,
            system_id=system_id,
            game_id=game_id,
        )

        self.session.add(source)

        # Log governance event
        await self._log_transition(
            doc_id, None, GovernanceStatus.DISCOVERED, triggered_by, None
        )

        await self.session.flush()
        logger.info(f"Source created: {doc_id} with status DISCOVERED")

        return source

    async def _log_transition(
        self,
        doc_id: str,
        from_status: GovernanceStatus | None,
        to_status: GovernanceStatus,
        triggered_by: str,
        metadata: Optional[dict],
    ) -> GovernanceEvent:
        """Log a successful state transition.

        Args:
            doc_id: Document identifier.
            from_status: Previous status.
            to_status: New status.
            triggered_by: Triggering component/user.
            metadata: Optional metadata.

        Returns:
            Created GovernanceEvent.
        """
        event = GovernanceEvent(
            event_id=uuid4(),
            doc_id=doc_id,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value,
            event_type=EventType.STATUS_CHANGE,
            triggered_by=triggered_by,
            triggered_at=datetime.now(timezone.utc),
            metadata_json=metadata,
        )

        self.session.add(event)
        await self.session.flush()

        return event

    async def _log_rejected_transition(
        self,
        doc_id: str,
        from_status: GovernanceStatus | None,
        to_status: GovernanceStatus,
        triggered_by: str,
        metadata: Optional[dict],
    ) -> GovernanceEvent:
        """Log a rejected state transition attempt.

        Reference: GOVERNANCE_FLOW_v1.0.md Section 7
        - Any rejected transition must be logged as a governance event

        Args:
            doc_id: Document identifier.
            from_status: Current status.
            to_status: Attempted target status.
            triggered_by: Triggering component/user.
            metadata: Optional metadata.

        Returns:
            Created GovernanceEvent with rejection info.
        """
        rejection_metadata = {
            "rejected": True,
            "reason": f"Illegal transition: {from_status} -> {to_status}",
            **(metadata or {}),
        }

        event = GovernanceEvent(
            event_id=uuid4(),
            doc_id=doc_id,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value,
            event_type=EventType.STATUS_CHANGE,
            triggered_by=triggered_by,
            triggered_at=datetime.now(timezone.utc),
            metadata_json=rejection_metadata,
        )

        self.session.add(event)
        await self.session.flush()

        logger.warning(f"Rejected transition logged: {doc_id} {from_status} -> {to_status}")

        return event

    @staticmethod
    def get_allowed_transitions(status: GovernanceStatus | None) -> list[GovernanceStatus]:
        """Get list of allowed transitions from a given status.

        Args:
            status: Current status.

        Returns:
            List of allowed target statuses.
        """
        return get_allowed_transitions(status)

    @staticmethod
    def is_terminal_state(status: GovernanceStatus) -> bool:
        """Check if a status is a terminal state (no further transitions).

        Args:
            status: Status to check.

        Returns:
            True if terminal state.
        """
        return len(get_allowed_transitions(status)) == 0
