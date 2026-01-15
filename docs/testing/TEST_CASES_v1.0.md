# TEST_CASES_v1.0

## 0. Purpose
This document defines **concrete, executable test cases** for Nexus Core MVP1.

Each test case:
- Maps directly to one or more FR/NFR IDs
- Uses real source data placed in the Transfer Station
- Can be executed inside Docker
- Produces observable, verifiable outcomes

Passing all applicable test cases is required for MVP1 acceptance.

---

## 1. Conventions

### 1.1 Test Case Format
Each test case follows:
- **Test ID**
- **Title**
- **Related Requirements**
- **Preconditions**
- **Steps**
- **Expected Results**

### 1.2 Test Data Rules
- Use real PDFs / text / images
- No synthetic source generation
- Filenames may vary; SHA-256 is authoritative

---

## 2. Ingestion – Discovery & Governance

### T-ING-001 — Detect Ungoverned Source
**Related Requirements:** FR-001, FR-002, FR-003

**Preconditions:**
- Clean environment
- No governance record exists for the test file

**Steps:**
1. Place a PDF into `/transfer_station/sources/`
2. Wait for discovery scan

**Expected Results:**
- SHA-256 is computed
- Governance record is created
- Status is `PENDING_APPROVAL`

---

### T-ING-002 – Duplicate Source Detection
**Related Requirements:** FR-005

**Preconditions:**
- A source with known SHA-256 already exists in governance

**Steps:**
1. Place a second copy of the same file in `/transfer_station/sources/`

**Expected Results:**
- Duplicate is detected
- Ingestion does not proceed
- Admin decision is required

---

### T-ING-002A – Duplicate State Transitions
**Related Requirements:** FR-005

**Preconditions:**
- Existing source with matching SHA-256

**Steps:**
1. Place a duplicate file in `/transfer_station/sources/`
2. Verify status is `DUPLICATE_DETECTED`
3. Admin chooses `IGNORE_DUPLICATE`
4. Verify status becomes `PENDING_APPROVAL`
5. Admin chooses `ALLOW_SEPARATE_INSTANCE`
6. Verify status becomes `APPROVED`

**Expected Results:**
- Duplicate status is visible
- Admin decisions move the source to the correct next state

---

### T-ING-003 – Denied Source Is Not Ingested
**Related Requirements:** FR-004, FR-007

**Preconditions:**
- Source is in `PENDING_APPROVAL`

**Steps:**
1. Admin denies the source

**Expected Results:**
- Status becomes `DENIED`
- No extraction jobs are created

---

### T-GOV-005 – Denial Reopen
**Related Requirements:** FR-006

**Preconditions:**
- Source is `DENIED`

**Steps:**
1. Admin reopens the source for approval

**Expected Results:**
- Status becomes `PENDING_APPROVAL`

---

## 3. Ingestion – Approval & Extraction

### T-ING-004 — Approved Source Triggers Dual Extraction
**Related Requirements:** FR-004, FR-011, FR-012

**Preconditions:**
- Source is `PENDING_APPROVAL`

**Steps:**
1. Admin approves the source

**Expected Results:**
- Ingestion job is queued
- Docling extractor runs
- Unstructured extractor runs
- Raw manifests for both tools are created

---

### T-ING-005 — Extractor Provenance Recorded
**Related Requirements:** FR-013

**Preconditions:**
- Extraction has completed

**Steps:**
1. Inspect raw manifest metadata

**Expected Results:**
- Tool ID, version, run ID, timestamps are present

---

### T-ING-006 — OCR Text Is Distinguished
**Related Requirements:** FR-014

**Preconditions:**
- Source contains scanned pages

**Steps:**
1. Inspect normalized manifest blocks

**Expected Results:**
- OCR-derived text blocks are flagged distinctly

---

## 4. Normalization, Enrichment, Chunking

### T-ING-007 — Normalization Produces Canonical Blocks
**Related Requirements:** FR-015

**Preconditions:**
- Raw manifests exist

**Steps:**
1. Run normalization stage

**Expected Results:**
- Canonical block schema is produced for each tool

---

### T-ING-008 – Content-Aware Metadata Enrichment
**Related Requirements:** FR-016, FR-017, FR-018

**Preconditions:**
- Normalized manifests exist

**Steps:**
1. Run enrichment stage

**Expected Results:**
- Section titles and content types are added
- System-specific metadata is present
- No LLM calls are made per chunk

---

### T-ING-008A – Deterministic Enrichment Verification
**Related Requirements:** FR-017

**Preconditions:**
- Enrichment rules are versioned

**Steps:**
1. Run enrichment
2. Record enriched manifest output
3. Re-run enrichment with the same rules version

**Expected Results:**
- Enriched output is identical across runs

---

### T-ING-009 – Dual Chunk Sets Created
**Related Requirements:** FR-019, FR-020

**Preconditions:**
- Enriched manifests exist

**Steps:**
1. Run chunking stage

**Expected Results:**
- Docling chunk set exists
- Unstructured chunk set exists
- Each chunk contains required metadata

---

### T-ING-009A – Chunk ID Determinism
**Related Requirements:** NFR-010

**Preconditions:**
- Chunking completed for a source

**Steps:**
1. Record all `chunk_id` values
2. Re-run chunking with identical inputs and tool versions

**Expected Results:**
- All `chunk_id` values are identical across runs

---

## 5. Storage & Indexing

### T-ING-010 — Chunks Stored with Embeddings
**Related Requirements:** FR-021

**Preconditions:**
- Chunk files exist

**Steps:**
1. Run embedding + storage stage

**Expected Results:**
- Chunk rows exist in Postgres
- pgvector embeddings are populated

---

### T-ING-011 — Full-Text Search Index Created
**Related Requirements:** FR-022

**Preconditions:**
- Chunks stored in DB

**Steps:**
1. Inspect DB indexes

**Expected Results:**
- FTS GIN index exists and is populated

---

## 6. Validation & Certification

### T-ING-012 — Validation Passes for Good Source
**Related Requirements:** FR-023, FR-024, FR-025, FR-026

**Preconditions:**
- Full ingestion pipeline completed

**Steps:**
1. Run validator

**Expected Results:**
- Validation report generated (MD + JSON)
- Source marked `INGESTED`

---

### T-ING-013 – Validation Fails on Missing Artifact
**Related Requirements:** FR-024

**Preconditions:**
- Remove one expected artifact manually

**Steps:**
1. Run validator

**Expected Results:**
- Validation fails
- Missing artifact is reported

---

### T-VAL-001 – Validation Failure Diagnostics
**Related Requirements:** FR-026

**Preconditions:**
- Validation is run on a failing source

**Steps:**
1. Trigger validation failure

**Expected Results:**
- Report includes explicit failure reasons
- Report is written to `/transfer_station/artifacts/reports/<doc_id>/`

---

### T-VAL-002 – Chunk Collision Detection
**Related Requirements:** NFR-010

**Preconditions:**
- Duplicate chunk IDs are introduced

**Steps:**
1. Run validator

**Expected Results:**
- Validation fails
- Duplicate chunk IDs are listed

---

### T-VAL-003 – Chunk Size Limit Enforcement
**Related Requirements:** FR-023

**Preconditions:**
- A chunk exceeds the maximum allowed size

**Steps:**
1. Run validator

**Expected Results:**
- Validation fails
- Report identifies the oversized chunk

---

## 7. Deactivation & Removal

### T-ING-014 – Source Removal Deactivates Data
**Related Requirements:** FR-008, FR-009, FR-010

**Preconditions:**
- Source is `INGESTED`

**Steps:**
1. Remove source file from `/transfer_station/sources/`

**Expected Results:**
- Source status becomes `DEACTIVATED`
- Derived chunks become inactive
- Admin removal request is created
- Deactivation occurs within 120 seconds of file removal

---

### T-ING-015 – Extraction Failure Handling
**Related Requirements:** NFR-002

**Preconditions:**
- Source is `APPROVED`

**Steps:**
1. Force Docling worker failure during extraction

**Expected Results:**
- Status becomes `ERROR`
- Failure is logged with actionable details

---

### T-ING-016 – Partial Chunk Storage Cleanup
**Related Requirements:** NFR-001

**Preconditions:**
- Chunk storage stage is running

**Steps:**
1. Interrupt storage mid-run
2. Retry ingestion

**Expected Results:**
- No duplicate chunk rows
- Ingestion completes without orphaned data

---

## 8. Query & Scope Enforcement

### T-QRY-001 — Game Context Restricts Sources
**Related Requirements:** FR-032

**Preconditions:**
- Multiple sources exist
- Only some are linked to the active game

**Steps:**
1. Execute query in game context

**Expected Results:**
- Only game-linked sources are used

---

### T-QRY-002 — No Sources Returns Friendly Response
**Related Requirements:** FR-033

**Preconditions:**
- No sources linked to game or user

**Steps:**
1. Execute query

**Expected Results:**
- Friendly "no authoritative sources" message

---

## 9. Character Actions

### T-ACT-001 — Active Character Used for Action
**Related Requirements:** FR-035

**Preconditions:**
- Player has an active character

**Steps:**
1. Submit action query

**Expected Results:**
- Active character is used automatically

---

### T-ACT-002 — Partial Action Correction Explained
**Related Requirements:** FR-036

**Preconditions:**
- Action references valid weapon but incorrect modifier

**Steps:**
1. Submit action

**Expected Results:**
- Correct modifier applied
- Explanation provided

---

## 10. Feedback

### T-FBK-001 – Feedback Lowers Rank and Flags
**Related Requirements:** FR-037, FR-038, FR-039

**Preconditions:**
- Chunk has received repeated negative feedback

**Steps:**
1. Submit thumbs-down feedback repeatedly

**Expected Results:**
- Chunk ranking is lowered
- Chunk is flagged for admin review

---

## 11. Security & Access

### T-SEC-001 – Role-Based Endpoint Access
**Related Requirements:** NFR-005, NFR-011

**Preconditions:**
- JWT tokens for PLAYER, GM, ADMIN

**Steps:**
1. Call admin-only endpoints with each role

**Expected Results:**
- ADMIN succeeds
- PLAYER and GM receive 403

---

### T-SEC-002 – Admin Audit-Only Enforcement
**Related Requirements:** NFR-006

**Preconditions:**
- Admin role token

**Steps:**
1. Execute a query

**Expected Results:**
- Response is labeled audit-only
- No gameplay actions are executed

---

### T-SEC-003 – GM-Only Scope Bypass Prevention
**Related Requirements:** FR-034

**Preconditions:**
- GM role without game ownership

**Steps:**
1. Query GM-only source

**Expected Results:**
- Access denied

---

## 12. Limits & Enforcement

### T-LIM-001 — Limit Violation Hard Locks UI
**Related Requirements:** FR-040, FR-041

**Preconditions:**
- User exceeds tier limits

**Steps:**
1. Attempt to access UI

**Expected Results:**
- Only limit resolution screen is accessible

---

## 13. Cleanup

### T-CLN-001 — Cleanup Restores Clean Environment
**Related Requirements:** NFR-009

**Preconditions:**
- One or more test runs completed

**Steps:**
1. Run cleanup script

**Expected Results:**
- Test-scoped artifacts removed
- DB reset
- Environment ready for new test run

---

## 14. Non-Functional Requirements

### T-NFR-001 — Idempotency Verification
**Related Requirements:** NFR-001, NFR-010

**Preconditions:**
- Source ingested successfully

**Steps:**
1. Re-ingest the same source with the same tool versions

**Expected Results:**
- Chunk IDs and artifacts are identical

---

### T-NFR-002 — Partial Failure Observability
**Related Requirements:** NFR-002

**Preconditions:**
- Ingestion in progress

**Steps:**
1. Force a worker failure

**Expected Results:**
- Status becomes `ERROR`
- Logs contain actionable failure details

---

### T-NFR-003 — Query Latency Measurement
**Related Requirements:** NFR-003

**Preconditions:**
- Known-good sources ingested

**Steps:**
1. Run a simple keyword query

**Expected Results:**
- Latency is captured and reported

---

## 15. Acceptance Statement

All applicable test cases in this document must pass for Nexus Core MVP1 to be considered test-complete.
