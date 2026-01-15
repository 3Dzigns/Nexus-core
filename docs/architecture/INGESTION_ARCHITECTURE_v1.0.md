# INGESTION_ARCHITECTURE_v1.0

## 0. Purpose
This document is the **authoritative specification** for the Nexus Core MVP1 ingestion pipeline.

**Ingestion correctness is a hard dependency** for all downstream capabilities (querying, character actions, GM tools). If ingestion is incorrect, the system is considered non-functional.

This spec defines:
- Source discovery and governance
- Admin approval workflow
- Dual extraction (Docling + Unstructured)
- Artifact/manifest storage conventions
- Normalization, enrichment, chunking
- Storage + indexing in Postgres/pgvector
- Deactivation/removal behavior
- Validation & certification requirements
- Non-negotiable constraints for testing and observability

---

## 1. Scope

### 1.1 In Scope (MVP1)
- Filesystem-based source intake from a Windows host directory mounted into Docker
- Governance state machine enforced via Pydantic models
- Admin approval/denial of newly detected sources
- Duplicate detection by SHA-256 with admin decision required
- Extraction using **both** Docling and Unstructured for each approved source
- Preservation of tool outputs (two manifests, two chunk sets)
- Content-aware metadata enrichment (deterministic; no LLM-per-chunk)
- Chunking, embedding, and storage in Postgres with pgvector
- Full-text search (FTS) indexing
- Post-ingestion validation (certification) with human-readable reports
- Automatic deactivation on source file removal, plus admin removal request creation

### 1.2 Out of Scope (MVP1)
- Canonical merge of Docling + Unstructured into one manifest (MVP1 uses dual datasets)
- Graph-based reasoning, multi-step world state, and complex query resolution (MVP2+)
- Payments/billing enforcement (tiers exist; payment flow does not)
- Module content ingestion and usage by players (module concepts exist; module pipeline not required for MVP1)

---

## 2. Environments & Runtime Constraints

### 2.1 Deployment Target
- **Docker Desktop on Windows**
- All ingestion steps run inside containers
- No tests are executed on the host OS (Windows) directly

### 2.2 Transfer Station (Host-Mounted Volume)
Host path (example):
- `E:\Transfer_Station\`

Mounted in containers as:
- `/transfer_station/`

**The host path is configurable** via environment variables, but all code assumes the container path `/transfer_station`.

---

## 3. Transfer Station Directory Layout (Authoritative)

Within `Transfer_Station`, the following structure is required:

```
Transfer_Station/
  sources/                 # dropzone: user places files here
  quarantine/              # denied or suspicious sources (optional)
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
  logs/
    ingestion/
      ... structured logs ...
```

### 3.1 Human-Friendly Identity Requirements
- `doc_id` must be stable and human-friendly (not just SHA)
- `doc_id` format: `<original_filename>__<sha256>`
- `doc_id` sanitization rules:
  - Allowed characters: `A-Z a-z 0-9 . _ -`
  - Replace any other character with `_`
  - Trim to 120 characters; if truncated, preserve the trailing `__<sha256>`
- All artifacts must be traceable back to:
  - original filename
  - source SHA-256
  - governance record

---

## 4. Governance Model (Pydantic-Enforced)

### 4.1 Governance is the Gate
No extraction, chunking, embedding, or indexing may occur unless:
- the source exists in governance
- the source has been **approved**

### 4.2 Source Identity
Every discovered source gets:
- `source_sha256` (primary identity)
- `original_filename`
- `first_seen_at`
- `current_path` (container path)
- `status`
- `state_version` (optimistic lock counter)

### 4.3 Source Status State Machine
Statuses (minimum set):
- `DISCOVERED` (seen on disk, not yet reviewed)
- `PENDING_APPROVAL` (queued for admin)
- `DUPLICATE_DETECTED` (duplicate SHA-256 detected; admin decision required)
- `APPROVED` (allowed to ingest)
- `DENIED` (not allowed to ingest)
- `INGESTING` (pipeline executing)
- `INGESTED` (pipeline completed + certified)
- `DEACTIVATED` (source removed from disk; data deactivated)
- `ERROR` (pipeline failed; requires admin review)

Allowed transitions (summary):
- DISCOVERED -> PENDING_APPROVAL
- DISCOVERED -> DUPLICATE_DETECTED
- PENDING_APPROVAL -> APPROVED | DENIED
- DENIED -> PENDING_APPROVAL (admin reopen)
- DUPLICATE_DETECTED -> PENDING_APPROVAL (IGNORE_DUPLICATE)
- DUPLICATE_DETECTED -> APPROVED (ALLOW_SEPARATE_INSTANCE)
- APPROVED -> INGESTING
- INGESTING -> INGESTED | ERROR
- INGESTED -> DEACTIVATED (on file removal)
- ERROR -> PENDING_APPROVAL (admin retries) | DEACTIVATED

**Pydantic rules** must prevent illegal transitions.

### 4.4 Duplicate Detection (Admin Decision Required)
If a newly discovered source has a SHA-256 matching an existing governance record:
- ingestion **must not proceed automatically**
- status becomes `DUPLICATE_DETECTED`
- admin must choose:
  - `IGNORE_DUPLICATE`
  - `ALLOW_SEPARATE_INSTANCE` (rare; still uses same sha; creates distinct doc_id)

MVP1 default expectation: **IGNORE_DUPLICATE**.

---

## 5. Source Discovery

### 5.1 Discovery Trigger
- A periodic scanner (or watcher) scans `/transfer_station/sources/`
- Any file not present in governance by SHA is treated as new

### 5.2 Discovery Output
On discovery:
- compute SHA-256
- create governance record
- set status `PENDING_APPROVAL`
- surface to Admin UI

### 5.3 Removal Detection
If a source file previously known to governance is missing from disk:
- automatically set governance status to `DEACTIVATED`
- **deactivate** all derived DB records (chunks, embeddings, FTS visibility)
- create an **admin removal request** record for audit/review
  - recorded as a governance_events row with `event_type = REMOVAL_REQUEST`

Removal detection mechanism:
- Component: ingestion worker
- Mechanism: polling `/transfer_station/sources/`
- Poll interval: 60 seconds (configurable)
- Latency tolerance: 120 seconds
- On removal: write a `REMOVAL_REQUEST` governance event

No deletions occur automatically.

---

## 6. Admin Approval Workflow

### 6.1 Admin UI Responsibilities
Admin sees:
- filename
- sha-256
- size/type
- first-seen timestamp
- duplicate flags

Admin actions:
- Approve
- Deny (requires reason)
- Resolve duplicate decision

### 6.2 Approval Side Effects
On approval:
- status becomes `APPROVED`
- ingestion worker enqueues an ingestion job

On denial:
- status becomes `DENIED`
- source remains visible for audit
- source may optionally be moved to quarantine (policy-driven)

---

## 7. Extraction (Dual Tools)

### 7.1 Required Behavior
For each approved source:
- run **Docling** extractor → manifest + assets
- run **Unstructured** extractor → manifest + assets

Both outputs are preserved.

### 7.2 Output Requirements
Each extractor run must produce:
- `raw manifest` (tool native or lightly wrapped)
- extracted images (if present)
- OCR text blocks flagged as `ocr_text` when applicable

### 7.3 Tool Provenance
Every extractor output must include:
- `tool_id` = `docling | unstructured`
- `tool_version`
- `run_id`
- `started_at` / `ended_at`
- `doc_id` and `source_sha256`

---

## 8. Normalization (Canonical Internal Schema)

### 8.1 Purpose
Docling and Unstructured produce different structures.
Normalization converts each into the same internal representation so the rest of the pipeline does not branch per tool.

### 8.2 Canonical Block Model (Minimum Fields)
Each normalized manifest must contain a list of blocks:
- `block_id`
- `tool_id`
- `doc_id`
- `page_num` (nullable for non-paged inputs)
- `bbox` (nullable)
- `block_type` (paragraph, heading, table, figure, caption, ocr_text, etc.)
- `text` (nullable for figure-only)
- `asset_refs` (list)
- `order_index`

---

## 9. Content-Aware Metadata Enrichment

### 9.1 Principle
Metadata must be **content-aware** and **document-aware**, and may vary by game system (Pathfinder, Cyberpunk, etc.).

MVP1 enrichment must be deterministic (no LLM-per-chunk).

### 9.2 Enrichment Outputs
For each block/chunk, enrichment may add:
- `section_title` / `section_path`
- `content_type` (rules, statblock, flavor, table, sidebar, etc.)
- `entities` (structured tags; can be empty)
- `system_id` association for the source

### 9.3 Observed Terms (System-Specific)
Enrichment may emit observed terms:
- terms are stored in DB as observations tied to `system_id`
- feedback later adjusts ranking **within the same system only**

### 9.4 Hybrid Enrichment Algorithm (MVP1)

Enrichment combines extractor metadata with deterministic rules:

1. **Preserve tool metadata**
   - Keep tool block types, hierarchy, and coordinates in normalized manifests

2. **Apply system-specific rules**
   - Rules are stored in `/config/enrichment_rules/{system_id}.yaml`
   - Rules use deterministic pattern matching (regex + keywords)

3. **Assign section paths**
   - Prefer heading hierarchy from extractors
   - Fallback to page-based grouping if hierarchy is missing

4. **Extract entities (optional)**
   - Deterministic NER (no LLM)
   - Store results in `metadata_json.entities`

5. **System assignment**
   - Use pre-set system_id when available
   - If missing, perform deterministic detection; else leave NULL

Determinism guarantee:
- Same source + same rules version -> identical enriched output
- Record `enrichment_rules_version` in enriched manifests

---

## 10. Chunking

### 10.1 Dual Chunk Sets
Chunking runs independently for each tool dataset:
- Docling enriched manifest → `docling_chunks.jsonl`
- Unstructured enriched manifest → `unstructured_chunks.jsonl`

### 10.2 Chunk Requirements
Each chunk must include:
- `chunk_id`
- `doc_id`
- `tool_id`
- `chunk_text`
- `page_start` / `page_end` (nullable)
- `section_path` (nullable)
- `metadata_json` (json object)
- `asset_refs` (list)
- `chunk_sha256`

Chunk ID format:
- `{doc_id}::{tool_id}::{chunk_sha256[:16]}`

---

## 11. Embedding & Storage

### 11.1 Storage Target
- Postgres with pgvector

### 11.2 Text Embeddings
Every chunk is embedded unless:
- chunk text is empty
- explicit skip reason recorded

Embedding retry behavior:
- If embedding generation fails, queue the chunk for retry
- Source remains `INGESTING` until embeddings succeed
- After 3 failed attempts, set status to `ERROR`

### 11.3 Image Embeddings (Optional in MVP1)
If image retrieval is in MVP1 scope for your build:
- extracted images are embedded separately
- linked via `asset_refs`

### 11.4 Full-Text Search
Chunks must be indexed via:
- `tsvector` column
- GIN index

### 11.5 Indexing
Indexes must exist for:
- `doc_id`
- `tool_id`
- `system_id`
- `active` flag (deactivation behavior)
- vector index (HNSW preferred; IVFFLAT fallback)

---

## 12. Deactivation & Removal

### 12.1 Removal from Disk
If a source disappears from `/transfer_station/sources/`:
- governance status becomes `DEACTIVATED`
- derived records become inactive (soft deactivate)
- create admin removal request
  - recorded as a governance_events row with `event_type = REMOVAL_REQUEST`

### 12.2 Soft Deactivation Semantics
Soft deactivation means:
- records remain in DB
- retrieval filters exclude inactive records
- validation can still inspect the historic data

Deactivation must be atomic as defined in TRANSACTION_MODEL_v1.0.md.

---

## 13. Validation & Certification (Required)

### 13.1 Purpose
Validation proves the ingestion pipeline completed correctly.

### 13.2 Validator Inputs
- `doc_id`
- expected tool runs (docling + unstructured)
- DB connection
- artifact paths

### 13.3 Required Checks (MVP1)
Validator must confirm:
- governance status is consistent
- raw manifests exist for both tools
- normalized + enriched artifacts exist (if configured)
- chunk files exist for both tools
- chunk row counts in DB match expected
- embeddings exist for required chunks
- FTS populated and index exists
- vector index exists
- no orphaned rows
- deactivated sources are excluded from retrieval

### 13.4 Outputs
Validator produces:
- markdown report
- json report

Reports are stored at:
- `/transfer_station/artifacts/reports/<doc_id>/validation_<run_id>.md`

### 13.5 Certification
A document may be marked `INGESTED` only if:
- validator returns PASS
- certification record is stored in DB

---

## 14. Testing Rules (Non-Negotiable)

- All tests run inside containers
- Test data comes only from `/transfer_station/sources/` (no synthetic data generation)
- PowerShell scripts may invoke container commands but do not execute tests on host
- A cleanup script must remove all test-scoped data and artifacts to return the environment to a clean state

---

## 15. Implementation Notes (MVP1 Guidance)

### 15.1 Logging
- Structured logs with correlation IDs
- Each pipeline stage logs start/end, doc_id, tool_id, run_id

### 15.2 Idempotency
- Pipeline stages must be safe to retry
- Retries must not create duplicate chunks/embeddings

### 15.3 Determinism
- Given the same source and tool versions, pipeline should produce stable identifiers and outputs (where feasible)

---

## 16. Acceptance Criteria (Ingestion)
Ingestion is considered correct for a document when:
- Source is approved
- Both extractors ran successfully
- Artifacts exist on disk
- Chunk sets exist for both tools
- Chunks and embeddings exist in DB
- Indexes exist
- Validator PASS report exists
- Query engine can retrieve chunks for the doc when in scope

---

## 17. Failure Handling and Rollback

- Any pipeline failure before certification MUST:
  - Set governance state to `ERROR`
  - Remove all artifacts for the doc_id
  - Remove all DB rows for the doc_id
- A retry starts from a clean slate

---

## 18. Change Control
This document is versioned.
- Any change must bump the version in the filename
- Changes must be recorded in the project CHANGELOG


