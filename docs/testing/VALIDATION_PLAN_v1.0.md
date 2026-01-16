# VALIDATION_PLAN_v1.0.md
**Version:** v1.0  
**Applies To:** Nexus Core MVP1  
**Planning Task:** ING-PLAN-005 — Validation & Certification Plan

---

## 1. Purpose

This document defines the **authoritative validation and certification plan** for Nexus Core MVP1 ingestion.

Its purpose is to:
- Define what it means for ingestion to be *correct*
- Specify mandatory validation checks
- Establish pass/fail criteria
- Lock certification rules before implementation

Validation is a **hard gate**. No source may be marked `INGESTED` without passing validation as defined here.

---

## 2. Validation Principles (Non-Negotiable)

- Validation is deterministic and repeatable
- Validation is non-destructive
- Validation is evidence-based (artifacts + storage)
- Partial success is forbidden
- Validation never fixes ingestion errors
- Failure always blocks certification

Validator implementation:
- Runtime validator and test validator MUST share the same codebase
- Validator version MUST be recorded in reports
- Validator version MUST match the deployed validator binary

---

## 3. Validation Preconditions

Validation MAY begin only when **all** of the following are true:

- Source governance state is `INGESTING`
- No ingestion or extraction jobs are running for the source
- Artifact generation stages have completed
- Required artifact directories exist on disk

If any precondition is not met, validation MUST abort and log the reason.

---

## 4. Validation Scope

Validation applies to **one source at a time** and covers:

- Governance integrity
- Artifact completeness
- Provenance and traceability
- Chunk correctness
- Storage and indexing verification
- Deactivation enforcement

Validation does **not** evaluate:
- Content quality
- Semantic correctness
- AI answer quality

---

## 5. Required Validation Checks

All checks listed below are **mandatory**. Failure of any single check results in validation failure.

---

### 5.1 Governance Integrity Checks

Validation MUST confirm:

- Governance record exists for the source
- Current state is `INGESTING`
- All prior state transitions followed `GOVERNANCE_FLOW_v1.0.md`
- No illegal or skipped transitions occurred

**Failure Condition:**
- Missing record or invalid transition history

---

### 5.2 Artifact Presence & Structure Checks

Validation MUST confirm the existence of:

- Original source artifact (`original_source.json`)
- Docling raw manifest
- Unstructured raw manifest
- Normalized manifests (dual)
- Enriched manifests (dual)
- Chunk directories (dual)

Artifacts MUST:
- Reside in correct directories
- Match the structure defined in `ARTIFACT_CONTRACT_v1.0.md`

**Failure Condition:**
- Any required artifact is missing or misplaced

---

### 5.3 Provenance & Metadata Checks

For each manifest and chunk set, validation MUST confirm:

- doc_id present and correct
- source_sha256 present and correct
- tool name and version recorded
- run identifiers present
- timestamps present

**Failure Condition:**
- Missing or inconsistent provenance metadata

---

### 5.4 Dual-Extractor Completeness Checks

Validation MUST confirm:

- Docling artifacts exist
- Unstructured artifacts exist
- Neither extractor output is treated as canonical

**Failure Condition:**
- Missing extractor output or implicit merge detected

---

### 5.5 Chunk Integrity Checks

Validation MUST confirm:

- Chunks exist for both extractors
- Each chunk references:
  - doc_id
  - tool_origin
  - section_title
  - content_type
  - system_tag
- Chunk identifiers are unique per source
- Chunk IDs follow the required format
- Chunk text length is within required bounds

**Failure Condition:**
- Missing required chunk metadata
- Duplicate chunk IDs or invalid chunk ID format
- Chunk text exceeds the maximum allowed size

**Chunk Size Rule (MVP1):**
- Maximum chunk text length: 8,000 characters
- If any chunk exceeds the limit, validation FAILS

---

### 5.6 Storage & Index Verification

Validation MUST confirm:

- DB rows exist for all chunks
- Each chunk has an embedding vector
- Full-text search index includes chunk text

Verification MAY use:
- Database queries
- Index inspection

**Failure Condition:**
- Missing rows, embeddings, or indexes

### 5.7 Tool Version Compatibility

Validation MUST confirm:
- Tool versions match TOOL_VERSIONS_v1.0.md minimums

**Failure Condition:**
- Tool version below minimum or missing

---

### 5.8 Deactivation & Exclusion Checks

If the source is deactivated during validation, validation MUST confirm:

- Derived chunks are excluded from retrieval
- No active queries can access the source

**Failure Condition:**
- Deactivated data remains retrievable

### 5.9 Orphaned Artifact Detection

Validation MUST confirm:
- No artifacts exist on disk without a corresponding DB record

**Failure Condition:**
- Orphaned artifacts detected

---

## 6. Validation Outcomes

### 6.1 PASS

Validation passes only when **all checks succeed**.

Actions on PASS:
- Generate validation report (JSON + Markdown)
- Update governance state to `INGESTED`
- Log certification event

---

### 6.2 FAIL

Validation fails if **any check fails**.

Actions on FAIL:
- Generate failure report (JSON + Markdown)
- Update governance state to `ERROR`
- Include explicit failure reasons

Automatic retries are forbidden.

---

## 7. Validation Reports

Each validation run MUST produce:

- One machine-readable JSON report
- One human-readable Markdown report

**Report Location:**
```
/transfer_station/artifacts/reports/<doc_id>/
```

**Required Report Fields:**
- doc_id
- validation_timestamp
- pass_fail status
- validator_version
- list of checks performed
- detailed failure reasons (if any)

Reports are immutable once written.

---

## 8. Mapping to Requirements & Tests

Validation checks map directly to:

- **FR-023 – FR-026** (Validation & Certification)
- **T-ING-012** (Validation pass)
- **T-ING-013** (Validation failure on missing artifact)

No validation logic may exist outside this mapping.

---

## 9. Enforcement Rules

- Validation logic MUST be centralized
- Validation MUST be runnable independently
- Validation MUST NOT mutate ingestion artifacts
- Validation failures MUST be observable

Silent success or failure is forbidden.

---

## 10. Change Control

This document is versioned.

- Any modification requires a version bump
- Validation changes MUST update test cases
- Certification criteria changes require governance review

---

## 11. Acceptance Statement

The validation plan for Nexus Core MVP1 is accepted when:

- Validation blocks all incorrect ingestion
- Only validated sources reach `INGESTED`
- Validation reports provide sufficient audit evidence

This document defines the **authoritative validation contract** for MVP1.

---

## 12. Validation Philosophy (Git Memory Compliance)

### Core Philosophy

Validation in Nexus Core MVP1 follows a **proof-of-correctness** model:

1. **Evidence-Based**: All checks rely on observable artifacts and database state, not in-memory promises
2. **All-or-Nothing**: Partial success is rejected; every check must pass for certification
3. **Non-Interference**: Validation never modifies ingestion state or fixes errors
4. **Deterministic**: Same source + same artifacts → same validation result
5. **Hard Gate**: Validation is the **only** path to `INGESTED` status
6. **Audit Trail**: Every validation run produces immutable reports

### Why This Approach

This philosophy ensures:
- **Reproducibility**: Failed ingestion can be debugged from reports alone
- **Trust**: No component can bypass validation
- **Simplicity**: Clear binary outcome (PASS/FAIL)
- **Accountability**: Every certification is traceable

### Source Citations

| Section | Source Document | Reference |
|---------|-----------------|-----------|
| Preconditions (Section 3) | INGESTION_ARCHITECTURE_v1.0.md | Section 13.2 |
| Governance Checks (Section 5.1) | GOVERNANCE_FLOW_v1.0.md | Sections 4, 7 |
| Artifact Checks (Section 5.2) | ARTIFACT_CONTRACT_v1.0.md | Sections 3, 5 |
| Provenance Checks (Section 5.3) | ARTIFACT_CONTRACT_v1.0.md | Section 7 |
| Dual-Extractor Checks (Section 5.4) | ARTIFACT_CONTRACT_v1.0.md | Section 6 |
| Chunk Checks (Section 5.5) | INGESTION_ARCHITECTURE_v1.0.md | Section 10.2 |
| Storage Checks (Section 5.6) | INGESTION_ARCHITECTURE_v1.0.md | Section 11 |
| Deactivation Checks (Section 5.8) | GOVERNANCE_FLOW_v1.0.md | Section 4.4 |
| Reports (Section 7) | INGESTION_ARCHITECTURE_v1.0.md | Section 13.4 |
| FR Mapping (Section 8) | REQUIREMENTS_v1.0.md | FR-023 to FR-026 |
| Test Mapping (Section 8) | TEST_CASES_v1.0.md | T-ING-012, T-ING-013 |

### Validation-Related Commits

- `895e6d9` - Initial commit: Nexus Core MVP1 specification documents

