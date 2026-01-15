"""Governance state transitions for Nexus Core.

Reference:
- GOVERNANCE_FLOW_v1.0.md Section 4
- PHASE_0_INITIALIZATION_PROMPT_v1.0.md

Task ID: PHASE0-INIT-007

Defines the authoritative allowed and forbidden state transitions.
"""

from nexus_core.models.source import GovernanceStatus

# =============================================================================
# Allowed Transitions (GOVERNANCE_FLOW_v1.0.md Section 4)
# =============================================================================

ALLOWED_TRANSITIONS: dict[GovernanceStatus | None, list[GovernanceStatus]] = {
    # Initial state - new sources start as DISCOVERED
    None: [GovernanceStatus.DISCOVERED],
    # Discovery and Approval (Section 4.1)
    GovernanceStatus.DISCOVERED: [
        GovernanceStatus.PENDING_APPROVAL,
        GovernanceStatus.DUPLICATE_DETECTED,
    ],
    GovernanceStatus.PENDING_APPROVAL: [
        GovernanceStatus.APPROVED,
        GovernanceStatus.DENIED,
    ],
    GovernanceStatus.DENIED: [
        GovernanceStatus.PENDING_APPROVAL,  # Admin can reopen
        GovernanceStatus.DEACTIVATED,  # Optional cleanup
    ],
    GovernanceStatus.DUPLICATE_DETECTED: [
        GovernanceStatus.PENDING_APPROVAL,  # IGNORE_DUPLICATE decision
        GovernanceStatus.APPROVED,  # ALLOW_SEPARATE_INSTANCE decision
    ],
    # Ingestion Execution (Section 4.2)
    GovernanceStatus.APPROVED: [
        GovernanceStatus.INGESTING,
    ],
    GovernanceStatus.INGESTING: [
        GovernanceStatus.INGESTED,  # Validation PASS only
        GovernanceStatus.ERROR,  # Pipeline failure
    ],
    # Admin-Gated Retries (Section 4.3)
    GovernanceStatus.ERROR: [
        GovernanceStatus.PENDING_APPROVAL,  # Admin retry
        GovernanceStatus.DEACTIVATED,  # Manual decision
    ],
    # Deactivation (Section 4.4)
    GovernanceStatus.INGESTED: [
        GovernanceStatus.DEACTIVATED,  # Source removed from disk
    ],
    # Terminal state - no transitions allowed
    GovernanceStatus.DEACTIVATED: [],
}


# =============================================================================
# Forbidden Transitions (GOVERNANCE_FLOW_v1.0.md Section 5)
# Explicitly listed for validation and documentation
# =============================================================================

FORBIDDEN_TRANSITIONS: list[tuple[GovernanceStatus, GovernanceStatus]] = [
    # Cannot skip approval
    (GovernanceStatus.PENDING_APPROVAL, GovernanceStatus.INGESTING),
    # Cannot skip validation
    (GovernanceStatus.APPROVED, GovernanceStatus.INGESTED),
    # Cannot go from error to ingested without retry
    (GovernanceStatus.ERROR, GovernanceStatus.INGESTED),
    # Deactivated is terminal - cannot reactivate
    (GovernanceStatus.DEACTIVATED, GovernanceStatus.DISCOVERED),
    (GovernanceStatus.DEACTIVATED, GovernanceStatus.PENDING_APPROVAL),
    (GovernanceStatus.DEACTIVATED, GovernanceStatus.APPROVED),
    (GovernanceStatus.DEACTIVATED, GovernanceStatus.INGESTING),
    (GovernanceStatus.DEACTIVATED, GovernanceStatus.INGESTED),
    (GovernanceStatus.DEACTIVATED, GovernanceStatus.ERROR),
]


def is_transition_allowed(
    from_status: GovernanceStatus | None,
    to_status: GovernanceStatus,
) -> bool:
    """Check if a state transition is allowed.

    Args:
        from_status: Current status (None for new sources).
        to_status: Target status.

    Returns:
        True if the transition is allowed, False otherwise.
    """
    # Check forbidden list first (explicit denials)
    if from_status is not None:
        if (from_status, to_status) in FORBIDDEN_TRANSITIONS:
            return False

    # Check allowed transitions
    allowed = ALLOWED_TRANSITIONS.get(from_status, [])
    return to_status in allowed


def get_allowed_transitions(status: GovernanceStatus | None) -> list[GovernanceStatus]:
    """Get list of allowed transitions from a given status.

    Args:
        status: Current status (None for new sources).

    Returns:
        List of allowed target statuses.
    """
    return ALLOWED_TRANSITIONS.get(status, [])
