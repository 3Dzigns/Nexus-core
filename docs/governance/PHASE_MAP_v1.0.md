# PHASE_MAP_v1.0.md
**Version:** v1.0  
**Applies To:** Nexus Core MVP1  
**Planning Task:** ING-PLAN-001 — Phase Mapping

---

## 1. Purpose

This document provides a **single source of truth** mapping Nexus Core MVP1 **phases** to:

- Governing documents
- Functional requirements (FRs)
- Test cases

Its purpose is to:
- Prevent phase drift
- Ensure implementation follows the intended order
- Enable fast traceability during implementation, testing, and validation

This document is **descriptive only**. It does **not** add new behavior or requirements.

---

## 2. Phase Definitions (Authoritative)

Phases are defined **exactly** as specified in `ACCEPTANCE_CRITERIA_v1.0.md`.

No phases may be merged, reordered, or skipped.

---

## 3. Phase-to-Artifact Mapping

### Phase 0 — Project & Governance Foundations

**Purpose:** Establish system foundations and governance enforcement.

**Governing Documents:**
- ARCHITECTURE_v1.0.md
- INGESTION_ARCHITECTURE_v1.0.md
- GOVERNANCE_FLOW_v1.0.md
- INGESTION_DEPENDENCIES_v1.0.md
- OPENAPI_v1.0.md
- API_VERSIONING_v1.0.md
- DATABASE_SCHEMA_v1.0.md
- DATABASE_CONSTRAINTS_v1.0.md
- TRANSACTION_MODEL_v1.0.md
- JWT_SPEC_v1.0.md
- TOOL_VERSIONS_v1.0.md
- DEPLOYMENT_v1.0.md
- MONITORING_v1.0.md
- LOGGING_v1.0.md
- RETENTION_POLICY_v1.0.md

**Primary Requirements:**
- FR-001
- FR-002
- FR-003

**Primary Test Cases:**
- T-ING-001

---

### Phase 1 — Source Discovery & Approval

**Purpose:** Detect sources and enforce explicit admin approval.

**Governing Documents:**
- INGESTION_ARCHITECTURE_v1.0.md
- GOVERNANCE_FLOW_v1.0.md
- REQUIREMENTS_v1.0.md
- INGESTION_DEPENDENCIES_v1.0.md

**Primary Requirements:**
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007

**Primary Test Cases:**
- T-ING-001
- T-ING-002
- T-ING-003

---

### Phase 2 — Extraction & Artifact Generation

**Purpose:** Produce dual extractor outputs and preserve provenance.

**Governing Documents:**
- INGESTION_ARCHITECTURE_v1.0.md
- ARTIFACT_CONTRACT_v1.0.md
- REQUIREMENTS_v1.0.md

**Primary Requirements:**
- FR-011
- FR-012
- FR-013
- FR-014

**Primary Test Cases:**
- T-ING-004
- T-ING-005
- T-ING-006

---

### Phase 3 — Normalization, Enrichment & Chunking

**Purpose:** Produce deterministic, content-aware chunks.

**Governing Documents:**
- INGESTION_ARCHITECTURE_v1.0.md
- ARTIFACT_CONTRACT_v1.0.md
- REQUIREMENTS_v1.0.md

**Primary Requirements:**
- FR-015
- FR-016
- FR-017
- FR-018
- FR-019
- FR-020

**Primary Test Cases:**
- T-ING-007
- T-ING-008
- T-ING-009

---

### Phase 4 — Storage, Indexing & Validation

**Purpose:** Persist chunks, index content, and certify correctness.

**Governing Documents:**
- VALIDATION_PLAN_v1.0.md
- ARTIFACT_CONTRACT_v1.0.md
- INGESTION_ARCHITECTURE_v1.0.md

**Primary Requirements:**
- FR-021
- FR-022
- FR-023
- FR-024
- FR-025
- FR-026

**Primary Test Cases:**
- T-ING-010
- T-ING-011
- T-ING-012
- T-ING-013

---

### Phase 5 — Deactivation & Removal

**Purpose:** Safely deactivate sources and derived data.

**Governing Documents:**
- GOVERNANCE_FLOW_v1.0.md
- CLEANUP_STRATEGY_v1.0.md
- REQUIREMENTS_v1.0.md

**Primary Requirements:**
- FR-008
- FR-009
- FR-010

**Primary Test Cases:**
- T-ING-014

---

### Phase 6 — Query & Action Safety

**Purpose:** Enforce scope, role, and action correctness.

**Governing Documents:**
- ARCHITECTURE_v1.0.md
- REQUIREMENTS_v1.0.md
- QUERY_POLICY_v1.0.md
- ACCESS_MATRIX_v1.0.md
- FAULT_RECOVERY_v1.0.md

**Primary Requirements:**
- FR-027
- FR-028
- FR-029
- FR-030
- FR-031
- FR-032
- FR-033
- FR-034
- FR-035
- FR-036

**Primary Test Cases:**
- T-QRY-001
- T-QRY-002
- T-ACT-001
- T-ACT-002

---

### Phase 7 — Feedback, Limits & UI Enforcement

**Purpose:** Apply feedback loops and enforce tier limits.

**Governing Documents:**
- ARCHITECTURE_v1.0.md
- REQUIREMENTS_v1.0.md

**Primary Requirements:**
- FR-037
- FR-038
- FR-039
- FR-040
- FR-041

**Primary Test Cases:**
- T-FBK-001
- T-LIM-001

---

## 4. Usage Rules

- Implementation MUST proceed in phase order
- Tests MUST be executed according to phase boundaries
- Validation and acceptance are phase-gated

Skipping or partially implementing a phase is forbidden.

---

## 5. Change Control

This document is versioned.

- Any change requires a version bump
- Phase changes MUST update acceptance criteria and tests

---

## 6. Acceptance Statement

The phase map for Nexus Core MVP1 is accepted when:

- All phases map cleanly to requirements and tests
- No orphaned requirements or tests exist
- Phase order is strictly enforced

This document defines the **authoritative phase map** for MVP1.

