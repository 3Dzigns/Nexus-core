# INGESTION_DEPENDENCIES_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** INGESTION_ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines the **explicit dependency order** for the ingestion pipeline.
Each step lists the blockers and required outputs needed to proceed.

This document is **descriptive only**. It does not add new behavior.

---

## 2. Linear Dependency Order

1. **Source discovery**
   - Blockers: none
   - Required outputs: SHA-256 computed, governance record created, state `PENDING_APPROVAL`

2. **Admin approval**
   - Blockers: governance record exists, state `PENDING_APPROVAL`
   - Required outputs: state `APPROVED`, ingestion job enqueued

3. **Dual extraction (Docling + Unstructured)**
   - Blockers: state `APPROVED`, duplicate decision resolved
   - Required outputs: raw manifests for both tools, provenance metadata, extracted assets

4. **Normalization**
   - Blockers: both raw manifests present
   - Required outputs: normalized manifests for both tools

5. **Metadata enrichment**
   - Blockers: normalized manifests present
   - Required outputs: enriched manifests for both tools

6. **Chunking**
   - Blockers: enriched manifests present
   - Required outputs: docling and unstructured chunk sets

7. **Embedding and storage**
   - Blockers: chunk sets present
   - Required outputs: chunk rows in Postgres, embeddings, active flags set

8. **Indexing (FTS + vector)**
   - Blockers: stored chunks and embeddings
   - Required outputs: FTS and vector indexes populated

9. **Validation and certification**
   - Blockers: all artifacts and indexes present, state `INGESTING`
   - Required outputs: validation reports, state `INGESTED`

10. **Deactivation (on removal)**
    - Blockers: source removed from `/transfer_station/sources/`
    - Required outputs: state `DEACTIVATED`, soft-disabled data, admin removal request

---

## 3. Dependency Enforcement Rules

- No step may run if its blockers are unmet.
- Failure at any step halts progression.
- Validation is the only path to `INGESTED`.

Rollback on failure:
- If any step fails before certification, **all artifacts and DB rows for the doc_id MUST be removed**
- Governance state becomes `ERROR`
- A retry starts from a clean slate (no partial artifacts or rows)

---

## 4. Change Control

This document is versioned.
- Any change requires a version bump
- Dependency changes MUST update tests and validation logic

---

## 5. Source Citations (Git Memory Compliance)

Dependencies in this document are derived from the following authoritative sources:

| Step | Dependency | Source Document | Section |
|------|------------|-----------------|---------|
| 1 | Source Discovery | INGESTION_ARCHITECTURE_v1.0.md | Section 5 |
| 2 | Admin Approval | INGESTION_ARCHITECTURE_v1.0.md | Section 6 |
| 3 | Dual Extraction | INGESTION_ARCHITECTURE_v1.0.md | Section 7 |
| 4 | Normalization | INGESTION_ARCHITECTURE_v1.0.md | Section 8 |
| 5 | Metadata Enrichment | INGESTION_ARCHITECTURE_v1.0.md | Section 9 |
| 6 | Chunking | INGESTION_ARCHITECTURE_v1.0.md | Section 10 |
| 7 | Embedding & Storage | INGESTION_ARCHITECTURE_v1.0.md | Section 11 |
| 8 | Indexing | INGESTION_ARCHITECTURE_v1.0.md | Section 11.4-11.5 |
| 9 | Validation | INGESTION_ARCHITECTURE_v1.0.md | Section 13 |
| 10 | Deactivation | INGESTION_ARCHITECTURE_v1.0.md | Section 12 |

### Additional Source References

**Rollback behavior:**
- INGESTION_ARCHITECTURE_v1.0.md Section 17

**Governance state machine:**
- INGESTION_ARCHITECTURE_v1.0.md Section 4
- GOVERNANCE_FLOW_v1.0.md (full state transition rules)

**Initial commit establishing dependencies:**
- `895e6d9` - Initial commit: Nexus Core MVP1 specification documents