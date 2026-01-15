# GOVERNANCE_FLOW_v1.0.md

**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** INGESTION_ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines the **authoritative governance state machine** for Nexus Core MVP1 ingestion.

It is **subordinate** to the ingestion architecture. Any conflict must be resolved in favor of:
- `docs/architecture/INGESTION_ARCHITECTURE_v1.0.md`

---

## 2. Governance Principles (Non-Negotiable)

- No source may be processed without a governance record
- All state transitions are explicit and auditable
- No component may skip states
- Validation is the only path to `INGESTED`
- Deactivation is preferred over deletion
- Admin intent is required for all approval, retry, and removal actions

---

## 3. Governance States (Authoritative List)

The following governance states are **the only valid states in MVP1**:

| State | Description |
|------|-------------|
| `DISCOVERED` | File detected on disk, governance record created |
| `PENDING_APPROVAL` | Awaiting explicit admin decision |
| `DUPLICATE_DETECTED` | Duplicate SHA-256 detected; admin decision required |
| `DENIED` | Explicitly rejected by admin |
| `APPROVED` | Approved for ingestion, not yet processed |
| `INGESTING` | Pipeline executing (extraction through indexing) |
| `INGESTED` | Fully validated and certified |
| `ERROR` | Failure occurred during ingestion or validation |
| `DEACTIVATED` | Source removed from disk; data excluded from retrieval |

No additional states are permitted in MVP1.

---

## 4. Allowed State Transitions

Only the transitions listed below are permitted.

### 4.1 Discovery and Approval

| From | To | Triggered By | Notes |
|------|----|-------------|------|
| *(none)* | `DISCOVERED` | Ingestion Worker | SHA-256 computed, record created |
| `DISCOVERED` | `PENDING_APPROVAL` | Ingestion Worker | Automatic after record creation |
| `DISCOVERED` | `DUPLICATE_DETECTED` | Ingestion Worker | SHA-256 matches existing source |
| `PENDING_APPROVAL` | `APPROVED` | **Admin** | Explicit approval required |
| `PENDING_APPROVAL` | `DENIED` | **Admin** | Explicit rejection required |
| `DENIED` | `PENDING_APPROVAL` | **Admin** | Reopen denied source |
| `DUPLICATE_DETECTED` | `PENDING_APPROVAL` | **Admin** | IGNORE_DUPLICATE decision |
| `DUPLICATE_DETECTED` | `APPROVED` | **Admin** | ALLOW_SEPARATE_INSTANCE decision |

Duplicate detection is recorded as a governance **state**.
Admins must choose to ignore or allow a separate instance.

---

### 4.2 Ingestion Execution

| From | To | Triggered By | Notes |
|------|----|-------------|------|
| `APPROVED` | `INGESTING` | Ingestion Worker | Job enqueued |
| `INGESTING` | `INGESTED` | Validation Agent | Validation PASS |
| `INGESTING` | `ERROR` | Ingestion Worker | Any pipeline failure |

Validation is the **only allowed path** to `INGESTED`.

---

### 4.3 Admin-Gated Retries

| From | To | Triggered By | Notes |
|------|----|-------------|------|
| `ERROR` | `PENDING_APPROVAL` | **Admin** | Retry after review |

---

### 4.4 Deactivation and Removal

| From | To | Triggered By | Notes |
|------|----|-------------|------|
| `INGESTED` | `DEACTIVATED` | Ingestion Worker | Source removed from disk |
| `ERROR` | `DEACTIVATED` | **Admin** | Manual decision |
| `DENIED` | `DEACTIVATED` | **Admin** | Optional cleanup |

Deactivation MUST:
- Soft-disable derived data
- Exclude data from retrieval
- Preserve records for audit

Deactivation detection:
- Component: ingestion worker
- Mechanism: polling `/transfer_station/sources/`
- Poll interval: 60 seconds (configurable)
- Latency tolerance: 120 seconds
- On removal: write a `REMOVAL_REQUEST` governance event

---

## 5. Forbidden Transitions (Explicitly Disallowed)

The following transitions MUST NEVER occur:

- `PENDING_APPROVAL` -> `INGESTING`
- `APPROVED` -> `INGESTED`
- `ERROR` -> `INGESTED`
- `DEACTIVATED` -> any active state
- Any state -> hard deletion

If such a transition is attempted, the system MUST:
- Block the operation
- Log the attempt
- Surface it for admin review

---

## 6. Component Authority Matrix

| Component | Allowed Actions |
|-----------|-----------------|
| Ingestion Worker | Discovery, `APPROVED` -> `INGESTING`, deactivation detection |
| Validation Agent | `INGESTING` -> `INGESTED` or `ERROR` |
| Admin UI / API | Approval, denial, retry, deactivation |
| Query Orchestrator | Read-only governance access |

No component may exceed its authority.

---

## 7. Enforcement Rules

- Governance checks MUST be centralized
- All transitions MUST be validated at runtime
- State changes MUST be logged with:
  - source identifier
  - prior state
  - new state
  - triggering component
  - timestamp
- Illegal transitions MUST fail fast
- State transitions MUST use optimistic locking:
  - Read `state_version`
  - Apply transition only if version matches
  - Increment `state_version` on success
  - On version conflict, return a 409 conflict

Illegal state prevention:
- A transition is only allowed if it appears in the allowed transition table
- Duplicate or out-of-order transitions must be rejected
- Any rejected transition must be logged as a governance event

---

## 8. Audit and Observability Requirements

For every governance state change:
- An immutable log entry MUST exist
- The current state MUST be queryable via API
- Historical states MUST be inspectable

Silent or implicit transitions are forbidden.

Governance event types:
- `STATUS_CHANGE` for standard transitions
- `REMOVAL_REQUEST` when a source file is removed from disk

---

## 9. Change Control

This document is versioned.

- Any modification requires a version bump
- Changes MUST identify impacted tests and requirements
- Governance changes require full ingestion compatibility review

---

## 10. Acceptance Statement

The governance model for Nexus Core MVP1 is considered complete when:
- All states and transitions are enforced at runtime
- No illegal transition is possible
- Validation is the sole path to certification
- Deactivated data is fully excluded from retrieval

This document defines the **authoritative governance flow contract** for MVP1.

