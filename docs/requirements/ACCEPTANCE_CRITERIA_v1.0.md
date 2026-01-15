# ACCEPTANCE_CRITERIA_v1.0

## 0. Purpose
This document defines the **formal acceptance criteria** for Nexus Core MVP1.

Acceptance criteria determine **when a feature, phase, or the entire MVP1** is considered complete. These criteria are objective, verifiable, and derived directly from approved requirements and test cases.

No subjective judgment or "mostly works" determination is allowed.

---

## 1. Acceptance Philosophy

### 1.1 Objective Completion
A component is accepted only when:
- All required artifacts exist
- All mapped test cases pass
- Validation reports confirm correctness

### 1.2 No Partial Acceptance
- Partial ingestion success is not acceptable
- Skipped steps invalidate acceptance
- Failed validation blocks acceptance

---

## 2. Artifact Acceptance

The following documents **must exist, be versioned, and be approved**:

- ARCHITECTURE_v1.0.md
- INGESTION_ARCHITECTURE_v1.0.md
- REQUIREMENTS_v1.0.md
- TEST_PLAN_v1.0.md
- TEST_CASES_v1.0.md
- ACCEPTANCE_CRITERIA_v1.0.md

All documents must be consistent with each other.

---

## 3. Phase-Level Acceptance Criteria

### Phase 0 — Project & Governance Foundations

**Accepted when:**
- Repo structure exists
- Docker Compose starts successfully
- Governance models validate allowed state transitions

---

### Phase 1 — Source Discovery & Approval

**Accepted when:**
- Ungoverned sources are detected
- Governance records created correctly
- Admin approval/denial functions
- Duplicate detection requires admin decision

Mapped tests:
- T-ING-001
- T-ING-002
- T-ING-003

---

### Phase 2 — Extraction & Artifact Generation

**Accepted when:**
- Approved sources trigger extraction
- Docling and Unstructured both run
- Raw manifests exist for both tools
- Provenance metadata recorded

Mapped tests:
- T-ING-004
- T-ING-005
- T-ING-006

---

### Phase 3 — Normalization, Enrichment, Chunking

**Accepted when:**
- Canonical normalized manifests exist
- Content-aware metadata enrichment completes
- Dual chunk sets created
- Chunk metadata is complete

Mapped tests:
- T-ING-007
- T-ING-008
- T-ING-009

---

### Phase 4 — Storage, Indexing & Validation

**Accepted when:**
- Chunks stored in Postgres
- Embeddings generated
- Full-text search indexes exist
- Validation PASS reports generated
- Sources marked INGESTED only after validation

Mapped tests:
- T-ING-010
- T-ING-011
- T-ING-012
- T-ING-013

---

### Phase 5 — Deactivation & Removal

**Accepted when:**
- Source removal deactivates data
- Admin removal request created
- Deactivated data excluded from retrieval

Mapped tests:
- T-ING-014

---

### Phase 6 — Query & Action Safety

**Accepted when:**
- Game context restricts sources
- No-source queries return friendly response
- Active character is used for actions
- Partial action corrections are explained

Mapped tests:
- T-QRY-001
- T-QRY-002
- T-ACT-001
- T-ACT-002

---

### Phase 7 — Feedback, Limits & UI Enforcement

**Accepted when:**
- Feedback is collected
- Ranking adjusts correctly
- Admin flags generated for persistent negatives
- Tier violations hard-lock the UI

Mapped tests:
- T-FBK-001
- T-LIM-001

---

## 4. System-Level Acceptance Criteria (MVP1)

Nexus Core MVP1 is accepted when **all phases 0–7** meet acceptance criteria and:

- All test cases in TEST_CASES_v1.0.md pass
- No failed validation reports remain unresolved
- Cleanup procedures restore a clean environment
- No AI query can bypass governance, scope, or role rules

---

## 5. Acceptance Evidence

Acceptance must be supported by:
- Test execution logs
- Validation reports
- Database inspection (where applicable)

Verbal confirmation is not sufficient.

---

## 6. Rejection Conditions

MVP1 must be rejected if:
- Any ingestion test fails
- Any validation report fails
- Any source is marked INGESTED without validation
- Any query accesses unauthorized sources

---

## 7. Change Control

This document is versioned.

- Any change requires a version bump
- Changes must identify impacted phases and tests

---

## 8. Final Acceptance Statement

MVP1 is considered complete only when all acceptance criteria in this document are met.

This document defines the final, authoritative acceptance contract for Nexus Core MVP1.

