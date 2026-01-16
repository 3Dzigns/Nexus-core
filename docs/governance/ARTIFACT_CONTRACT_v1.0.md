# ARTIFACT_CONTRACT_v1.0.md
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Planning Task:** ING-PLAN-004 - Artifact and Manifest Contract Plan

---

## 1. Purpose

This document defines the **authoritative artifact and manifest contracts** for Nexus Core MVP1 ingestion.

Its purpose is to:
- Lock artifact expectations before code exists
- Ensure deterministic validation and auditability
- Prevent silent data loss or implicit merges
- Provide a fixed contract for implementation and validation agents

Any artifact, directory, or metadata not defined here is **out of scope** for MVP1.

---

## 2. Core Artifact Principles (Non-Negotiable)

- Every ingestion stage MUST produce observable artifacts
- Artifacts MUST be written to disk before state transitions advance
- Artifacts are immutable once written
- Deactivation NEVER deletes artifacts
- Validation relies on artifacts, not in-memory state
- Docling and Unstructured outputs are never merged canonically in MVP1

Artifact immutability clarifications:
- Each pipeline stage writes NEW artifacts
- Prior artifacts are never modified
- Example: enrichment writes `docling_enriched.json`; normalized artifacts remain unchanged
- Rollback exception: if ingestion fails before certification, all artifacts for the doc_id are removed

---

## 3. Artifact Root and Directory Structure

All ingestion artifacts MUST reside under the Transfer Station root:

```
/transfer_station/
  artifacts/
    manifests/
      <doc_id>/
        raw/
          docling_manifest.json
          unstructured_manifest.json
          original_source.json
        normalized/
          docling_normalized.json
          unstructured_normalized.json
        enriched/
          docling_enriched.json
          unstructured_enriched.json
    chunks/
      <doc_id>/
        docling_chunks.jsonl
        unstructured_chunks.jsonl
    assets/
      <doc_id>/
        images/
          ... extracted image files ...
    reports/
      <doc_id>/
        validation_<run_id>.md
        validation_<run_id>.json
```

No ingestion component may write artifacts outside this structure.

Enrichment rules configuration (not an artifact):
- Location: `/config/enrichment_rules/{system_id}.yaml`

---

## 4. Document Identity and Traceability

Each artifact MUST be traceable to a single source.

### 4.1 Document Identifier

Each document is identified by:
- `doc_id` (format: `<original_filename>__<sha256>`)
- `source_sha256` (content-derived)

Both identifiers MUST appear in:
- filenames (where practical)
- artifact metadata
- manifests

---

## 5. Required Artifact Types

The following artifact types are **mandatory** for a document to be considered ingestible.

### 5.1 Original Source Artifact

**Location:**
```
/transfer_station/artifacts/manifests/<doc_id>/raw/
```

**Contents:**
- `original_source.json`, referencing the original source file (by filename and sha256)

**Required Metadata:**
- doc_id
- source_sha256
- original_filename
- discovery_timestamp

---

### 5.2 Raw Extractor Manifests (Dual)

Raw extractor outputs MUST be preserved independently.

**Locations:**
```
.../raw/docling_manifest.json
.../raw/unstructured_manifest.json
```

**Required Metadata (Both):**
- doc_id
- source_sha256
- extractor_name
- extractor_version
- run_id
- start_timestamp
- end_timestamp
- ocr_flag per block (if applicable)

No canonical merge is permitted.

---

### 5.3 Normalized Manifests (Dual)

Extractor outputs MUST be normalized into a canonical internal schema, while remaining tool-separated.

**Locations:**
```
.../normalized/docling_normalized.json
.../normalized/unstructured_normalized.json
```

**Required Fields:**
- block_id
- block_type
- text_content
- page_number (if available)
- ocr_flag
- tool_origin
- doc_id

---

### 5.4 Enriched Manifests (Dual)

Metadata enrichment augments normalized manifests.

**Required Enrichment Fields:**
- section_title
- content_type
- system_tag (e.g., Pathfinder, Cyberpunk)
- deterministic_enrichment_version
- enrichment_rules_version

Enrichment MUST be deterministic and reproducible.

---

### 5.5 Chunk Artifacts (Dual Sets)

Chunking produces **two independent chunk sets**.

**Locations:**
```
.../chunks/docling_chunks.jsonl
.../chunks/unstructured_chunks.jsonl
```

**Each Chunk MUST Contain:**
- chunk_id
- doc_id
- tool_origin
- chunk_text
- section_title
- content_type
- system_tag
- chunk_index
- chunk_sha256

Chunk ID format:
- `{doc_id}::{tool_id}::{chunk_sha256[:16]}`

---

### 5.6 Storage and Index Evidence

Artifacts MUST support validation of storage.

**Evidence Includes:**
- DB rows referencing chunk_id
- Embedding vectors per chunk
- Full-text index presence

Evidence may be indirect (DB inspection) but MUST be provable.

---

### 5.7 Validation Reports

Validation produces **two reports per run**.

**Locations:**
```
/transfer_station/artifacts/reports/<doc_id>/
```

**Required Reports:**
- `validation_<run_id>.json`
- `validation_<run_id>.md`

**Required Fields:**
- doc_id
- validation_timestamp
- pass_fail
- failed_checks (if any)

---

## 6. Dual-Manifest Rule (Critical)

- Docling and Unstructured artifacts MUST both exist
- Failure of either blocks ingestion
- Validation MUST fail if either is missing

This rule is non-negotiable for MVP1.

---

## 7. Provenance and Determinism Requirements

All artifacts MUST record:
- tool name
- tool version
- run identifier
- timestamps

Given the same source and tool versions, artifacts SHOULD be reproducible.

---

## 8. Deactivation Semantics

When a source is deactivated:
- Artifacts remain on disk
- DB rows are soft-disabled
- Validation history remains readable

Artifacts MUST NOT be deleted automatically.

---

## 9. Validation Dependencies

Validation depends on:
- Presence of all required artifacts
- Correct directory placement
- Required metadata fields

Missing or malformed artifacts MUST cause validation failure.

---

## 10. Alignment and References

This document is aligned with:
- INGESTION_ARCHITECTURE_v1.0.md
- GOVERNANCE_FLOW_v1.0.md
- REQUIREMENTS_v1.0.md (FR-011 through FR-026)
- TEST_CASES_v1.0.md (T-ING-004 through T-ING-013)

Any discrepancy must be raised as a planning issue.

---

## 11. Change Control

This document is versioned.

- Any change requires a version bump
- Artifact contract changes MUST update validation logic and tests

---

## 12. Acceptance Statement

The artifact contract for Nexus Core MVP1 is accepted when:
- All required artifacts are produced during ingestion
- Validation relies solely on these artifacts
- No implicit or undocumented artifacts exist

This document defines the **authoritative artifact contract** for MVP1.

---

## 13. Design Rationale (Git Memory Compliance)

### Why Artifacts Are Preserved Separately

Docling and Unstructured outputs are preserved independently (not merged) for the following reasons:

1. **Tool Evolution**: Extractors improve over time; preserving raw outputs enables re-normalization without re-extraction
2. **Comparative Analysis**: Dual outputs enable quality comparison and tool selection validation
3. **Determinism Verification**: Independent artifacts prove each tool's reproducibility
4. **Failure Isolation**: Tool-specific issues are traceable to specific artifacts
5. **MVP1 Scope**: Canonical merge is deferred to MVP2+ when merge strategies can be properly evaluated
6. **Auditability**: Every transformation stage is observable and verifiable

This decision is documented in:
- INGESTION_ARCHITECTURE_v1.0.md Section 7.1 (Dual extraction required behavior)
- INGESTION_ARCHITECTURE_v1.0.md Section 10.1 (Dual chunk sets)

### Source Citations

| Section | Source Document | Reference |
|---------|-----------------|-----------|
| Directory Structure (Section 3) | INGESTION_ARCHITECTURE_v1.0.md | Section 3 |
| Document Identity (Section 4) | INGESTION_ARCHITECTURE_v1.0.md | Section 3.1 |
| Raw Manifests (Section 5.2) | INGESTION_ARCHITECTURE_v1.0.md | Section 7.2 |
| Normalized Manifests (Section 5.3) | INGESTION_ARCHITECTURE_v1.0.md | Section 8.2 |
| Enriched Manifests (Section 5.4) | INGESTION_ARCHITECTURE_v1.0.md | Section 9.2 |
| Chunk Artifacts (Section 5.5) | INGESTION_ARCHITECTURE_v1.0.md | Section 10.2 |
| Validation Reports (Section 5.7) | INGESTION_ARCHITECTURE_v1.0.md | Section 13.4 |
| Dual-Manifest Rule (Section 6) | INGESTION_ARCHITECTURE_v1.0.md | Section 7.1 |
| Tool Provenance (Section 7) | INGESTION_ARCHITECTURE_v1.0.md | Section 7.3 |
| Deactivation Semantics (Section 8) | INGESTION_ARCHITECTURE_v1.0.md | Section 12.2 |

### Artifact-Related Commits

- `895e6d9` - Initial commit: Nexus Core MVP1 specification documents

