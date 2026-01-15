"""Test case T-ING-001: Governance State Machine Enforcement.

Reference:
- TEST_CASES_v1.0.md Section 2 (T-ING-001)
- GOVERNANCE_FLOW_v1.0.md
- REQUIREMENTS_v1.0.md FR-001, FR-002, FR-003

Task ID: PHASE0-INIT-007

T-ING-001 — Detect Ungoverned Source
Related Requirements: FR-001, FR-002, FR-003

Preconditions:
- Clean environment
- No governance record exists for the test file

Steps:
1. Place a PDF into `/transfer_station/sources/`
2. Wait for discovery scan

Expected Results:
- SHA-256 is computed
- Governance record is created
- Status is `PENDING_APPROVAL`

This test validates the governance state machine enforcement at the unit level.
Full integration testing (with actual files in Transfer Station) is deferred to Phase 1.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.governance import (
    ALLOWED_TRANSITIONS,
    FORBIDDEN_TRANSITIONS,
    GovernanceStateMachine,
    IllegalTransitionError,
    OptimisticLockError,
    is_transition_allowed,
)
from nexus_core.models.source import GovernanceEvent, GovernanceStatus, Source


class TestGovernanceTransitions:
    """Test governance state transition rules."""

    def test_allowed_transitions_complete(self):
        """Verify all states have defined transitions."""
        # All states except None should be in the allowed transitions map
        for status in GovernanceStatus:
            assert status in ALLOWED_TRANSITIONS, f"Missing transitions for {status}"

        # None (initial state) should also be defined
        assert None in ALLOWED_TRANSITIONS

    def test_discovered_transitions(self):
        """Test allowed transitions from DISCOVERED state."""
        allowed = ALLOWED_TRANSITIONS[GovernanceStatus.DISCOVERED]

        # Should allow transition to PENDING_APPROVAL or DUPLICATE_DETECTED
        assert GovernanceStatus.PENDING_APPROVAL in allowed
        assert GovernanceStatus.DUPLICATE_DETECTED in allowed

        # Should NOT allow direct transition to INGESTING
        assert GovernanceStatus.INGESTING not in allowed

    def test_pending_approval_transitions(self):
        """Test allowed transitions from PENDING_APPROVAL state."""
        allowed = ALLOWED_TRANSITIONS[GovernanceStatus.PENDING_APPROVAL]

        # Should allow APPROVED or DENIED
        assert GovernanceStatus.APPROVED in allowed
        assert GovernanceStatus.DENIED in allowed

        # Should NOT allow skip to INGESTING (forbidden in spec)
        assert GovernanceStatus.INGESTING not in allowed

    def test_approved_transitions(self):
        """Test allowed transitions from APPROVED state."""
        allowed = ALLOWED_TRANSITIONS[GovernanceStatus.APPROVED]

        # Should allow INGESTING
        assert GovernanceStatus.INGESTING in allowed

        # Should NOT allow skip to INGESTED (forbidden in spec)
        assert GovernanceStatus.INGESTED not in allowed

    def test_ingesting_transitions(self):
        """Test allowed transitions from INGESTING state."""
        allowed = ALLOWED_TRANSITIONS[GovernanceStatus.INGESTING]

        # Should allow INGESTED or ERROR
        assert GovernanceStatus.INGESTED in allowed
        assert GovernanceStatus.ERROR in allowed

    def test_deactivated_is_terminal(self):
        """Test that DEACTIVATED is a terminal state."""
        allowed = ALLOWED_TRANSITIONS[GovernanceStatus.DEACTIVATED]

        # No transitions allowed from DEACTIVATED
        assert len(allowed) == 0

    def test_forbidden_transitions_defined(self):
        """Test that forbidden transitions are explicitly defined."""
        # Key forbidden transitions from GOVERNANCE_FLOW_v1.0.md Section 5
        assert (GovernanceStatus.PENDING_APPROVAL, GovernanceStatus.INGESTING) in FORBIDDEN_TRANSITIONS
        assert (GovernanceStatus.APPROVED, GovernanceStatus.INGESTED) in FORBIDDEN_TRANSITIONS
        assert (GovernanceStatus.ERROR, GovernanceStatus.INGESTED) in FORBIDDEN_TRANSITIONS

        # DEACTIVATED to any active state should be forbidden
        active_states = [
            GovernanceStatus.DISCOVERED,
            GovernanceStatus.PENDING_APPROVAL,
            GovernanceStatus.APPROVED,
            GovernanceStatus.INGESTING,
            GovernanceStatus.INGESTED,
            GovernanceStatus.ERROR,
        ]
        for state in active_states:
            assert (GovernanceStatus.DEACTIVATED, state) in FORBIDDEN_TRANSITIONS

    def test_is_transition_allowed_valid(self):
        """Test is_transition_allowed for valid transitions."""
        # Valid transitions
        assert is_transition_allowed(None, GovernanceStatus.DISCOVERED)
        assert is_transition_allowed(GovernanceStatus.DISCOVERED, GovernanceStatus.PENDING_APPROVAL)
        assert is_transition_allowed(GovernanceStatus.PENDING_APPROVAL, GovernanceStatus.APPROVED)
        assert is_transition_allowed(GovernanceStatus.APPROVED, GovernanceStatus.INGESTING)
        assert is_transition_allowed(GovernanceStatus.INGESTING, GovernanceStatus.INGESTED)

    def test_is_transition_allowed_invalid(self):
        """Test is_transition_allowed for invalid transitions."""
        # Invalid transitions
        assert not is_transition_allowed(GovernanceStatus.PENDING_APPROVAL, GovernanceStatus.INGESTING)
        assert not is_transition_allowed(GovernanceStatus.APPROVED, GovernanceStatus.INGESTED)
        assert not is_transition_allowed(GovernanceStatus.DEACTIVATED, GovernanceStatus.APPROVED)


@pytest.mark.asyncio
class TestGovernanceStateMachine:
    """Test governance state machine implementation."""

    async def test_create_source(self, session: AsyncSession):
        """Test creating a new source with DISCOVERED status (T-ING-001 core)."""
        state_machine = GovernanceStateMachine(session)

        # Create a new source
        source = await state_machine.create_source(
            doc_id="test_file__abc123def456",
            source_sha256="abc123def456" * 4,  # 64 char hash
            original_filename="test_file.pdf",
            current_path="/transfer_station/sources/test_file.pdf",
            owner_user_id="test_user",
            triggered_by="ingestion_worker",
        )

        # Verify source was created
        assert source is not None
        assert source.doc_id == "test_file__abc123def456"
        assert source.status == GovernanceStatus.DISCOVERED
        assert source.state_version == 1

        # Verify governance event was logged
        result = await session.execute(
            select(GovernanceEvent).where(GovernanceEvent.doc_id == source.doc_id)
        )
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].from_status is None
        assert events[0].to_status == "DISCOVERED"

    async def test_valid_transition(self, session: AsyncSession):
        """Test executing a valid state transition."""
        state_machine = GovernanceStateMachine(session)

        # Create source
        source = await state_machine.create_source(
            doc_id="valid_transition__abc123",
            source_sha256="abc123" * 10 + "abcd",
            original_filename="valid_transition.pdf",
            current_path="/transfer_station/sources/valid_transition.pdf",
            owner_user_id="test_user",
            triggered_by="ingestion_worker",
        )

        # Transition to PENDING_APPROVAL
        updated = await state_machine.transition(
            doc_id=source.doc_id,
            to_status=GovernanceStatus.PENDING_APPROVAL,
            triggered_by="ingestion_worker",
        )

        assert updated.status == GovernanceStatus.PENDING_APPROVAL
        assert updated.state_version == 2

    async def test_illegal_transition_rejected(self, session: AsyncSession):
        """Test that illegal transitions are rejected with proper error."""
        state_machine = GovernanceStateMachine(session)

        # Create source in PENDING_APPROVAL state
        source = await state_machine.create_source(
            doc_id="illegal_transition__abc123",
            source_sha256="def456" * 10 + "defg",
            original_filename="illegal_transition.pdf",
            current_path="/transfer_station/sources/illegal_transition.pdf",
            owner_user_id="test_user",
            triggered_by="ingestion_worker",
        )

        await state_machine.transition(
            doc_id=source.doc_id,
            to_status=GovernanceStatus.PENDING_APPROVAL,
            triggered_by="ingestion_worker",
        )

        # Attempt illegal transition: PENDING_APPROVAL -> INGESTING (forbidden)
        with pytest.raises(IllegalTransitionError) as exc_info:
            await state_machine.transition(
                doc_id=source.doc_id,
                to_status=GovernanceStatus.INGESTING,
                triggered_by="malicious_component",
            )

        assert exc_info.value.from_status == GovernanceStatus.PENDING_APPROVAL
        assert exc_info.value.to_status == GovernanceStatus.INGESTING

        # Verify rejection was logged
        result = await session.execute(
            select(GovernanceEvent)
            .where(GovernanceEvent.doc_id == source.doc_id)
            .order_by(GovernanceEvent.triggered_at.desc())
        )
        events = result.scalars().all()
        rejection_event = events[0]
        assert rejection_event.metadata_json is not None
        assert rejection_event.metadata_json.get("rejected") is True

    async def test_optimistic_locking(self, session: AsyncSession):
        """Test that optimistic locking prevents concurrent modifications."""
        state_machine = GovernanceStateMachine(session)

        # Create source
        source = await state_machine.create_source(
            doc_id="optimistic_lock__abc123",
            source_sha256="ghi789" * 10 + "ghij",
            original_filename="optimistic_lock.pdf",
            current_path="/transfer_station/sources/optimistic_lock.pdf",
            owner_user_id="test_user",
            triggered_by="ingestion_worker",
        )

        # Transition with correct version
        await state_machine.transition(
            doc_id=source.doc_id,
            to_status=GovernanceStatus.PENDING_APPROVAL,
            triggered_by="ingestion_worker",
            expected_version=1,
        )

        # Attempt transition with stale version
        with pytest.raises(OptimisticLockError) as exc_info:
            await state_machine.transition(
                doc_id=source.doc_id,
                to_status=GovernanceStatus.APPROVED,
                triggered_by="admin",
                expected_version=1,  # Stale - should be 2 now
            )

        assert exc_info.value.expected_version == 1
        assert exc_info.value.actual_version == 2

    async def test_full_happy_path(self, session: AsyncSession):
        """Test full happy path: DISCOVERED -> ... -> INGESTED."""
        state_machine = GovernanceStateMachine(session)

        # Create source (DISCOVERED)
        source = await state_machine.create_source(
            doc_id="happy_path__abc123",
            source_sha256="jkl012" * 10 + "jklm",
            original_filename="happy_path.pdf",
            current_path="/transfer_station/sources/happy_path.pdf",
            owner_user_id="test_user",
            triggered_by="ingestion_worker",
        )
        assert source.status == GovernanceStatus.DISCOVERED

        # DISCOVERED -> PENDING_APPROVAL
        source = await state_machine.transition(
            doc_id=source.doc_id,
            to_status=GovernanceStatus.PENDING_APPROVAL,
            triggered_by="ingestion_worker",
        )
        assert source.status == GovernanceStatus.PENDING_APPROVAL

        # PENDING_APPROVAL -> APPROVED (admin approval)
        source = await state_machine.transition(
            doc_id=source.doc_id,
            to_status=GovernanceStatus.APPROVED,
            triggered_by="admin_user",
        )
        assert source.status == GovernanceStatus.APPROVED

        # APPROVED -> INGESTING
        source = await state_machine.transition(
            doc_id=source.doc_id,
            to_status=GovernanceStatus.INGESTING,
            triggered_by="ingestion_worker",
        )
        assert source.status == GovernanceStatus.INGESTING

        # INGESTING -> INGESTED (validation pass)
        source = await state_machine.transition(
            doc_id=source.doc_id,
            to_status=GovernanceStatus.INGESTED,
            triggered_by="validator",
        )
        assert source.status == GovernanceStatus.INGESTED

        # Verify all events were logged
        result = await session.execute(
            select(GovernanceEvent).where(GovernanceEvent.doc_id == source.doc_id)
        )
        events = result.scalars().all()
        assert len(events) == 5  # Create + 4 transitions

    async def test_deactivated_is_terminal(self, session: AsyncSession):
        """Test that DEACTIVATED state cannot transition to any other state."""
        state_machine = GovernanceStateMachine(session)

        # Create and fast-forward to INGESTED
        source = await state_machine.create_source(
            doc_id="terminal_test__abc123",
            source_sha256="mno345" * 10 + "mnop",
            original_filename="terminal_test.pdf",
            current_path="/transfer_station/sources/terminal_test.pdf",
            owner_user_id="test_user",
            triggered_by="ingestion_worker",
        )

        # Fast-forward through states
        for to_status in [
            GovernanceStatus.PENDING_APPROVAL,
            GovernanceStatus.APPROVED,
            GovernanceStatus.INGESTING,
            GovernanceStatus.INGESTED,
            GovernanceStatus.DEACTIVATED,
        ]:
            source = await state_machine.transition(
                doc_id=source.doc_id,
                to_status=to_status,
                triggered_by="test",
            )

        assert source.status == GovernanceStatus.DEACTIVATED

        # Verify DEACTIVATED is terminal
        assert GovernanceStateMachine.is_terminal_state(GovernanceStatus.DEACTIVATED)

        # Attempt to transition out (should fail)
        with pytest.raises(IllegalTransitionError):
            await state_machine.transition(
                doc_id=source.doc_id,
                to_status=GovernanceStatus.APPROVED,
                triggered_by="admin",
            )


class TestGovernanceStateMachineHelpers:
    """Test helper methods on GovernanceStateMachine."""

    def test_get_allowed_transitions(self):
        """Test getting allowed transitions for a state."""
        allowed = GovernanceStateMachine.get_allowed_transitions(GovernanceStatus.PENDING_APPROVAL)

        assert GovernanceStatus.APPROVED in allowed
        assert GovernanceStatus.DENIED in allowed
        assert GovernanceStatus.INGESTING not in allowed

    def test_is_terminal_state(self):
        """Test terminal state detection."""
        assert GovernanceStateMachine.is_terminal_state(GovernanceStatus.DEACTIVATED)
        assert not GovernanceStateMachine.is_terminal_state(GovernanceStatus.INGESTED)
        assert not GovernanceStateMachine.is_terminal_state(GovernanceStatus.APPROVED)
