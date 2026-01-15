# TEST_PLAN_v1.0

## 0. Purpose
This document defines the **testing strategy and execution rules** for Nexus Core MVP1.

The goal of testing in MVP1 is to **prove ingestion correctness and system safety**, not to optimize performance or UX. Any feature that cannot be tested according to this plan is considered incomplete.

This plan derives authority from:
- ARCHITECTURE_v1.0.md
- INGESTION_ARCHITECTURE_v1.0.md
- REQUIREMENTS_v1.0.md
- TEST_CORPUS_v1.0.md

---

## 1. Testing Principles

### 1.1 Governance-First Testing
- Tests MUST respect governance state transitions
- Tests MUST NOT bypass admin approval or validation steps

### 1.2 Container-Only Execution
- All tests MUST execute inside Docker containers
- The host OS may only be used to:
  - start/stop containers
  - mount volumes
  - invoke container commands
All test code, including unit tests that use in-memory databases, MUST run inside containers.

### 1.3 Determinism and Repeatability
- Given the same source files and tool versions, test results MUST be repeatable
- Tests MUST NOT depend on external network calls except for explicitly allowed APIs

---

## 2. Test Environment

### 2.1 Environment Scope
- Single combined **DEV/TEST** environment
- No production environment exists for MVP1

### 2.2 Required Services
The following services MUST be running for test execution:
- Postgres + pgvector (`nexus_db`)
- Ingestion worker(s)
- Docling worker
- Unstructured worker
- Validator
- API service

UI containers are optional for ingestion tests.

---

## 3. Test Data Rules

### 3.1 Source Data
- Test sources MUST be placed manually in `/transfer_station/sources/`
- Test sources MUST represent real-world formats (PDF, text, image)
- The system MUST NOT generate synthetic source documents
- The standard test corpus is defined in `TEST_CORPUS_v1.0.md`

### 3.2 Data Isolation
- Each test run MUST operate on a clean environment
- Artifacts and DB records from previous runs MUST NOT affect new runs

---

## 4. Test Types

### 4.1 Unit Tests

**Purpose:** Verify isolated logic components.

Examples:
- Governance state transition rules
- SHA-256 calculation
- Metadata enrichment rules

**Constraints:**
- Unit tests MUST NOT require external services
- Unit tests MAY use in-memory DBs where appropriate, but they MUST still run inside Docker

---

### 4.2 Integration Tests

**Purpose:** Verify multi-component interactions.

Examples:
- Source discovery → governance record creation
- Approval → extraction job enqueue
- Extraction → artifact creation

**Constraints:**
- Integration tests MUST run inside Docker
- Real containers MUST be used

---

### 4.3 End-to-End Ingestion Tests (Critical)

**Purpose:** Prove ingestion correctness.

Examples:
- Approved PDF ingested through full pipeline
- Dual manifests produced
- Chunks stored and indexed

**Constraints:**
- Tests MUST follow the exact ingestion sequence
- No steps may be skipped or mocked

---

### 4.4 Validation Tests

**Purpose:** Verify validator correctness.

Examples:
- Missing artifact detected
- Orphaned DB rows detected
- Deactivated sources excluded from retrieval

---

## 5. Test Execution Workflow

### 5.1 Standard Test Run

1. Clean environment
2. Start containers
3. Place test sources in `/transfer_station/sources/`
4. Observe discovery and governance creation
5. Approve sources
6. Run ingestion pipeline
7. Run validator
8. Capture reports

---

### 5.2 Cleanup Procedure (Mandatory)

After every test run:
- All test-ingested sources MUST be deactivated or removed
- All test-scoped artifacts under `/transfer_station/artifacts/` MUST be removed
- All DB records created during the test MUST be removed or reset

Cleanup MUST restore the environment to a known clean state.

---

## 6. Failure Handling

### 6.1 Expected Failures
Tests SHOULD explicitly cover failure scenarios, including:
- Duplicate source detection
- Denied source ingestion attempts
- Extractor failures

### 6.2 Failure Visibility
- All failures MUST be logged
- Failures MUST be observable via logs or reports
- Silent failures are not acceptable

---

## 7. Reporting

### 7.1 Required Outputs
Each test run MUST produce:
- Structured logs
- Validation reports (if ingestion occurred)

### 7.2 Report Locations
Reports MUST be written to:
- `/transfer_station/artifacts/reports/`

---

## 8. Automation

### 8.1 PowerShell Scripts
PowerShell scripts MAY be used to:
- start containers
- trigger test runs
- invoke validators

PowerShell scripts MUST NOT contain business logic.

### 8.2 CI/CD (Out of Scope)
- Automated CI pipelines are deferred until post-MVP1

---

## 9. Traceability

Each test MUST reference:
- One or more FR/NFR IDs
- Relevant architecture sections

---

## 10. Acceptance Criteria for Testing

Testing is considered sufficient for MVP1 when:
- All ingestion-related FRs have at least one passing test
- Validator passes for known-good sources
- Cleanup procedures restore a clean environment

---

## 11. Change Control

This document is versioned.
- Changes require a version bump
- Changes to this plan may require updates to test cases

---

## 12. Acceptance Statement

This test plan defines the authoritative testing strategy for Nexus Core MVP1.

