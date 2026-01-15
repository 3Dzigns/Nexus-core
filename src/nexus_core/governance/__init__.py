"""Governance state machine for Nexus Core."""

from nexus_core.governance.state_machine import (
    GovernanceError,
    GovernanceStateMachine,
    IllegalTransitionError,
    OptimisticLockError,
)
from nexus_core.governance.transitions import (
    ALLOWED_TRANSITIONS,
    FORBIDDEN_TRANSITIONS,
    is_transition_allowed,
)

__all__ = [
    "GovernanceStateMachine",
    "GovernanceError",
    "IllegalTransitionError",
    "OptimisticLockError",
    "ALLOWED_TRANSITIONS",
    "FORBIDDEN_TRANSITIONS",
    "is_transition_allowed",
]
