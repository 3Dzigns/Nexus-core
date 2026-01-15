# REQUIREMENTS_v1.0

## 0. Purpose
This document defines the **explicit functional and non-functional requirements** for Nexus Core MVP1.

These requirements are **testable obligations**, not design suggestions. Any implementation that does not satisfy these requirements is considered incorrect, regardless of intent.

This document derives authority from:
- ARCHITECTURE_v1.0.md
- INGESTION_ARCHITECTURE_v1.0.md
- QUERY_POLICY_v1.0.md
- ACCESS_MATRIX_v1.0.md
- FAULT_RECOVERY_v1.0.md

---

## 1. Scope Definition

### 1.1 MVP1 Goals
MVP1 must:
- Reliably ingest TTRPG source material
- Enforce governance and approval
- Preserve extracted data from multiple tools
- Support deterministic + AI-assisted queries
- Respect role, context, and source scope

### 1.2 Explicit Non-Goals
MVP1 does **not** include:
- Graph reasoning or multi-step world state
- Automated billing or payments
- Player-visible module content
- Long-term NPC memory
- Cross-game persistence of state

---

## 2. Functional Requirements (FR)

### 2.1 Source Discovery & Governance

**FR-001** The system MUST detect files present in `/transfer_station/sources/` that have **no governance record** (by SHA-256) and treat them as candidates for governance.

**FR-002** The system MUST compute a SHA-256 hash for every discovered file.

**FR-003** The system MUST create a governance record for every discovered file before any processing occurs.

**FR-004** The system MUST NOT ingest or extract any source without explicit admin approval.

**FR-005** If a discovered file has a SHA-256 matching an existing source, the system MUST flag it as a duplicate and require an admin decision.

**FR-006** Admins MUST be able to approve or deny sources via the Admin UI or API.

**FR-007** Denied sources MUST NOT proceed to extraction and MUST remain visible for audit.

---

### 2.2 Source Removal & Deactivation

**FR-008** If an approved source file is removed from disk, the system MUST automatically deactivate the source.

**FR-009** Deactivation MUST soft-disable all derived chunks, embeddings, and indexes.

**FR-010** Source removal MUST generate an admin removal request for audit purposes.

---

### 2.3 Extraction

**FR-011** Every approved source MUST be processed by both Docling and Unstructured extractors.

**FR-012** The system MUST preserve extractor outputs independently and MUST NOT merge them canonically in MVP1.

**FR-013** Extractors MUST record tool version, run ID, timestamps, and provenance metadata.

**FR-014** OCR-derived text MUST be distinguishable from native text in extractor output.

---

### 2.4 Normalization & Metadata Enrichment

**FR-015** Extractor outputs MUST be normalized into a canonical internal schema.

**FR-016** Metadata enrichment MUST be content-aware and document-aware.

**FR-017** Metadata enrichment MUST be deterministic and MUST NOT require per-chunk LLM calls.

**FR-018** Metadata terms MUST be associated with a system (e.g., Pathfinder, Cyberpunk).

---

### 2.5 Chunking & Storage

**FR-019** The system MUST create separate chunk sets for Docling and Unstructured outputs.

**FR-020** Each chunk MUST retain sufficient metadata for retrieval, ranking, and audit.

**FR-021** Chunks MUST be stored in Postgres with pgvector embeddings.

**FR-022** Full-text search indexes MUST be created for all text chunks.

---

### 2.6 Validation & Certification

**FR-023** The system MUST validate ingestion completeness before marking a source as ingested.

**FR-024** Validation MUST confirm artifacts, chunks, embeddings, and indexes exist.

**FR-025** A source MUST NOT be marked `INGESTED` unless validation passes.

**FR-026** Validation MUST produce both machine-readable and human-readable reports.

---

### 2.7 Query & Orchestration

**FR-027** The system MUST classify queries by complexity before AI invocation.

**FR-028** The system MUST short-circuit queries resolvable without AI.

**FR-029** The system MUST support keyword, vector, and hybrid retrieval.

**FR-030** Hybrid retrieval MUST use reranking to reconcile keyword and vector results.

**FR-031** The orchestrator MUST enrich missing query metadata when possible.

---

### 2.8 Role, Context, and Scope Enforcement

**FR-032** Queries executed in a game context MUST use only sources linked to that game.

**FR-033** Queries executed outside a game context MUST use only sources owned by the user account.

**FR-034** GM-only sources (modules, personas) MUST NOT be visible to players and MUST be accessible only to the **GM owner of the game** to which they are linked.

---

### 2.9 Character Actions

**FR-035** Action resolution MUST use the active character for the current game.

**FR-036** The system MUST apply correct rules and explain corrections for partially invalid actions.

---

### 2.10 Feedback

**FR-037** The system MUST collect thumbs-up / thumbs-down feedback on AI responses.

**FR-038** Feedback MUST affect ranking only within the same system and use a deterministic score:
- score = up_votes - down_votes (clamped to [-10, 10])
- ranking adjustment is proportional to score within the same system_id

**FR-039** Repeated negative feedback MUST lower rank and flag content for admin review.

---

### 2.11 Limits & Enforcement

**FR-040** Tier limit violations MUST hard-lock the UI until resolved.

**FR-041** Resolution screens MUST allow users to select which items become inactive, using tier limits from `tier_limits`.

Storage quotas are **not enforced** in MVP1.

---

## 3. Non-Functional Requirements (NFR)

### 3.1 Reliability

**NFR-001** Ingestion steps MUST be idempotent and safe to retry.

**NFR-002** Partial failures MUST be observable and logged.

**NFR-010** Chunk IDs MUST be deterministic across re-ingestion for identical content and tool versions.

---

### 3.2 Performance

**NFR-003** Simple queries SHOULD complete within interactive latency bounds.

**NFR-004** (Removed for MVP1 DEV/TEST) Ingestion throughput performance targets are deferred until a production-like environment exists.

Admin approval throughput targets are deferred to post-MVP1.

---

### 3.3 Security

**NFR-005** Role and context checks MUST be enforced server-side.
**NFR-011** JWT validation MUST follow JWT_SPEC_v1.0.md.

**NFR-006** Admin-only actions MUST NOT be accessible via UI manipulation.

---

### 3.4 Testability

**NFR-007** All tests MUST run inside Docker containers.

**NFR-008** Test runs MUST NOT create synthetic source data.

**NFR-009** Cleanup scripts MUST restore the environment to a clean state.

---

## 4. Traceability

Each requirement MUST be traceable to:
- architecture elements
- test cases
- validation reports

---

## 5. Change Control

This document is versioned.
- Any change requires a version bump
- Requirement changes MUST update affected test cases

---

## 6. Acceptance Statement

MVP1 requirements are satisfied when:
- All FRs and NFRs are implemented
- All test cases pass
- Validation reports confirm correctness

This document defines the contractual requirements for Nexus Core MVP1.

