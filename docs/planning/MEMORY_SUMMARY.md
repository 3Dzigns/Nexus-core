# MEMORY_SUMMARY.md

**Task ID:** ING-PLAN-000
**Purpose:** Repository Memory Initialization for Ingestion Planning
**Created:** 2026-01-15

---

## Purpose of MVP1 Ingestion

**Source:** INGESTION_ARCHITECTURE_v1.0.md Section 0

**Ingestion correctness is a hard dependency** for all downstream capabilities (querying, character actions, GM tools). If ingestion is incorrect, the system is considered non-functional.

The ingestion specification defines:
- Source discovery and governance
- Admin approval workflow
- Dual extraction (Docling + Unstructured)
- Artifact/manifest storage conventions
- Normalization, enrichment, chunking
- Storage + indexing in Postgres/pgvector
- Deactivation/removal behavior
- Validation & certification requirements
- Non-negotiable constraints for testing and observability

### MVP1 Scope

**In Scope:**
- Filesystem-based source intake from Windows host directory mounted into Docker
- Governance state machine enforced via Pydantic models
- Admin approval/denial of newly detected sources
- Duplicate detection by SHA-256 with admin decision required
- Extraction using both Docling and Unstructured for each approved source
- Preservation of tool outputs (two manifests, two chunk sets)
- Content-aware metadata enrichment (deterministic; no LLM-per-chunk)
- Chunking, embedding, and storage in Postgres with pgvector
- Full-text search (FTS) indexing
- Post-ingestion validation (certification) with human-readable reports
- Automatic deactivation on source file removal

**Out of Scope (MVP1):**
- Canonical merge of Docling + Unstructured into one manifest
- Graph-based reasoning, multi-step world state
- Payments/billing enforcement
- Module content ingestion for players

---

## Non-Negotiable Constraints

### Architectural Principles

**Source:** ARCHITECTURE_v1.0.md Section 1

1. **Governance First**
   - No data enters the system without governance
   - All state transitions are explicit and enforced
   - Deactivation is preferred over deletion

2. **Deterministic Before AI**
   - Deterministic logic is always preferred over AI
   - AI is used only where interpretation or synthesis is required
   - AI never mutates authoritative state

3. **Separation of Concerns**
   - Ingestion ≠ Retrieval ≠ Synthesis
   - UI ≠ API ≠ Workers
   - Player ≠ GM ≠ Game scopes are strictly separated

4. **Testability and Observability**
   - Every step must be testable inside Docker
   - All failures must be observable
   - No silent retries without logs

### Testing Rules (Non-Negotiable)

**Source:** INGESTION_ARCHITECTURE_v1.0.md Section 14

- All tests run inside containers
- Test data comes only from `/transfer_station/sources/` (no synthetic data generation)
- PowerShell scripts may invoke container commands but do not execute tests on host
- A cleanup script must remove all test-scoped data and artifacts to return the environment to a clean state

---

## Phasing Expectations

**Source:** ACCEPTANCE_CRITERIA_v1.0.md Section 3

Implementation proceeds in strict phase order (no skipping):

| Phase | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| 0 | Project & Governance Foundations | **Complete** | Repo structure, Docker Compose, governance state machine |
| 1 | Source Discovery & Approval | Pending | Source detection, governance records, admin approval, duplicate detection |
| 2 | Extraction & Artifact Generation | Pending | Dual extraction (Docling + Unstructured), raw manifests, provenance |
| 3 | Normalization, Enrichment, Chunking | Pending | Canonical manifests, content-aware metadata, dual chunk sets |
| 4 | Storage, Indexing & Validation | Pending | Postgres storage, embeddings, FTS indexes, validation PASS |
| 5 | Deactivation & Removal | Pending | Source removal handling, admin removal requests |
| 6 | Query & Action Safety | Pending | Game context restriction, active character actions |
| 7 | Feedback, Limits & UI Enforcement | Pending | Feedback collection, ranking adjustment, tier enforcement |

### Phase Acceptance Model

- A phase is accepted only when all required artifacts exist, all mapped test cases pass, and validation reports confirm correctness
- No partial acceptance is allowed
- Failed validation blocks acceptance
- MVP1 is accepted when all phases 0-7 meet acceptance criteria

---

## Authoritative Document References

| Document | Location | Purpose |
|----------|----------|---------|
| INGESTION_ARCHITECTURE_v1.0.md | docs/architecture/ | Authoritative ingestion specification |
| ARCHITECTURE_v1.0.md | docs/architecture/ | System-wide architecture |
| REQUIREMENTS_v1.0.md | docs/requirements/ | Testable functional/non-functional requirements |
| ACCEPTANCE_CRITERIA_v1.0.md | docs/requirements/ | Phase acceptance gates |
| TEST_PLAN_v1.0.md | docs/testing/ | Testing strategy and execution rules |
| TEST_CASES_v1.0.md | docs/testing/ | Concrete test case definitions |

---

## Git Memory Protocol

This document establishes Git as the authoritative memory context for ingestion planning.

**Protocol:**
1. Pull latest before starting any planning task
2. Read commit history for affected files
3. Do NOT modify existing specification documents
4. Create new artifacts only when required
5. Use task ID prefix in commit messages: `[ING-PLAN-XXX]`
6. Document aligned specs in commit messages

**Commit History (docs/):**
- `895e6d9` - Initial commit: Nexus Core MVP1 specification documents
