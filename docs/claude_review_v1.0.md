# CLAUDE_REVIEW_v1.1

**Version:** v1.1 (Second-Pass Review)
**Review Date:** 2026-01-14
**Reviewer:** Claude Code (Architectural Review Agent)
**Scope:** All 23 specification documents in docs/
**Changes from v1.0:** Added Category D (Data Integrity), Category E (Edge Cases), Category F (API Integration)

---

## Executive Summary

This **second comprehensive architectural review** of Nexus Core MVP1 documentation builds upon the initial 47-gap analysis and identifies **significant additional issues** across three critical dimensions:

1. **Data Integrity & Consistency** - 10 critical gaps
2. **Edge Cases & Boundary Conditions** - 89 distinct edge cases
3. **API & Integration Completeness** - 10 major gaps

**Total Issues Identified: 112 gaps** (47 original + 65 new from second-pass review)

**Overall Assessment:** The documentation demonstrates a **structurally sound and well-thought-out architecture** with comprehensive governance models and clear separation of concerns. However, the initial review was thorough for architectural concerns but **missed critical data integrity, transaction semantics, and boundary condition specifications** that must be addressed before implementation.

**Key Strengths:**
- Comprehensive governance-first architecture with clear state machine definitions
- Well-defined dual extraction pipeline preserving tool independence
- Strong separation of concerns (Ingestion ≠ Retrieval ≠ Synthesis)
- Extensive requirements traceability (41 FRs, 9 NFRs)
- Clear phase-gated implementation approach

**Critical Gaps:**
- Missing tool version specifications (Docling, Unstructured, pgvector, PostgreSQL)
- Undefined state transition triggers (APPROVED → INGESTING)
- Ambiguous ownership model (sources table vs source_links table)
- JWT authentication claims structure not specified
- Chunk ID format undefined (breaks idempotency guarantees)
- Content-aware enrichment algorithm not specified

---

## Severity Classification

| Severity | Count | Original | New (Second-Pass) | Definition | Impact on MVP1 |
|----------|-------|----------|-------------------|------------|---------------|
| **CRITICAL** | 22 | 12 | 10 (Data Integrity) | Blocks implementation | Cannot start coding |
| **HIGH** | 43 | 18 | 25 (Edge Cases/API) | Required pre-testing | Cannot validate correctness |
| **MEDIUM** | 47 | 17 | 30 (Edge Cases/API) | Required pre-production | Cannot deploy safely |
| **TOTAL** | **112** | **47** | **65** | | |

**Implementation Status:** 18 critical blockers identified (8 original + 10 new data integrity issues); 4 resolved through user decisions, 14 require specification updates.

---

## Critical Issues (Implementation Blockers)

### C-001: DUPLICATE_DETECTED Status Missing from State Machine

**Location:** INGESTION_ARCHITECTURE_v1.0.md Section 4.4 vs Section 4.3

**Issue:**
- Section 4.4 references `DUPLICATE_DETECTED` as a "governance item"
- But DUPLICATE_DETECTED is NOT defined in the 8-status enum (Section 4.3)
- DATABASE_SCHEMA_v1.0.md and OPENAPI_v1.0.md also list only 8 statuses
- No defined transitions for duplicate handling

**Impact:** Duplicate detection workflow cannot be implemented; admins cannot resolve duplicate decisions.

**User Decision:** Add DUPLICATE_DETECTED as 9th governance status

**Resolution Required:**
1. **GOVERNANCE_FLOW_v1.0.md Section 4.1** - Add DUPLICATE_DETECTED to status list
2. **DATABASE_SCHEMA_v1.0.md Section 2.1** - Add to sources.status enum
3. **OPENAPI_v1.0.md** - Add to GovernanceStatus schema
4. Define state transitions:
   - `DISCOVERED → DUPLICATE_DETECTED` (when SHA-256 match found)
   - `DUPLICATE_DETECTED → PENDING_APPROVAL` (admin chooses IGNORE_DUPLICATE)
   - `DUPLICATE_DETECTED → APPROVED` (admin chooses ALLOW_SEPARATE_INSTANCE)
5. **TEST_CASES_v1.0.md** - Add T-ING-002A for duplicate state flow

---

### C-002: APPROVED → INGESTING Transition Trigger Undefined

**Location:** GOVERNANCE_FLOW_v1.0.md Section 4.2, INGESTION_VALIDATION_AGENT_PROMPT_v1.0.md

**Issue:**
- Multiple documents reference transition from APPROVED to INGESTING
- No specification of WHO/WHAT triggers this transition
- GOVERNANCE_FLOW_v1.0.md Section 6 shows "Ingestion Orchestrator" can change state, but no orchestrator is defined in ARCHITECTURE_v1.0.md Section 2.2

**Impact:** Cannot implement ingestion pipeline without knowing trigger mechanism.

**User Decision:** Job queue scheduler (separate orchestrator service)

**Resolution Required:**
1. **ARCHITECTURE_v1.0.md Section 2.2** - Add `nexus_orchestrator` container:
   ```
   - nexus_orchestrator
     - Monitors APPROVED sources (polling)
     - Enqueues ingestion jobs
     - Manages state transitions to INGESTING
   ```
2. **GOVERNANCE_FLOW_v1.0.md** - Add Section 5.5 "Orchestrator-Triggered Transitions":
   - Polling interval: 60 seconds (configurable)
   - Job queue: Priority queue (APPROVED sources ordered by approval timestamp)
   - Transition logging: governance_events with `triggered_by: orchestrator`
3. **INGESTION_DEPENDENCIES_v1.0.md** - Add orchestrator as Step 0 prerequisite
4. **OPENAPI_v1.0.md** - Add `/orchestrator/health` endpoint

---

### C-003: Tool Versions Unspecified

**Location:** All documents (INGESTION_ARCHITECTURE_v1.0.md, TEST_PLAN_v1.0.md, etc.)

**Issue:**
- Docling version not specified
- Unstructured version not specified
- pgvector extension version not specified
- PostgreSQL minimum version not specified
- Python runtime version not specified
- Container base images not specified
- ARTIFACT_CONTRACT_v1.0.md Section 5.2 requires `tool_version` field but no guidance on format

**Impact:**
- Cannot guarantee reproducible builds
- Cannot ensure extractor compatibility
- Cannot validate tool_version fields
- Risk of version-dependent extraction differences

**User Decision:** Create new TOOL_VERSIONS_v1.0.md document

**Resolution Required:**

Create **docs/planning/TOOL_VERSIONS_v1.0.md** with:

```markdown
# TOOL_VERSIONS_v1.0.md

## Core Dependencies

### Extraction Tools
- **Docling:** v1.x.x (research latest stable release)
- **Unstructured:** v0.x.x (research latest stable release)

### Database
- **PostgreSQL:** >=14.0 (required for pgvector compatibility)
- **pgvector extension:** >=0.5.0 (HNSW index support)

### Python Runtime
- **Python:** >=3.11 (Docling requirement)

### Container Base Images
- nexus_api: python:3.11-slim
- nexus_ingestion_worker: python:3.11-slim
- nexus_docling_worker: python:3.11-slim
- nexus_unstructured_worker: python:3.11-slim
- nexus_validator: python:3.11-slim
- nexus_db: postgres:14-alpine + pgvector extension
- nexus_orchestrator: python:3.11-slim

### Embedding Model
- **Model:** sentence-transformers/all-MiniLM-L6-v2
- **Dimensions:** 384
- **Provider:** HuggingFace Transformers (local, no API)

## Version Format
tool_version field format: "{name}/{semver}" (e.g., "docling/1.2.3")

## Compatibility Matrix
[Define tested combinations]

## Upgrade Policy
Tool version changes require:
- Version bump in TOOL_VERSIONS_v1.0.md
- Re-validation of existing artifacts
- Migration plan if incompatible changes
```

**Additional Updates:**
- **DATABASE_SCHEMA_v1.0.md Section 3.3** - Update embeddings table: `embedding vector(384)`
- **ARCHITECTURE_v1.0.md Section 6** - Reference embedding model selection

---

### C-004: Chunk ID Format Undefined

**Location:** INGESTION_ARCHITECTURE_v1.0.md Section 10.2, DATABASE_SCHEMA_v1.0.md Section 3.2

**Issue:**
- chunk_id is primary key but generation algorithm not specified
- Section 10.2 says chunks must include `chunk_id` and `chunk_sha256` but doesn't explain relationship
- No uniqueness constraints defined
- Violates NFR-001 (idempotency) - re-ingestion could produce different chunk_ids

**Impact:**
- Cannot implement idempotent chunking
- Risk of duplicate chunks on re-ingestion
- Cannot verify chunk_id collision across tools

**Resolution Required:**

1. **ARTIFACT_CONTRACT_v1.0.md Section 5.5** - Define chunk_id format:
   ```
   chunk_id format: {doc_id}::{tool_id}::{chunk_sha256[:16]}

   Example:
   - doc_id: sample_book__abc123def456
   - tool_id: docling
   - chunk_sha256: f3a4b2c1d5e6f7a8...
   - chunk_id: sample_book__abc123def456::docling::f3a4b2c1d5e6f7a8

   Rationale:
   - Deterministic (same content → same ID)
   - Globally unique across tools and documents
   - Human-readable for debugging
   ```

2. **DATABASE_SCHEMA_v1.0.md Section 3.2** - Add uniqueness constraint:
   ```
   UNIQUE(doc_id, tool_id, chunk_sha256)
   ```

3. **REQUIREMENTS_v1.0.md NFR-001** - Add explicit chunk_id determinism requirement

4. **TEST_CASES_v1.0.md** - Add T-ING-009A: Verify re-ingestion produces identical chunk_ids

---

### C-005: Content-Aware Enrichment Algorithm Undefined

**Location:** INGESTION_ARCHITECTURE_v1.0.md Section 9

**Issue:**
- FR-017 requires "deterministic enrichment (no LLM-per-chunk)"
- Section 9 says metadata must be "content-aware" and "document-aware"
- Section 9.2 mentions enrichment outputs (section_title, content_type, entities) but no algorithm
- Section 9 says enrichment "may vary by game system" but no specification of system-specific logic
- Circular dependency: enrichment needs system_id, but system_id may come from enrichment

**Impact:** Cannot implement enrichment; content-aware requirement contradicts determinism without specification.

**User Decision:** Hybrid approach (tool outputs + rule-based classification)

**Resolution Required:**

**INGESTION_ARCHITECTURE_v1.0.md** - Add Section 9.4 "Hybrid Enrichment Algorithm":

```markdown
## 9.4 Hybrid Enrichment Algorithm (MVP1)

Enrichment combines extractor-provided metadata with rule-based classification:

### Step 1: Extract Tool Metadata
- Docling provides: block_type (heading, paragraph, table, figure), hierarchy
- Unstructured provides: element_type, page_number, coordinates
- Both tools provide bounding boxes and structural semantics
- Preserve all tool classifications in normalized manifest

### Step 2: Apply System-Specific Rules
For each normalized block:
- Match content patterns against system-specific ruleset
- Rules stored in: `/config/enrichment_rules/{system_id}.yaml`
- Pattern matching uses regex + keyword detection (deterministic)

**Example Pathfinder Rules:**
```yaml
system_id: pathfinder
rules:
  - pattern: "AC \\d+, HP \\d+"
    content_type: statblock
  - pattern: "^#+\\s*(Chapter|Section)"
    content_type: section_header
  - pattern: "Table \\d+\\-\\d+"
    content_type: rules_table
  - pattern: "^(Spell|Feat|Item):"
    content_type: game_mechanic
```

### Step 3: Assign Section Path
- Use heading hierarchy from Docling to construct section_path
- Format: "Chapter 3 / Combat Rules / Initiative"
- Fallback: Use page_number if hierarchy unavailable
- Section path enables context-aware retrieval

### Step 4: Extract Entities (Optional)
- Named entity recognition via spaCy (deterministic, rule-based)
- Entity types: character_name, location, item, spell, monster
- Store in metadata_json.entities array
- No LLM required; uses pre-trained NER model

### Step 5: System ID Assignment
- If system_id not set during approval, attempt auto-detection:
  - Match document title/content against known system patterns
  - Fallback: system_id = NULL (use generic enrichment rules)
- Admin can override system_id via approval workflow

### Determinism Guarantee
- Same source + same enrichment_rules version → identical metadata
- Enrichment version tracked in manifest provenance
- Rules are versioned: `enrichment_rules_version: "1.0"`
- Re-ingestion with same rules produces identical enriched manifests
```

**Additional Updates:**
1. **ARTIFACT_CONTRACT_v1.0.md** - Add enrichment_rules config directory to artifact structure
2. **ARTIFACT_CONTRACT_v1.0.md Section 5.4** - Add enrichment_version field requirement
3. **TEST_CASES_v1.0.md** - Add T-ING-008A: Verify deterministic enrichment across re-runs

---

### C-006: JWT Claims Structure Undefined

**Location:** OPENAPI_v1.0.md Section security

**Issue:**
- Section defines `bearerAuth` with `bearerFormat: JWT` but no claims specification
- No definition of how role (PLAYER, GM, ADMIN) is extracted from token
- No specification of how active_game_id is communicated
- REQUIREMENTS_v1.0.md NFR-005 requires "server-side role checks" but no implementation spec
- ACCESS_MATRIX_v1.0.md assumes roles exist but doesn't define token structure

**Impact:**
- Cannot implement authentication
- Cannot enforce role-based access control
- Security vulnerability (client could forge role claims without spec)

**Resolution Required:**

Create **docs/api/JWT_SPEC_v1.0.md**:

```markdown
# JWT_SPEC_v1.0.md

**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** OPENAPI_v1.0.md

## Token Structure

### Standard Claims (RFC 7519)
- `iss` (issuer): "nexus-core-api"
- `sub` (subject): user_id (UUID string)
- `exp` (expiration): Unix timestamp
- `iat` (issued at): Unix timestamp
- `jti` (JWT ID): Unique token identifier (for revocation)

### Custom Claims
- `role`: "PLAYER" | "GM" | "ADMIN" (string, REQUIRED)
- `active_game_id`: game_id (UUID string, nullable)
- `games_owned`: [game_id] (array of UUIDs, for GMs only)
- `tier`: "FREE" | "BASIC" | "PRO" (string, for limit enforcement)

### Example Token Payload
```json
{
  "iss": "nexus-core-api",
  "sub": "user-uuid-123",
  "role": "GM",
  "active_game_id": "game-uuid-456",
  "games_owned": ["game-uuid-456", "game-uuid-789"],
  "tier": "PRO",
  "exp": 1704067200,
  "iat": 1704063600,
  "jti": "token-uuid-abc"
}
```

## Validation Rules

### Server-Side Enforcement
1. **All endpoints MUST validate JWT signature** (RS256 algorithm)
2. **All endpoints MUST validate exp claim** (reject expired tokens)
3. **All endpoints MUST extract role claim** (no default; reject if missing)
4. **Admin-only endpoints MUST return 403** if role != "ADMIN"
5. **Game-scoped endpoints MUST validate active_game_id**:
   - If endpoint requires game context and active_game_id is null: return 400
   - If role is GM, validate active_game_id is in games_owned: return 403 if not

### Token Refresh
- Refresh token flow deferred to post-MVP1
- MVP1 tokens expire after 24 hours (configurable)
- Client must re-authenticate on expiration

## Security Requirements
- Private key for signing MUST be stored in environment variable (not committed)
- Public key for validation MUST be accessible to all services
- Tokens transmitted only via Authorization: Bearer header (HTTPS required)

## Change Control
This document is versioned. Changes require:
- Version bump
- Update to OPENAPI_v1.0.md security section
- Re-validation of all auth tests
```

**Additional Updates:**
1. **OPENAPI_v1.0.md** - Add reference to JWT_SPEC_v1.0.md in security section
2. **REQUIREMENTS_v1.0.md NFR-005** - Reference JWT validation requirements
3. **TEST_CASES_v1.0.md** - Add T-SEC-001: Verify role-based endpoint access

---

### C-007: Source Ownership Model Ambiguous

**Location:** DATABASE_SCHEMA_v1.0.md Sections 2.1 vs 6.1

**Issue:**
- Ownership defined in TWO places:
  - `sources` table has: owner_user_id, game_id (nullable)
  - `source_links` table has: scope_type, owner_user_id, game_id, gm_only
- No specification of precedence or relationship
- OPENAPI_v1.0.md has no endpoints to manage source_links
- UI_WIREFRAME_SPEC_v1.0.md Section 6.3 says GM can "Link/unlink GM sources" but no API exists

**Impact:**
- Cannot implement ownership checks
- Ambiguous query scope enforcement
- Risk of security bypass

**User Decision:** Use sources table only (primary ownership)

**Resolution Required:**

1. **DATABASE_SCHEMA_v1.0.md Section 2.1** - Clarify sources table:
   ```
   owner_user_id (text, NOT NULL) - User who owns this source
   game_id (text, nullable) - Game this source is linked to (if any)

   Ownership Rules:
   - owner_user_id is set during approval (admin who approved becomes owner)
   - game_id is set when source is linked to a game (via Admin UI)
   - Sources can be owned by user (game_id = NULL) or game (game_id set)
   ```

2. **DATABASE_SCHEMA_v1.0.md Section 6.1** - Clarify source_links purpose:
   ```
   source_links table is for ADDITIONAL access grants only:
   - Allows sharing sources across multiple games
   - Allows temporary access grants to other users
   - Primary ownership is ALWAYS in sources.owner_user_id

   Query Logic:
   - User can access source if:
     - sources.owner_user_id = user_id, OR
     - source_links exists WHERE owner_user_id = user_id
   ```

3. **REQUIREMENTS_v1.0.md FR-032, FR-033** - Update to reference primary ownership model

4. **OPENAPI_v1.0.md** - Add endpoints (MEDIUM priority):
   ```
   POST /sources/{doc_id}/link - Create source_link
   DELETE /sources/{doc_id}/link/{link_id} - Remove source_link
   GET /sources/{doc_id}/links - List all links for a source
   ```

---

### C-008: Removal Request Workflow Missing

**Location:** INGESTION_ARCHITECTURE_v1.0.md Sections 5.3, 12.1

**Issue:**
- Section 5.3 states: "create an **admin removal request** record for audit/review"
- Section 12.1 mentions "create admin removal request"
- But no database table for removal_requests
- No API endpoints to list/view/act on removal requests
- Admins have no way to see that a source was removed from disk

**Impact:** Cannot implement removal detection audit trail.

**User Decision:** Use governance_events table (no new table needed)

**Resolution Required:**

1. **GOVERNANCE_FLOW_v1.0.md Section 7** - Add event type:
   ```
   Event Types:
   - STATUS_CHANGE: Normal state transitions
   - REMOVAL_REQUEST: Source file removed from disk (detected by orchestrator)

   REMOVAL_REQUEST event structure:
   {
     "event_type": "REMOVAL_REQUEST",
     "doc_id": "sample_book__abc123",
     "from_status": "INGESTED",
     "to_status": "DEACTIVATED",
     "triggered_by": "nexus_orchestrator",
     "triggered_at": "2026-01-14T10:00:00Z",
     "metadata_json": {
       "removed_at": "2026-01-14T09:58:32Z",
       "detected_by": "file_monitor",
       "detection_method": "polling"
     }
   }
   ```

2. **DATABASE_SCHEMA_v1.0.md Section 2.2** - Add event_type field:
   ```
   governance_events table:
   - event_type (text, enum: STATUS_CHANGE, REMOVAL_REQUEST)
   ```

3. **OPENAPI_v1.0.md** - Add filter parameter to governance events endpoint:
   ```
   GET /governance/events?event_type=REMOVAL_REQUEST
   ```

4. **Admin UI** - Add filter to show removal requests (implementation detail, not spec)

---

### C-009: Deactivation Trigger Mechanism Unspecified

**Location:** GOVERNANCE_FLOW_v1.0.md Section 4.4, TEST_CASES_v1.0.md T-ING-014

**Issue:**
- Section 4.4 states deactivation occurs "when source removed from disk"
- But no specification of HOW removal is detected:
  - File system watcher?
  - Polling?
  - Manual admin action?
- TEST_CASES_v1.0.md T-ING-014 says "Remove source file from `/transfer_station/sources/`" but no timing assertion
- No specification of detection latency tolerance

**Impact:** Cannot implement or test deactivation.

**Resolution Required:**

1. **GOVERNANCE_FLOW_v1.0.md Section 4.4** - Specify detection mechanism:
   ```
   ## Deactivation Detection

   Component: nexus_orchestrator (same service that triggers INGESTING)

   Mechanism: Polling
   - Poll interval: 60 seconds (configurable via ORCHESTRATOR_POLL_INTERVAL)
   - Scans sources table WHERE status IN ('INGESTED', 'ERROR', 'INGESTING')
   - For each source, checks if file exists at current_path
   - If file missing: transition to DEACTIVATED + create REMOVAL_REQUEST event

   Latency Tolerance: Detection within 120 seconds of file removal

   Edge Cases:
   - File renamed: Treated as removal (deactivated)
   - File moved to quarantine/: No deactivation (still present in transfer_station)
   - File temporarily unavailable (network): No deactivation on first poll; retry 3 times
   ```

2. **TEST_CASES_v1.0.md T-ING-014** - Update test case:
   ```
   T-ING-014: Source Removal Deactivation

   Steps:
   1. Ingest source to INGESTED state
   2. Remove source file from /transfer_station/sources/
   3. Wait up to 120 seconds
   4. Verify governance status = DEACTIVATED
   5. Verify governance_events has REMOVAL_REQUEST entry
   6. Verify chunks are excluded from retrieval (active = false)

   Assertions:
   - Deactivation detected within 120 seconds
   - Artifacts remain on disk (not deleted)
   - DB records soft-deactivated (active = false)
   ```

---

### C-010: Missing DENIED → PENDING_APPROVAL Transition

**Location:** GOVERNANCE_FLOW_v1.0.md Section 4.1

**Issue:**
- State machine shows PENDING_APPROVAL can transition to DENIED
- But no reverse transition if admin changes mind
- Creates orphaned DENIED records with no recovery path
- User experience gap

**Impact:** Admins cannot correct denial mistakes; sources must be re-discovered.

**Resolution Required:**

1. **GOVERNANCE_FLOW_v1.0.md Section 4.1** - Add optional transition:
   ```
   Optional Transitions (Admin Override):
   - DENIED → PENDING_APPROVAL
     - Trigger: Admin override action
     - Requires: override_reason (text)
     - Logged in governance_events with metadata.override_reason
   ```

2. **OPENAPI_v1.0.md** - Add endpoint:
   ```
   POST /governance/sources/{doc_id}/override-denial
   Body: { "reason": "Denial was in error; re-reviewing" }
   Response: 200 (state transitions to PENDING_APPROVAL)
   ```

3. **TEST_CASES_v1.0.md** - Add T-GOV-005: Denial reversal test

---

### C-011: Admin Audit-Only Enforcement Missing

**Location:** ACCESS_MATRIX_v1.0.md Section 4

**Issue:**
- Section 4 states "ADMIN: All sources (audit only)"
- But "audit only" is not defined or enforced
- No specification of what admins CAN vs CANNOT do
- Risk: Admin could run synthesis queries on private user sources

**Impact:** Security vulnerability; admin privilege scope undefined.

**Resolution Required:**

1. **ACCESS_MATRIX_v1.0.md Section 4** - Define audit scope:
   ```
   ## Admin Permissions (Audit Only)

   Admins CAN:
   - View governance status for all sources
   - Read raw/normalized/enriched manifests
   - Inspect validation reports
   - List chunks and embeddings (read-only)
   - View governance_events and feedback
   - Approve/deny/retry sources

   Admins CANNOT:
   - Execute synthesis queries on user sources
   - Modify chunk data or rankings
   - Submit feedback as user
   - Access user JWT tokens
   - Impersonate users
   ```

2. **OPENAPI_v1.0.md** - Add admin audit endpoint:
   ```
   GET /admin/audit/{doc_id}
   Response: {
     governance_status: ...,
     manifests: [...],
     validation_reports: [...],
     chunks_count: N,
     embeddings_count: N
   }
   (Read-only inspection; does NOT run queries)
   ```

3. **TEST_CASES_v1.0.md** - Add T-SEC-002: Verify admin cannot execute user queries

---

### C-012: GM-Only Source Scope Bypass Risk

**Location:** ACCESS_MATRIX_v1.0.md Section 6, QUERY_POLICY_v1.0.md

**Issue:**
- Section 6 says "source linked to game is visible only within that game context"
- But QUERY_POLICY_v1.0.md doesn't validate direct doc_id queries
- Risk: Player could query by explicit doc_id to bypass game context

**Impact:** Security vulnerability; scope enforcement bypass.

**Resolution Required:**

1. **QUERY_POLICY_v1.0.md Section 3** - Add pre-query validation:
   ```
   ## Pre-Query Scope Validation

   Before executing any query:
   1. Extract doc_id references from query_text (if any)
   2. For each doc_id:
      - Query sources WHERE doc_id = X
      - Check if user has access:
        - IF game_id is set AND user.active_game_id != sources.game_id: REJECT (403)
        - IF gm_only = true AND user.role != GM: REJECT (403)
        - IF owner_user_id != user.id AND no source_link exists: REJECT (403)
   3. If any doc_id check fails, reject entire query with 403 Forbidden
   ```

2. **TEST_CASES_v1.0.md** - Add T-SEC-003: Player query with GM-only doc_id returns 403

---

## Category D: Data Integrity & Consistency Issues (Second-Pass Review)

**These 10 critical gaps represent the highest risk for data corruption and silent failures.**

### D-001: CASCADE DELETE/DEACTIVATE RULES MISSING (CRITICAL)

**Location:** DATABASE_SCHEMA_v1.0.md, GOVERNANCE_FLOW_v1.0.md

**Issue:**
- No ON DELETE behavior specified for any foreign keys
- Risk of orphaned chunks, embeddings, FTS indexes when sources deactivated
- Database referential integrity undefined

**Impact:** Data corruption through orphaned records; incomplete deactivation.

**Resolution Required:**

Create **docs/database/DATABASE_CONSTRAINTS_v1.0.md**:

```markdown
# DATABASE_CONSTRAINTS_v1.0.md

## Foreign Key Cascade Rules

### sources → chunks
ON DELETE: RESTRICT (prevent source deletion if chunks exist)
ON UPDATE: CASCADE (doc_id updates propagate)

### chunks → embeddings
ON DELETE: CASCADE (delete embeddings when chunk deleted)
ON UPDATE: CASCADE (chunk_id updates propagate)

### chunks → fts_index
ON DELETE: CASCADE (remove FTS entries when chunk deleted)
ON UPDATE: CASCADE (chunk_id updates propagate)

### Deactivation Behavior
- Deactivation is NOT deletion (soft delete via active = false)
- When source.active = false:
  - SET chunks.active = false (UPDATE, not DELETE)
  - SET embeddings.active = false
  - No CASCADE DELETE triggered
```

**Additional Updates:**
- **DATABASE_SCHEMA_v1.0.md** - Add explicit ON DELETE/ON UPDATE clauses to all FK definitions
- **GOVERNANCE_FLOW_v1.0.md** - Document cascade behavior in deactivation section
- **TEST_CASES_v1.0.md** - Add T-INT-001: Verify orphan prevention

---

### D-002: TRANSACTION BOUNDARIES UNDEFINED (CRITICAL)

**Location:** All documents - completely missing

**Issue:**
- No specification of transaction scope for multi-step operations
- Ingestion involves: status update + manifest write + chunk insert + embedding generation
- Partial failures leave database in inconsistent state
- No guidance on transaction isolation levels

**Impact:** Data corruption during failures; cannot guarantee atomicity.

**Resolution Required:**

Create **docs/database/TRANSACTION_MODEL_v1.0.md**:

```markdown
# TRANSACTION_MODEL_v1.0.md

## Atomic Operations

### Ingestion Transaction Scope
```
BEGIN TRANSACTION (SERIALIZABLE)
  1. UPDATE sources SET status = 'INGESTING'
  2. Write manifest artifacts to disk
  3. INSERT INTO chunks (batch)
  4. INSERT INTO embeddings (batch)
  5. INSERT INTO fts_index (batch)
  6. UPDATE sources SET status = 'INGESTED'
COMMIT / ROLLBACK
```

On ROLLBACK:
- Delete all partial artifacts from disk
- Revert source status to APPROVED
- Log error in governance_events

### Deactivation Transaction Scope
```
BEGIN TRANSACTION (SERIALIZABLE)
  1. UPDATE sources SET status = 'DEACTIVATED', active = false
  2. UPDATE chunks SET active = false WHERE doc_id = X
  3. UPDATE embeddings SET active = false WHERE doc_id = X
  4. INSERT INTO governance_events (REMOVAL_REQUEST)
COMMIT / ROLLBACK
```

### Isolation Level: SERIALIZABLE
- Prevents concurrent modifications during multi-step operations
- Performance impact acceptable for MVP1 ingestion volume
```

**Additional Updates:**
- **INGESTION_ARCHITECTURE_v1.0.md** - Reference transaction boundaries in each pipeline stage
- **TEST_CASES_v1.0.md** - Add T-INT-002: Verify rollback on partial failure

---

### D-003: CONCURRENT MODIFICATION CONFLICTS (CRITICAL)

**Location:** GOVERNANCE_FLOW_v1.0.md (partial coverage via optimistic locking)

**Issue:**
- Section 7 mentions optimistic locking via state_version but no implementation spec
- Race conditions on simultaneous admin approvals not handled
- Multiple admins could approve same source → duplicate ingestion jobs
- No mutex/lock mechanism specified

**Impact:** Duplicate ingestion jobs; wasted resources; data inconsistency.

**Resolution Required:**

Create **docs/database/CONCURRENCY_MODEL_v1.0.md**:

```markdown
# CONCURRENCY_MODEL_v1.0.md

## Optimistic Locking Implementation

### State Transition Pattern
```sql
UPDATE sources
SET status = 'APPROVED', state_version = state_version + 1
WHERE doc_id = X AND state_version = Y
RETURNING state_version;
```

If affected_rows = 0:
- Another process modified the record
- Return 409 Conflict
- Client must refresh and retry

### Admin Approval Race Condition
Scenario: Admin A and Admin B both click "Approve" on same source

Resolution:
1. Both submit POST /governance/sources/{doc_id}/approve
2. First request wins (state_version incremented)
3. Second request fails (state_version mismatch)
4. API returns 409 Conflict: "Source already approved by another admin"

### Orchestrator Polling Lock
When orchestrator detects APPROVED source:
1. Optimistically lock: UPDATE status = 'INGESTING' WHERE status = 'APPROVED' AND state_version = Y
2. If affected_rows = 0: another orchestrator already claimed it
3. If affected_rows = 1: proceed with ingestion
```

**Additional Updates:**
- **GOVERNANCE_FLOW_v1.0.md Section 7** - Expand optimistic locking specification
- **OPENAPI_v1.0.md** - Add 409 Conflict responses to state transition endpoints
- **TEST_CASES_v1.0.md** - Add T-CON-001: Concurrent approval collision test

---

### D-004: DATA MIGRATION STRATEGY MISSING (HIGH)

**Location:** All documents - not addressed

**Issue:**
- No schema evolution procedures
- Cannot safely upgrade Docling/Unstructured versions mid-MVP1
- No guidance on backward compatibility

**Impact:** Cannot upgrade tools or schema without data loss risk.

**Resolution Required:**

Create **docs/database/DATABASE_MIGRATION_v1.0.md**:

```markdown
# DATABASE_MIGRATION_v1.0.md

## Schema Evolution

### Migration Tool: Alembic (Python)
- Migrations stored in: /migrations/versions/
- Applied via: docker exec nexus_api alembic upgrade head

### Tool Version Upgrades
When upgrading Docling or Unstructured:
1. Update TOOL_VERSIONS_v1.0.md
2. Mark all existing sources WHERE tool_version != NEW as "requires_reingestion"
3. Admin reviews and approves re-ingestion
4. Re-ingestion creates NEW chunks (old chunks soft-deleted)

### Backward Compatibility
- Database schema changes MUST be backward compatible for 1 version
- Example: Adding column → default value required
- Breaking changes → new major version + migration path
```

**Additional Updates:**
- **DEPLOYMENT_v1.0.md** - Add migration procedures to startup sequence
- **TOOL_VERSIONS_v1.0.md** - Add upgrade policy reference

---

### D-005: BACKUP AND RECOVERY ABSENT (HIGH)

**Location:** All documents - not addressed

**Issue:**
- No backup procedures
- No RPO/RTO specifications
- No disaster recovery plan

**Impact:** Data loss scenarios unrecoverable.

**Resolution Required:**

Create **docs/operations/BACKUP_AND_RECOVERY_v1.0.md**:

```markdown
# BACKUP_AND_RECOVERY_v1.0.md

## Backup Strategy

### Database Backups
- Frequency: Daily at 2:00 AM UTC
- Tool: pg_dump (full backup)
- Retention: 7 daily, 4 weekly, 3 monthly
- Location: E:\Backups\nexus_db\ (host mount)

### Artifact Backups
- Frequency: Daily at 3:00 AM UTC
- Tool: Robocopy (incremental)
- Scope: /transfer_station/artifacts/
- Retention: 7 daily

### Recovery Time Objective (RTO)
- Target: < 4 hours (complete system restore)

### Recovery Point Objective (RPO)
- Target: < 24 hours (maximum data loss tolerance)

## Disaster Recovery Procedures
[Define restore procedures, failover scenarios]
```

**Additional Updates:**
- **DEPLOYMENT_v1.0.md** - Add backup service to docker-compose

---

### D-006: DATA RETENTION POLICIES INCOMPLETE (HIGH)

**Location:** CLEANUP_STRATEGY_v1.0.md (minimal)

**Issue:**
- No retention schedules for deactivated sources
- No TTL for validation reports
- Uncontrolled disk growth

**Impact:** Disk exhaustion; performance degradation.

**Resolution Required:**

Expand **CLEANUP_STRATEGY_v1.0.md** with retention policies:

```markdown
## Retention Policies

### Deactivated Sources
- Artifacts retained: 30 days after deactivation
- Database records retained: 90 days (soft delete)
- After 90 days: Hard delete (admin approval required)

### Validation Reports
- PASS reports: 7 days
- FAIL reports: 90 days (for debugging)

### Governance Events
- All events: Retain indefinitely (audit trail)

### Embeddings Cache
- Inactive embeddings: Delete after 30 days
```

---

### D-007: AUDIT TRAIL SCOPE GAPS (HIGH)

**Location:** GOVERNANCE_FLOW_v1.0.md Section 8

**Issue:**
- Only governance events audited
- Chunk/embedding changes not tracked
- Cannot reconstruct data lineage for non-governance operations

**Impact:** Limited forensic capabilities; compliance risk.

**Resolution Required:**

Expand **GOVERNANCE_FLOW_v1.0.md Section 8**:

```markdown
## Extended Audit Event Types

- STATUS_CHANGE (existing)
- REMOVAL_REQUEST (existing)
- CHUNK_CREATED (new)
- CHUNK_DELETED (new)
- EMBEDDING_GENERATED (new)
- VALIDATION_RUN (new)
- QUERY_EXECUTED (new - privacy implications, defer to post-MVP1)
```

---

### D-008: ORPHAN PREVENTION UNSPECIFIED (CRITICAL)

**Location:** DATABASE_SCHEMA_v1.0.md

**Issue:**
- No constraints prevent chunk creation without source validation
- Embeddings could reference non-existent chunks
- Database integrity violations possible

**Impact:** Data corruption through orphaned records.

**Resolution Required:**

**DATABASE_SCHEMA_v1.0.md** - Add referential integrity constraints:

```sql
-- Prevent chunk creation for non-existent sources
ALTER TABLE chunks ADD CONSTRAINT fk_chunks_sources
  FOREIGN KEY (doc_id) REFERENCES sources(doc_id)
  ON DELETE RESTRICT ON UPDATE CASCADE;

-- Prevent embeddings for non-existent chunks
ALTER TABLE embeddings ADD CONSTRAINT fk_embeddings_chunks
  FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
  ON DELETE CASCADE ON UPDATE CASCADE;

-- Prevent FTS entries for non-existent chunks
ALTER TABLE fts_index ADD CONSTRAINT fk_fts_chunks
  FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
  ON DELETE CASCADE ON UPDATE CASCADE;
```

**Additional Updates:**
- **TEST_CASES_v1.0.md** - Add T-INT-003: Verify FK constraint enforcement

---

### D-009: DEACTIVATION ATOMICITY MISSING (CRITICAL)

**Location:** INGESTION_ARCHITECTURE_v1.0.md Section 12

**Issue:**
- Multi-step deactivation (status + chunks + removal request) not atomic
- Partial deactivation leaves inconsistent state
- If status update succeeds but chunk update fails → data corruption

**Impact:** Inconsistent deactivation state; orphaned data.

**Resolution Required:**

Reference TRANSACTION_MODEL_v1.0.md (D-002 above) for deactivation transaction scope.

**Additional Updates:**
- **INGESTION_ARCHITECTURE_v1.0.md Section 12** - Reference transaction model
- **TEST_CASES_v1.0.md** - Add T-INT-004: Verify atomic deactivation

---

### D-010: CONCURRENT REMOVAL DETECTION RACE (MEDIUM)

**Location:** INGESTION_ARCHITECTURE_v1.0.md Section 5.3

**Issue:**
- File removed then re-added within poll interval (60s) creates ambiguity
- Deactivation may not trigger correctly
- Edge case not documented

**Impact:** Missed deactivation; stale data.

**Resolution Required:**

**GOVERNANCE_FLOW_v1.0.md Section 4.4** - Add edge case documentation:

```markdown
## Poll Window Edge Cases

### File Removed and Re-added
Scenario: File removed at T+0, re-added at T+30 (within 60s poll interval)

Behavior:
- Poll at T+60 detects file present
- No deactivation triggered
- File treated as continuous presence

Admin Guidance:
- If intentional re-add: No action needed
- If unintentional: Manually deactivate then re-approve
```

---

## Category E: Edge Cases & Boundary Conditions (Second-Pass Review)

**These 89 missing specifications represent untested boundary conditions that could cause runtime failures.**

### E-001 through E-089: Edge Case Catalog

Due to length constraints, edge cases are organized by subcategory. Full details available in plan file (peaceful-questing-platypus.md).

#### E-001 to E-009: Empty/Null Handling (MEDIUM to HIGH)
- Zero chunks from extraction
- Empty chunk_text storage
- Null section_path, content_type, system_tag
- Missing asset_refs
- Failed embeddings (retry limit?)
- Null game_id for user-owned sources
- Empty enrichment_rules file
- Null owner_user_id at approval time
- Empty validation reports

**Resolution:** Create **docs/requirements/EDGE_CASES_v1.0.md** with comprehensive catalog and handling specifications.

#### E-010 to E-016: Size Limits (CRITICAL)
- Maximum source file size undefined (could crash extractors)
- Maximum chunks per document undefined (DB exhaustion risk)
- Maximum chunk text length undefined (embedding model limits)
- Transfer Station disk quota undefined (disk full scenarios)
- Maximum doc_id length collision risk
- Maximum manifest file size
- Maximum concurrent ingestion jobs

**Resolution:** Create **docs/requirements/RESOURCE_LIMITS_v1.0.md**:

```markdown
# RESOURCE_LIMITS_v1.0.md

## File Size Limits
- Maximum source file: 100 MB (enforced at discovery)
- Maximum manifest file: 10 MB
- Maximum chunk text: 8,000 characters (embedding model limit)

## Database Limits
- Maximum chunks per document: 10,000
- Maximum embeddings per document: 10,000
- Maximum FTS entries per document: 10,000

## Concurrency Limits
- Maximum concurrent ingestion jobs: 3
- Maximum concurrent validation runs: 2

## Storage Quotas
- Transfer Station total: 50 GB (configurable)
- Artifacts per source: 500 MB (enforced at ingestion)
```

#### E-017 to E-023: Special Characters (MEDIUM)
- Unicode, emoji, RTL text in filenames
- Path separators in doc_id sanitization
- Control characters in chunk_text
- SQL injection via unescaped section_title in FTS
- YAML injection in enrichment_rules
- JSON injection in manifests
- Regex injection in query patterns

**Resolution:** Expand **INGESTION_ARCHITECTURE_v1.0.md Section 3.1** with sanitization rules.

#### E-024 to E-029: Timezone Handling (MEDIUM)
- Timestamp storage (UTC vs local)
- Clock skew affecting deactivation latency
- Poll interval jitter tolerance
- Daylight saving time transitions
- Timestamp comparison edge cases
- Event ordering across timezones

**Resolution:** **DATABASE_SCHEMA_v1.0.md** - Specify all timestamps as `TIMESTAMP WITH TIME ZONE`, stored in UTC.

#### E-030 to E-035: Rate Limiting (HIGH)
- Max concurrent ingestion jobs (undefined)
- Embedding throughput limits (undefined)
- Query rate limiting (absent from API spec)
- Admin approval throughput
- Validation run frequency
- Governance event write rate

**Resolution:** Add to **RESOURCE_LIMITS_v1.0.md** and **OPENAPI_v1.0.md** (rate limit headers).

#### E-036 to E-041: Resource Exhaustion (CRITICAL)
- Disk full during manifest writing
- Memory exhaustion during embedding (OOM)
- DB connection pool exhausted
- pgvector index corruption
- Worker process crash
- Orchestrator unavailability

**Resolution:** Create **docs/requirements/FAULT_RECOVERY_v1.0.md**:

```markdown
# FAULT_RECOVERY_v1.0.md

## Resource Exhaustion Handling

### Disk Full
- Detection: Monitor Transfer Station disk usage
- Threshold: Alert at 80%, block ingestion at 90%
- Recovery: Admin notification, manual cleanup, resume

### OOM During Embedding
- Detection: Worker process crash
- Recovery: Automatic retry with reduced batch size
- Limit: 3 retries, then ERROR status

### DB Connection Pool Exhausted
- Pool size: 20 connections (configurable)
- Timeout: 30 seconds
- Fallback: Queue request, return 503 Service Unavailable

### Retry Policies
- Network failures: Exponential backoff (1s, 2s, 4s, max 3 retries)
- Worker crashes: Immediate restart (max 3 restarts/5min)
- Validation failures: No automatic retry (admin action required)
```

#### E-042 to E-047: Network Failures (HIGH)
- Transfer Station network disconnect
- DB connection loss mid-ingestion
- Worker crash during extraction
- Retry policies completely undefined
- Connection timeout handling
- Partial data transmission

**Resolution:** Reference **FAULT_RECOVERY_v1.0.md** above.

#### E-048 to E-054: Malformed Input (HIGH)
- Corrupted PDF handling
- Invalid JSON in manifests
- Truncated JSONL chunk files
- Path traversal in sanitized doc_id
- Malicious file upload
- ZIP bombs
- Infinite recursion in nested structures

**Resolution:** Add validation checks to **INGESTION_ARCHITECTURE_v1.0.md** extraction stages.

#### E-055 to E-060: Extreme Values (MEDIUM)
- 1-page document
- 10,000-page document
- 1-word chunk vs 1M-character chunk
- Single chunk document
- Document with no extractable text
- Document with only images

**Resolution:** Add to **EDGE_CASES_v1.0.md** with expected behaviors.

#### E-061 to E-066: Illegal States (CRITICAL)
- INGESTING + DEACTIVATED simultaneously
- state_version mismatch handling
- Orphaned embeddings without chunks
- Active chunks with deactivated source
- INGESTED with zero chunks
- APPROVED with no file on disk

**Resolution:** Add state validation checks to **CONCURRENCY_MODEL_v1.0.md**.

#### E-067 to E-071: Deactivation Edge Cases (MEDIUM)
- Deactivation during validation run
- Re-adding same file after deactivation
- Deactivation during embedding generation
- Multiple deactivation requests
- Deactivation of non-existent source

**Resolution:** Add to **GOVERNANCE_FLOW_v1.0.md Section 4.4**.

#### E-072 to E-076: Testing Gaps (HIGH)
- Test isolation between runs
- Cleanup failure handling
- Tool version variance
- Test data corruption
- Parallel test execution conflicts

**Resolution:** Expand **TEST_PLAN_v1.0.md Section 2.3** with isolation procedures.

#### E-077 to E-089: Concurrency Hazards (CRITICAL)
- Simultaneous admin approvals (covered in D-003)
- Status change during validation
- Query + embedding generation race
- Multiple orchestrators polling
- Concurrent chunk insertions
- Parallel validation runs on same source
- Admin override during ingestion
- Deactivation during chunk storage
- Re-approval during ERROR state
- Concurrent feedback submissions
- Parallel manifest writes
- Multiple removal detections
- Simultaneous re-ingestion requests

**Resolution:** Reference **CONCURRENCY_MODEL_v1.0.md** (D-003).

---

## Category F: API & Integration Gaps (Second-Pass Review)

**These 10 major areas represent missing API capabilities that limit system usability.**

### F-001: CRUD Update Operations Missing (HIGH)

**Issue:**
- Cannot update source metadata post-creation
- No PATCH endpoint for system_id, game_id, owner_user_id
- Cannot bulk-reassign sources to different games
- Admin must delete and recreate to change metadata

**Impact:** Poor admin UX; cannot fix metadata errors without re-ingestion.

**Resolution Required:**

Add to **OPENAPI_v1.0.md**:

```yaml
/sources/{doc_id}:
  patch:
    summary: Update source metadata
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              system_id:
                type: string
              game_id:
                type: string
              owner_user_id:
                type: string
    responses:
      200:
        description: Metadata updated
      409:
        description: Cannot update source in INGESTING state
```

**Additional Updates:**
- **TEST_CASES_v1.0.md** - Add T-API-001: PATCH metadata update test

---

### F-002: Webhook/Event Streaming Absent (HIGH)

**Issue:**
- No async notifications for governance state changes
- Admin UI must poll for ingestion status
- No event subscription model
- Poor UX for long-running operations

**Impact:** Inefficient polling; delayed notifications; poor real-time UX.

**Resolution Required:**

Add to **OPENAPI_v1.0.md**:

```yaml
/events/stream:
  get:
    summary: Server-Sent Events stream for governance state changes
    responses:
      200:
        description: SSE stream
        content:
          text/event-stream:
            schema:
              type: object
              properties:
                event:
                  type: string
                  enum: [status_change, removal_request, validation_complete]
                data:
                  type: object
```

**Additional Updates:**
- **ARCHITECTURE_v1.0.md** - Add SSE capability to nexus_api

---

### F-003: Bulk Operations Missing (MEDIUM)

**Issue:**
- Approve/deny/retry are single-entity only
- Cannot batch-approve 50 sources at once
- Admin must click 50 times for bulk operations

**Impact:** Poor admin UX; inefficient workflow.

**Resolution Required:**

Add to **OPENAPI_v1.0.md**:

```yaml
/governance/sources/bulk-approve:
  post:
    summary: Approve multiple sources
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              doc_ids:
                type: array
                items:
                  type: string
    responses:
      200:
        description: Bulk operation results
        content:
          application/json:
            schema:
              type: object
              properties:
                succeeded:
                  type: array
                  items:
                    type: string
                failed:
                  type: array
                  items:
                    type: object
                    properties:
                      doc_id:
                        type: string
                      reason:
                        type: string
```

---

### F-004: Search & Filtering Limited (MEDIUM)

**Issue:**
- No full-text search on filenames
- No date-range filtering
- No faceted search responses
- Cannot filter by system_id, game_id, owner_user_id

**Impact:** Poor discoverability; cannot find sources efficiently.

**Resolution Required:**

Add query parameters to **OPENAPI_v1.0.md** `/sources` endpoint:

```yaml
/sources:
  get:
    parameters:
      - name: search
        in: query
        description: Full-text search on filename
      - name: system_id
        in: query
      - name: game_id
        in: query
      - name: status
        in: query
      - name: created_after
        in: query
        schema:
          type: string
          format: date-time
      - name: created_before
        in: query
        schema:
          type: string
          format: date-time
```

---

### F-005: Export Capabilities Absent (MEDIUM)

**Issue:**
- Cannot export source manifests
- Cannot bulk-download validation reports
- No data portability

**Impact:** Vendor lock-in; cannot migrate data.

**Resolution Required:**

Add to **OPENAPI_v1.0.md**:

```yaml
/sources/{doc_id}/export:
  get:
    summary: Export all artifacts for a source
    responses:
      200:
        description: ZIP archive containing all manifests and reports
        content:
          application/zip:
            schema:
              type: string
              format: binary
```

---

### F-006: Import Specifications Missing (MEDIUM)

**Issue:**
- No bulk-load endpoint
- No recovery workflow from backups
- Cannot restore sources from export

**Impact:** Cannot recover from backup; manual re-ingestion required.

**Resolution Required:**

Add to **OPENAPI_v1.0.md**:

```yaml
/sources/import:
  post:
    summary: Import previously exported source
    requestBody:
      content:
        multipart/form-data:
          schema:
            type: object
            properties:
              archive:
                type: string
                format: binary
    responses:
      200:
        description: Import successful
```

---

### F-007: API Versioning Undefined (HIGH)

**Issue:**
- No /api/v1/ version prefix
- No deprecation policy
- Breaking changes risk client failures

**Impact:** Cannot evolve API without breaking clients.

**Resolution Required:**

Create **docs/api/API_VERSIONING_v1.0.md**:

```markdown
# API_VERSIONING_v1.0.md

## Version Prefix
- All endpoints: /api/v1/...
- Example: /api/v1/sources, /api/v1/governance/sources/{doc_id}/approve

## Deprecation Policy
- Breaking changes → new major version (/api/v2/)
- Old version supported for 6 months after new version release
- Deprecation warnings in response headers: `X-API-Deprecation: true`

## Version Negotiation
- Client MUST specify version in URL path
- No default version (prevents accidental upgrades)
```

**Additional Updates:**
- **OPENAPI_v1.0.md** - Add `/api/v1/` prefix to all paths

---

### F-008: CORS Policy Missing (MEDIUM)

**Issue:**
- No Access-Control-Allow-Origin specified
- Browser-based UI integration unclear

**Impact:** Browser UI may not function; CORS errors.

**Resolution Required:**

Add to **DEPLOYMENT_v1.0.md**:

```markdown
## CORS Configuration

### Allowed Origins (DEV/TEST)
- http://localhost:3000 (nexus_ui)
- http://localhost:3001 (nexus_admin_ui)

### Allowed Methods
- GET, POST, PUT, PATCH, DELETE, OPTIONS

### Allowed Headers
- Content-Type, Authorization, X-API-Version

### Exposed Headers
- X-API-Deprecation, X-Rate-Limit-Remaining
```

---

### F-009: GraphQL Considerations (LOW - Deferred)

**Issue:**
- REST-only approach
- No migration path to GraphQL stated
- Potential future requirement

**Impact:** Limited flexibility for complex queries.

**Resolution:** Document as out-of-scope for MVP1; defer to post-MVP1 planning.

---

### F-010: WebSocket/SSE Missing (HIGH)

**Issue:**
- No real-time ingestion progress
- Admin cannot see live extraction status
- Polling required for status updates

**Impact:** Poor admin UX; inefficient status tracking.

**Resolution:** Covered in F-002 (SSE stream). Implement for governance state changes.

---

## High Priority Issues (Pre-Testing Required)

### H-001: Missing Error Recovery Tests

**Location:** TEST_CASES_v1.0.md

**Issue:**
- Test plan defines failure scenarios (Section 4.6.1) but no test cases cover recovery paths
- No test for ERROR → admin retry → INGESTED flow
- No test for partial chunk storage cleanup
- NFR-001 (idempotent retries) is untestable without error recovery tests

**Resolution Required:**

Add test cases to **TEST_CASES_v1.0.md**:

```markdown
T-ING-015: Extraction Failure Recovery
- Setup: Source approved, Docling fails (simulated network error)
- Expected: Status = ERROR, error logged
- Action: Admin retry via /governance/sources/{doc_id}/retry
- Expected: Status transitions ERROR → PENDING_APPROVAL → APPROVED → INGESTING → INGESTED
- Verify: Artifacts created, chunks stored, validation passes

T-ING-016: Partial Chunk Storage Cleanup
- Setup: Source ingested, 500 of 1000 chunks stored, then service crashes
- Expected: Status = ERROR
- Action: Admin retry
- Expected: Previous chunks cleared, re-ingestion creates fresh 1000 chunks
- Verify: No duplicate chunk_ids, all chunks have matching embeddings

T-VAL-001: Validation Failure Diagnostics
- Setup: Source ingested with intentionally missing manifest
- Action: Run validation
- Expected: Status = FAIL, report includes specific failed check
- Verify: Report specifies which artifact is missing and path expectation
```

---

### H-002: Chunk Uniqueness Not Validated

**Location:** VALIDATION_PLAN_v1.0.md Section 5.5

**Issue:**
- Section 5.5 states "Chunk identifiers are unique per source"
- But doesn't specify:
  - Unique within [source] or [source + tool_origin]?
  - What happens if collision detected?
  - How is uniqueness verified?
- Risk: Two tools could produce chunk_id "chunk_001", validation passes silently

**Resolution Required:**

1. **VALIDATION_PLAN_v1.0.md Section 5.5** - Add uniqueness validation check:
   ```
   ## 5.5 Chunk Uniqueness Validation

   Check: No duplicate chunk_ids exist across entire database

   Query:
   SELECT chunk_id, COUNT(*)
   FROM chunks
   WHERE doc_id = {doc_id}
   GROUP BY chunk_id
   HAVING COUNT(*) > 1

   Expected: Zero rows (no duplicates)

   If duplicates found:
   - Validation FAILS
   - Report lists all duplicate chunk_ids
   - Admin must investigate (likely tool bug or idempotency failure)

   Additional Check: Verify chunk_id format matches specification
   - Format: {doc_id}::{tool_id}::{chunk_sha256[:16]}
   - Reject if format invalid
   ```

2. **TEST_CASES_v1.0.md** - Add T-VAL-002: Collision detection test

---

### H-003: NFR Coverage Sparse

**Location:** REQUIREMENTS_v1.0.md NFR-001 through NFR-009

**Issue:**
- 9 non-functional requirements defined
- Only T-CLN-001 references NFRs (NFR-009)
- 8 NFRs have no test coverage

**Resolution Required:**

Add test cases to **TEST_CASES_v1.0.md**:

```markdown
T-NFR-001: Idempotency Verification
- FR Reference: NFR-001 "Ingestion steps MUST be safe to retry"
- Setup: Ingest source to INGESTED state, capture all artifact SHAs
- Action: Delete DB records, re-ingest same source with same tool versions
- Expected: Identical chunk_ids, chunk_sha256, manifest content
- Verify: Artifacts byte-identical (deterministic)

T-NFR-002: Partial Failure Observability
- FR Reference: NFR-002 "Partial failures MUST be observable and logged"
- Setup: Ingest source, kill Docling worker mid-extraction
- Expected: Status = ERROR, logs contain extraction failure details
- Verify: Admin can diagnose from logs alone (no DB inspection required)

T-NFR-003: Query Latency Measurement
- FR Reference: NFR-003 "Simple queries SHOULD complete within interactive latency"
- Setup: Ingest 10 sources (100 chunks each)
- Action: Run simple query (single keyword, no AI)
- Measure: Time from request to response
- Expected: <500ms (target; not blocking for MVP1)

T-NFR-005: Server-Side Role Validation
- FR Reference: NFR-005 "Role and context checks MUST be enforced server-side"
- Covered by T-SEC-001 (see C-006 resolution)

T-NFR-006: Admin-Only Endpoint Enforcement
- FR Reference: NFR-006 "Admin-only actions MUST NOT be accessible via UI manipulation"
- Covered by T-SEC-002 (see C-011 resolution)
```

---

### H-004: Metadata Enrichment Determinism Unchecked

**Location:** TEST_CASES_v1.0.md, REQUIREMENTS_v1.0.md FR-017

**Issue:**
- FR-017 requires deterministic enrichment
- No test verifies same source produces identical metadata on re-ingestion

**Resolution Required:**

Add **TEST_CASES_v1.0.md**:

```markdown
T-ING-008A: Deterministic Enrichment Verification
- Setup: Ingest source with system_id = "pathfinder"
- Capture: enriched manifest content_type and section_path for all blocks
- Action: Delete enriched manifests, re-run enrichment with same enrichment_rules version
- Expected: Identical content_type, section_path, entities for all blocks
- Verify: enrichment_version matches, output is byte-identical
```

---

### H-005 through H-018: Additional High Priority Issues

Due to length constraints, the following high-priority issues are summarized. Full details available in plan file (peaceful-questing-platypus.md).

| ID | Issue | Location | Resolution |
|----|-------|----------|------------|
| H-005 | Pagination missing from API | OPENAPI_v1.0.md | Add limit/offset to all list endpoints |
| H-006 | Tool version mismatch not detected | VALIDATION_PLAN_v1.0.md | Add version compatibility check |
| H-007 | Orphaned artifacts not detected | VALIDATION_PLAN_v1.0.md | Add orphan detection validation |
| H-008 | Concurrent state changes not handled | GOVERNANCE_FLOW_v1.0.md | Add state locking mechanism |
| H-009 | Transaction semantics undefined | INGESTION_DEPENDENCIES_v1.0.md | Define partial failure recovery |
| H-010 | Artifact path sanitization incomplete | INGESTION_ARCHITECTURE_v1.0.md Section 3.1 | Define full sanitization algorithm |
| H-011 | Feedback ranking algorithm undefined | REQUIREMENTS_v1.0.md FR-038 | Specify ranking impact formula |
| H-012 | Service startup order undefined | TEST_PLAN_v1.0.md Section 2.2 | Create DEPLOYMENT_v1.0.md |
| H-013 | Environment variables undefined | All documents | Define in DEPLOYMENT_v1.0.md |
| H-014 | Health check procedures missing | TEST_PLAN_v1.0.md | Define in DEPLOYMENT_v1.0.md |
| H-015 | Character sheet schema source undefined | UI_WIREFRAME_SPEC_v1.0.md Section 4 | Define schema loading mechanism |
| H-016 | Tier limit system undefined | UI_WIREFRAME_SPEC_v1.0.md Section 9.1 | Define tier_limits table and logic |
| H-017 | Validation report schema incomplete | DATABASE_SCHEMA_v1.0.md Section 4.1 | Define JSON report structure |
| H-018 | API endpoint contracts incomplete | OPENAPI_v1.0.md | Create detailed API_CONTRACTS_v1.0.md |

---

## Medium Priority Issues (Pre-Production Required)

### M-001 through M-017: Operational & Monitoring Gaps

Due to length constraints, medium-priority issues are summarized. Full details in plan file.

| ID | Issue | Resolution |
|----|-------|------------|
| M-001 | Monitoring metrics undefined | Create MONITORING_v1.0.md |
| M-002 | Alerting thresholds not specified | Define in MONITORING_v1.0.md |
| M-003 | Performance benchmarks missing | Create PERFORMANCE_BENCHMARKS_v1.0.md |
| M-004 | Log structure not specified | Define structured logging format |
| M-005 | Correlation IDs format undefined | Define trace ID propagation |
| M-006 | Test data requirements vague | Define test corpus requirements |
| M-007 | Artifact retention policy missing | Define cleanup policies |
| M-008 | Storage quota not enforced | Add storage limit NFR |
| M-009 | Embedding model fallback undefined | Define offline mode handling |
| M-010 | Active game context persistence unclear | Define session management |
| M-011 | Cleanup verification not automated | Add cleanup validation script |
| M-012 | Partial cleanup failure handling missing | Define rollback procedures |
| M-013 | Policy precedence undefined | Define conflict resolution rules |
| M-014 | Validator versioning undefined | Define compatibility matrix |
| M-015 | Chunk boundary violations unchecked | Add chunk size validation |
| M-016 | Cross-document terminology inconsistencies | Standardize glossary |
| M-017 | Admin approval bottleneck not modeled | Define throughput targets (post-MVP1) |

---

## Cross-Document Inconsistencies

### I-001: Artifact Immutability vs Enrichment

**Location:** ARTIFACT_CONTRACT_v1.0.md Section 2 vs REQUIREMENTS_v1.0.md FR-016

**Issue:**
- ARTIFACT_CONTRACT Section 2: "Artifacts are immutable once written"
- FR-016: "Metadata enrichment augments normalized manifests"

**Interpretation:** "Augment" could mean mutate (violates immutability) or create new artifact.

**Resolution:**
- **ARTIFACT_CONTRACT_v1.0.md Section 2** - Clarify:
  ```
  Artifact Immutability:
  - Each pipeline stage produces NEW immutable artifacts
  - Previous stage artifacts are NEVER modified
  - Example: Normalization creates docling_normalized.json; raw/docling_manifest.json remains unchanged
  - Enrichment creates docling_enriched.json; normalized manifest remains unchanged
  ```

---

### I-002: Validation vs Testing Authority

**Location:** VALIDATION_PLAN_v1.0.md vs TEST_PLAN_v1.0.md

**Issue:**
- Runtime validator (nexus_validator) certifies production
- Test validator (pytest) verifies correctness during development
- No specification of compatibility or shared codebase

**Resolution:**
- **VALIDATION_PLAN_v1.0.md Section 2** - Clarify:
  ```
  Validator Implementation:
  - Runtime validator (nexus_validator container) and test validator share codebase
  - Both implement identical validation logic from /validator/checks.py
  - Version must match: validator_version field in reports
  - Divergence is a critical bug
  ```

---

## Summary of Required Documentation Updates

### New Documents to Create (12 Total: 5 Original + 7 Second-Pass)

#### Original 5 Documents (First-Pass Review)

1. **docs/planning/TOOL_VERSIONS_v1.0.md** (CRITICAL)
   - Tool/library versions (Docling, Unstructured, pgvector, PostgreSQL)
   - Embedding model specification
   - Container base images
   - Version format standards
   - Compatibility matrix

2. **docs/api/JWT_SPEC_v1.0.md** (CRITICAL)
   - JWT claims structure (standard + custom)
   - Validation rules (server-side enforcement)
   - Token refresh flow (deferred)
   - Security requirements

3. **docs/deployment/DEPLOYMENT_v1.0.md** (CRITICAL)
   - Service startup order and dependencies
   - Health check procedures and endpoints
   - Environment variable definitions
   - Database migration procedures
   - CORS policy

4. **docs/operations/MONITORING_v1.0.md** (MEDIUM)
   - Metrics collection specifications
   - Alerting thresholds
   - Dashboard requirements
   - Log aggregation strategy

5. **docs/api/API_CONTRACTS_v1.0.md** (MEDIUM)
   - Detailed endpoint specifications
   - Request/response schemas
   - Error codes and messages
   - Rate limiting rules

#### New 7 Documents (Second-Pass Review - Data Integrity & Edge Cases)

6. **docs/database/DATABASE_CONSTRAINTS_v1.0.md** (CRITICAL - D-001)
   - Foreign key ON DELETE/ON UPDATE behaviors
   - Cascade rules for all relationships
   - Orphan prevention specifications
   - Deactivation vs deletion semantics

7. **docs/database/TRANSACTION_MODEL_v1.0.md** (CRITICAL - D-002, D-009)
   - Transaction boundaries for all multi-step operations
   - Isolation level specifications
   - Rollback procedures
   - Atomic operation definitions

8. **docs/database/CONCURRENCY_MODEL_v1.0.md** (CRITICAL - D-003, E-077+)
   - Optimistic locking implementation
   - Race condition handling
   - Mutex/lock mechanisms
   - Concurrent modification resolution

9. **docs/database/DATABASE_MIGRATION_v1.0.md** (HIGH - D-004)
   - Schema evolution procedures
   - Tool version upgrade strategies
   - Backward compatibility requirements
   - Migration tooling (Alembic)

10. **docs/operations/BACKUP_AND_RECOVERY_v1.0.md** (HIGH - D-005)
    - Backup strategies and schedules
    - RPO/RTO specifications
    - Disaster recovery procedures
    - Restore workflows

11. **docs/requirements/EDGE_CASES_v1.0.md** (HIGH - E-001 to E-089)
    - Comprehensive edge case catalog (89 cases)
    - Empty/null handling specifications
    - Extreme value behaviors
    - Illegal state prevention

12. **docs/requirements/RESOURCE_LIMITS_v1.0.md** (CRITICAL - E-010 to E-016, E-030 to E-035)
    - File size limits (source, manifest, chunk)
    - Database record limits (chunks per doc)
    - Concurrency limits (jobs, validations)
    - Storage quotas
    - Rate limiting specifications

13. **docs/requirements/FAULT_RECOVERY_v1.0.md** (CRITICAL - E-036 to E-047)
    - Resource exhaustion handling (disk, memory, connections)
    - Network failure retry policies
    - Worker crash recovery
    - Exponential backoff strategies
    - Timeout specifications

14. **docs/api/API_VERSIONING_v1.0.md** (HIGH - F-007)
    - Version prefix (/api/v1/)
    - Deprecation policy
    - Version negotiation
    - Breaking change procedures

### Existing Documents to Update (12)

#### CRITICAL Updates (Implementation Blockers):

1. **GOVERNANCE_FLOW_v1.0.md**
   - Section 4.1: Add DUPLICATE_DETECTED status
   - Section 4.1: Add DENIED → PENDING_APPROVAL transition
   - Section 5.5: Add "Orchestrator-Triggered Transitions" (new section)
   - Section 4.4: Specify deactivation detection mechanism
   - Section 7: Add REMOVAL_REQUEST event type

2. **DATABASE_SCHEMA_v1.0.md**
   - Section 2.1: Add DUPLICATE_DETECTED to status enum
   - Section 2.1: Clarify ownership model (owner_user_id NOT NULL)
   - Section 2.2: Add event_type field to governance_events
   - Section 3.2: Add UNIQUE constraint (doc_id, tool_id, chunk_sha256)
   - Section 3.3: Specify embedding vector(384)
   - Section 6.1: Clarify source_links is for sharing only

3. **INGESTION_ARCHITECTURE_v1.0.md**
   - Section 5: Add orchestrator component description
   - Section 5.3: Reference governance_events for removal requests
   - Section 9.4: Add "Hybrid Enrichment Algorithm" (new section)
   - Section 12.1: Specify deactivation detection (polling, 60s interval)

4. **OPENAPI_v1.0.md**
   - Add DUPLICATE_DETECTED to GovernanceStatus enum
   - Add reference to JWT_SPEC_v1.0.md in security section
   - Add POST /governance/sources/{doc_id}/override-denial endpoint
   - Add GET /orchestrator/health endpoint
   - Add GET /admin/audit/{doc_id} endpoint (audit-only)
   - Add pagination parameters (limit, offset) to list endpoints

5. **ARTIFACT_CONTRACT_v1.0.md**
   - Section 2: Clarify artifact immutability (new artifacts, not mutations)
   - Section 5.5: Define chunk_id format specification
   - Add enrichment_rules config directory location
   - Add enrichment_version tracking requirement

#### HIGH Priority Updates (Pre-Testing):

6. **REQUIREMENTS_v1.0.md**
   - Update FR-032/FR-033 to reference ownership model clarification
   - Add NFR-001 requirement: chunk_id determinism
   - Reference JWT_SPEC_v1.0.md in NFR-005

7. **TEST_CASES_v1.0.md**
   - Add T-ING-002A: Duplicate state transitions
   - Add T-ING-008A: Deterministic enrichment verification
   - Add T-ING-009A: Chunk ID determinism (re-ingestion)
   - Add T-ING-015: Extraction failure recovery
   - Add T-ING-016: Partial chunk storage cleanup
   - Add T-VAL-001: Validation failure diagnostics
   - Add T-VAL-002: Chunk collision detection
   - Add T-SEC-001: Role-based endpoint access
   - Add T-SEC-002: Admin audit-only enforcement
   - Add T-SEC-003: GM-only scope bypass prevention
   - Add T-NFR-001: Idempotency verification
   - Add T-NFR-002: Partial failure observability
   - Add T-NFR-003: Query latency measurement
   - Update T-ING-014: Deactivation timing assertion (120s)
   - Add T-GOV-005: Denial reversal

8. **VALIDATION_PLAN_v1.0.md**
   - Section 2: Clarify validator shared codebase
   - Section 5.5: Add chunk uniqueness validation check
   - Section 5.5: Add chunk_id format validation
   - Section 5.6: Add tool version compatibility check
   - Section 5.7: Add orphaned artifact detection

9. **ACCESS_MATRIX_v1.0.md**
   - Section 4: Define admin audit-only scope (CAN vs CANNOT)
   - Section 6: Add GM-only scope bypass prevention

10. **QUERY_POLICY_v1.0.md**
    - Section 3: Add pre-query doc_id scope validation

#### MEDIUM Priority Updates (Pre-Production):

11. **ARCHITECTURE_v1.0.md**
    - Section 2.2: Add nexus_orchestrator container
    - Section 6: Reference embedding model choice (TOOL_VERSIONS_v1.0.md)

12. **PHASE_MAP_v1.0.md**
    - Update Phase 0 test case mappings to include new tests

---

## Implementation Blocker Status

**CANNOT START IMPLEMENTATION** until these 18 items are resolved:

### Original 8 Blockers (From First-Pass Review)

| # | Blocker | Status | Resolution |
|---|---------|--------|------------|
| 1 | Duplicate detection status | ✅ RESOLVED | User decision: Add DUPLICATE_DETECTED (see C-001) |
| 2 | INGESTING trigger mechanism | ✅ RESOLVED | User decision: Job queue scheduler (see C-002) |
| 3 | Enrichment algorithm | ✅ RESOLVED | User decision: Hybrid approach (see C-005) |
| 4 | Removal request workflow | ✅ RESOLVED | User decision: Use governance_events (see C-008) |
| 5 | Tool versions | ❌ SPECIFICATION REQUIRED | Create TOOL_VERSIONS_v1.0.md (see C-003) |
| 6 | Ownership model | ❌ SPECIFICATION REQUIRED | Update DATABASE_SCHEMA_v1.0.md (see C-007) |
| 7 | Chunk ID format | ❌ SPECIFICATION REQUIRED | Update ARTIFACT_CONTRACT_v1.0.md (see C-004) |
| 8 | JWT claims structure | ❌ SPECIFICATION REQUIRED | Create JWT_SPEC_v1.0.md (see C-006) |

### New 10 Critical Blockers (From Second-Pass Review)

| # | Blocker | Status | Resolution |
|---|---------|--------|------------|
| 9 | CASCADE delete/deactivate rules | ❌ SPECIFICATION REQUIRED | Create DATABASE_CONSTRAINTS_v1.0.md (see D-001) |
| 10 | Transaction boundaries | ❌ SPECIFICATION REQUIRED | Create TRANSACTION_MODEL_v1.0.md (see D-002) |
| 11 | Concurrent modification handling | ❌ SPECIFICATION REQUIRED | Create CONCURRENCY_MODEL_v1.0.md (see D-003) |
| 12 | Orphan prevention constraints | ❌ SPECIFICATION REQUIRED | Update DATABASE_SCHEMA_v1.0.md (see D-008) |
| 13 | Deactivation atomicity | ❌ SPECIFICATION REQUIRED | Reference TRANSACTION_MODEL_v1.0.md (see D-009) |
| 14 | Size limits | ❌ SPECIFICATION REQUIRED | Create RESOURCE_LIMITS_v1.0.md (see E-010 to E-016) |
| 15 | Resource exhaustion handling | ❌ SPECIFICATION REQUIRED | Create FAULT_RECOVERY_v1.0.md (see E-036 to E-041) |
| 16 | Network failure retry policies | ❌ SPECIFICATION REQUIRED | Reference FAULT_RECOVERY_v1.0.md (see E-042 to E-047) |
| 17 | Illegal state prevention | ❌ SPECIFICATION REQUIRED | Reference CONCURRENCY_MODEL_v1.0.md (see E-061 to E-066) |
| 18 | API versioning strategy | ❌ SPECIFICATION REQUIRED | Create API_VERSIONING_v1.0.md (see F-007) |

**Progress:** 4 of 18 blockers resolved through user decisions
**Remaining:** 14 specifications need writing before implementation can proceed

---

## Traceability Matrix

### Critical Issues → Documentation Updates

| Issue | Documents to Update | Test Cases to Add |
|-------|-------------------|-------------------|
| C-001 (Duplicate Status) | GOVERNANCE_FLOW, DATABASE_SCHEMA, OPENAPI | T-ING-002A |
| C-002 (INGESTING Trigger) | ARCHITECTURE, GOVERNANCE_FLOW, OPENAPI | None |
| C-003 (Tool Versions) | Create TOOL_VERSIONS | None |
| C-004 (Chunk ID) | ARTIFACT_CONTRACT, DATABASE_SCHEMA, REQUIREMENTS | T-ING-009A, T-NFR-001 |
| C-005 (Enrichment) | INGESTION_ARCHITECTURE, ARTIFACT_CONTRACT | T-ING-008A |
| C-006 (JWT Claims) | Create JWT_SPEC, OPENAPI, REQUIREMENTS | T-SEC-001 |
| C-007 (Ownership) | DATABASE_SCHEMA, REQUIREMENTS, OPENAPI | None |
| C-008 (Removal) | GOVERNANCE_FLOW, DATABASE_SCHEMA | None |
| C-009 (Deactivation) | GOVERNANCE_FLOW, TEST_CASES | T-ING-014 (update) |
| C-010 (Denied→Pending) | GOVERNANCE_FLOW, OPENAPI | T-GOV-005 |
| C-011 (Admin Audit) | ACCESS_MATRIX, OPENAPI | T-SEC-002 |
| C-012 (Scope Bypass) | QUERY_POLICY | T-SEC-003 |

### Requirements → Test Coverage Gaps

| Requirement | Current Tests | Missing Tests | Priority |
|-------------|---------------|---------------|----------|
| FR-001 through FR-007 | T-ING-001, T-ING-002, T-ING-003 | T-ING-002A (duplicates) | CRITICAL |
| FR-011 through FR-014 | T-ING-004, T-ING-005, T-ING-006 | None | ✓ |
| FR-015 through FR-018 | T-ING-007, T-ING-008, T-ING-009 | T-ING-008A (determinism) | HIGH |
| FR-019 through FR-020 | T-ING-009 | T-ING-009A (chunk_id) | CRITICAL |
| FR-023 through FR-026 | T-ING-010, T-ING-011, T-ING-012, T-ING-013 | T-VAL-001, T-VAL-002 | HIGH |
| FR-032 through FR-034 | None | T-SEC-003 (scope) | CRITICAL |
| NFR-001 | None | T-NFR-001 (idempotency) | HIGH |
| NFR-002 | None | T-NFR-002 (observability) | HIGH |
| NFR-005, NFR-006 | None | T-SEC-001, T-SEC-002 | CRITICAL |

---

## Recommended Next Steps (Updated for v1.1)

### CRITICAL: Phase 1 - Data Integrity Foundation (BLOCKING)

**Goal:** Prevent data corruption and ensure transaction safety

**Priority:** **HIGHEST** - Must complete before any other work

1. **Create critical data integrity documents** (estimated: 8-12 hours):
   - docs/database/DATABASE_CONSTRAINTS_v1.0.md (2-3 hours)
     - All FK ON DELETE/ON UPDATE behaviors
     - Cascade rules for sources → chunks → embeddings → FTS
     - Orphan prevention specifications

   - docs/database/TRANSACTION_MODEL_v1.0.md (3-4 hours)
     - Transaction boundaries for ingestion pipeline
     - Deactivation atomic operations
     - Rollback procedures
     - Isolation level specifications

   - docs/database/CONCURRENCY_MODEL_v1.0.md (3-5 hours)
     - Optimistic locking implementation details
     - Admin approval race condition handling
     - Orchestrator polling mutex
     - State version conflict resolution

2. **Update DATABASE_SCHEMA_v1.0.md** (estimated: 2 hours):
   - Add FK constraint specifications with CASCADE rules
   - Add optimistic locking examples
   - Add orphan prevention constraints

**Deliverable:** Data integrity foundation specified; safe to proceed with implementation

**Risk if skipped:** HIGH - Data corruption, orphaned records, inconsistent state

---

### CRITICAL: Phase 2 - Edge Case & Resource Specifications (BLOCKING)

**Goal:** Prevent resource exhaustion and runtime failures

**Priority:** **CRITICAL** - Required before testing

3. **Create edge case and resource documents** (estimated: 6-8 hours):
   - docs/requirements/RESOURCE_LIMITS_v1.0.md (2 hours)
     - File size limits (source: 100MB, manifest: 10MB, chunk: 8K chars)
     - Database limits (10K chunks/doc)
     - Concurrency limits (3 jobs, 2 validations)
     - Storage quotas (50GB Transfer Station)

   - docs/requirements/FAULT_RECOVERY_v1.0.md (2-3 hours)
     - Resource exhaustion handling (disk, memory, connections)
     - Retry policies (exponential backoff)
     - Worker crash recovery
     - Timeout specifications

   - docs/requirements/EDGE_CASES_v1.0.md (2-3 hours)
     - Catalog of 89 edge cases with expected behaviors
     - Empty/null handling (9 cases)
     - Special characters (7 cases)
     - Extreme values (6 cases)
     - Illegal states (6 cases)

**Deliverable:** Edge cases documented; resource limits enforced

**Risk if skipped:** MEDIUM-HIGH - Runtime crashes, OOM failures, disk full errors

---

### CRITICAL: Phase 3 - API Completeness (HIGH PRIORITY)

**Goal:** Enable production-grade API usability

**Priority:** **HIGH** - Required before UI integration

4. **Create API enhancement documents** (estimated: 4-6 hours):
   - docs/api/API_VERSIONING_v1.0.md (1-2 hours)
     - Version prefix (/api/v1/)
     - Deprecation policy

   - Expand OPENAPI_v1.0.md (2-3 hours)
     - Add bulk operations (approve, deny, retry)
     - Add SSE stream endpoint for real-time events
     - Add PATCH endpoints for metadata updates
     - Add search/filter parameters
     - Add rate limit headers

   - Update DEPLOYMENT_v1.0.md (1 hour)
     - Add CORS policy specifications

**Deliverable:** Production-grade API with bulk ops, versioning, real-time updates

**Risk if skipped:** MEDIUM - Poor UX, inefficient workflows, integration challenges

---

### Phase 4 - Original Blockers (CRITICAL)

**Goal:** Resolve remaining v1.0 blockers

**Priority:** **CRITICAL** - Required before implementation

5. **Create original blocker documents** (estimated: 4-6 hours):
   - docs/planning/TOOL_VERSIONS_v1.0.md (1-2 hours)
   - docs/api/JWT_SPEC_v1.0.md (1 hour)
   - docs/deployment/DEPLOYMENT_v1.0.md (1-2 hours)
   - Update DATABASE_SCHEMA_v1.0.md - ownership model (30 min)
   - Update ARTIFACT_CONTRACT_v1.0.md - chunk ID format (30 min)

6. **Update 5 critical documents** (estimated: 4-6 hours):
   - GOVERNANCE_FLOW_v1.0.md (4 updates)
   - INGESTION_ARCHITECTURE_v1.0.md (3 updates)
   - OPENAPI_v1.0.md (5 updates)
   - ARTIFACT_CONTRACT_v1.0.md (3 updates)

**Deliverable:** All v1.0 blockers resolved

---

### Phase 5 - Test Coverage Expansion (HIGH PRIORITY)

**Goal:** Enable comprehensive test execution

7. **Update TEST_CASES_v1.0.md** (estimated: 4-6 hours):
   - Add 15 new test cases for v1.0 issues
   - Add 8 data integrity test cases (T-INT-001 to T-INT-004, T-CON-001)
   - Add 7 edge case validation tests
   - Add 5 API integration tests
   - Total: ~50 test cases (from 14 original)

8. **Generate consolidated test case list** (estimated: 1 hour):
   - Validate FR/NFR → test case mappings
   - Ensure no orphaned requirements

9. **Create PowerShell test infrastructure** (estimated: 4-6 hours):
   - Implement test runner per POWERSHELL_TEST_RUNNER_AGENT_PROMPT_v1.0.md
   - Create cleanup scripts
   - Validate container orchestration

**Deliverable:** Test plan complete, all FRs/NFRs testable, edge cases validated

---

### Phase 6 - Operational Readiness (MEDIUM PRIORITY)

**Goal:** Production deployment readiness

10. **Create operational documentation** (estimated: 4-6 hours):
    - docs/operations/MONITORING_v1.0.md
    - docs/operations/BACKUP_AND_RECOVERY_v1.0.md
    - docs/database/DATABASE_MIGRATION_v1.0.md

11. **Complete MEDIUM priority updates** (estimated: 2-3 hours):
    - ARCHITECTURE_v1.0.md (2 updates)
    - PHASE_MAP_v1.0.md (1 update)
    - CLEANUP_STRATEGY_v1.0.md (expand retention policies)

12. **Security audit preparation** (estimated: 2-4 hours):
    - Penetration testing checklist
    - Vulnerability assessment scope
    - Access control validation matrix

**Deliverable:** Production-ready documentation and operational runbooks

---

## Total Estimated Effort (v1.1)

| Phase | Priority | Estimated Hours | Cumulative Hours |
|-------|----------|----------------|------------------|
| Phase 1: Data Integrity | CRITICAL | 8-12 | 8-12 |
| Phase 2: Edge Cases | CRITICAL | 6-8 | 14-20 |
| Phase 3: API Completeness | HIGH | 4-6 | 18-26 |
| Phase 4: Original Blockers | CRITICAL | 4-6 | 22-32 |
| Phase 5: Test Coverage | HIGH | 9-13 | 31-45 |
| Phase 6: Operational | MEDIUM | 8-13 | 39-58 |

**Total Effort Before Implementation: 39-58 hours** (vs original estimate 22-32 hours for v1.0)

**Critical Path:** Phases 1-4 MUST complete before implementation (22-32 hours)

---

## Conclusion

This **second-pass architectural review** identifies **significant planning strengths** alongside **critical data integrity, edge case, and operational gaps**. The Nexus Core MVP1 architecture is sound, governance is comprehensive, and requirements are well-traced. However, the initial review (v1.0) focused primarily on architectural concerns and **missed critical data integrity issues, transaction semantics, and boundary condition specifications** that must be addressed before implementation.

**Critical Finding:** The documentation has **severe data integrity gaps** (10 critical issues) that represent the highest risk for silent data corruption. These issues (CASCADE rules, transaction boundaries, concurrency handling) were not identified in the first review pass but are **implementation blockers**.

**Primary Recommendation (Data Integrity - CRITICAL):** Before any other work, create:
- DATABASE_CONSTRAINTS_v1.0.md (FK cascade rules)
- TRANSACTION_MODEL_v1.0.md (atomic operations)
- CONCURRENCY_MODEL_v1.0.md (race condition handling)

These three documents define the **data integrity foundation** for the entire system. Without them, implementation will produce data corruption bugs that are expensive to fix.

**Secondary Recommendation (Edge Cases - HIGH):** Create:
- RESOURCE_LIMITS_v1.0.md (prevent resource exhaustion)
- FAULT_RECOVERY_v1.0.md (handle failures gracefully)
- EDGE_CASES_v1.0.md (document boundary conditions)

**Tertiary Recommendation (Original Blockers - CRITICAL):** Complete the 4 remaining original blockers from v1.0:
- TOOL_VERSIONS_v1.0.md
- JWT_SPEC_v1.0.md
- Update DATABASE_SCHEMA_v1.0.md (ownership model)
- Update ARTIFACT_CONTRACT_v1.0.md (chunk ID format)

**Test Coverage Expansion:** The current 14 test cases should grow to **~50 test cases** to cover:
- Original FRs/NFRs (35 test cases)
- Data integrity scenarios (8 test cases)
- Edge case validation (7 test cases)

**Documentation Quality Assessment (Updated):**
- **Architecture & Governance:** Excellent (95% complete)
- **Requirements Traceability:** Very Good (90% complete)
- **Implementation Guidance:** Good (75% complete)
- **Data Integrity Specifications:** **Poor (20% complete)** ⚠️
- **Edge Case Coverage:** **Poor (15% complete)** ⚠️
- **Operational Readiness:** Fair (50% complete)

**Estimated Effort Before Implementation:**
- Phase 1: Critical Data Integrity - 8-12 hours
- Phase 2: Critical Edge Cases - 6-8 hours
- Phase 3: API Completeness - 4-6 hours
- Phase 4: Original Blockers - 4-6 hours
- **Total: 22-32 hours**

**Risk Assessment:**
- **Without Data Integrity Fixes:** HIGH risk of data corruption in production
- **Without Edge Case Specs:** MEDIUM risk of runtime failures on boundary conditions
- **Without API Completeness:** MEDIUM risk of poor UX and integration failures

With the recommended updates (14 new documents + 12 updated documents), Nexus Core MVP1 documentation will be comprehensive, data-safe, and implementation-ready.

---

## Change Control

This review document is versioned.

**Version History:**
- **v1.0** (2026-01-14): Initial review - identified 47 gaps (12 Critical, 18 High, 17 Medium)
  - Focused on architectural concerns, governance clarity, requirement traceability
  - Identified 8 critical implementation blockers
  - Missed data integrity, transaction semantics, and edge case specifications

- **v1.1** (2026-01-14): Second-pass review - identified 65 additional gaps
  - Added Category D: Data Integrity & Consistency (10 critical issues)
  - Added Category E: Edge Cases & Boundary Conditions (89 specifications)
  - Added Category F: API & Integration Gaps (10 major areas)
  - Updated blocker count from 8 to 18
  - Total gaps: 112 (47 original + 65 new)

**Change Policy:**
- Any changes to findings require version bump
- v1.1 supersedes v1.0 (v1.0 retained for historical reference)
- All referenced documents should update to reflect review recommendations

---

## Review Acceptance Statement

This architectural review (v1.1) is considered complete when:
- All critical blockers are addressed:
  - Original blockers: C-001 through C-012 (8 total)
  - Data integrity blockers: D-001, D-002, D-003, D-008, D-009 (5 total)
  - Edge case blockers: E-010 to E-016, E-036 to E-047, E-061 to E-066 (critical subsets)
  - API blocker: F-007 (1 total)
- High priority test gaps are filled:
  - Original: H-001 through H-004
  - Data integrity: D-004 through D-007
  - Edge cases: E-001 to E-089 (documented in EDGE_CASES_v1.0.md)
  - API integration: F-001 through F-010
- All 14 new specification documents are created
- All 12 existing documents are updated
- Implementation can proceed with confidence in:
  - Specification completeness
  - Data integrity guarantees
  - Edge case handling
  - API usability

**Acceptance Criteria:**
✅ Architecture sound (achieved)
✅ Governance comprehensive (achieved)
✅ Requirements traced (achieved)
❌ Data integrity specified (requires Phase 1: 8-12 hours)
❌ Edge cases documented (requires Phase 2: 6-8 hours)
❌ Operational readiness (requires Phase 3: 4-6 hours)

This document (v1.1) defines the **authoritative and comprehensive architectural review** for Nexus Core MVP1 planning phase.

**Recommendation:** Do NOT proceed to implementation until all ❌ criteria are ✅. The risk of data corruption and runtime failures is too high.

---

## Summary of Changes: v1.0 → v1.1

### What Changed

**v1.0 Review (Initial):**
- Focused on: Architecture, governance, requirements, API contracts
- Identified: 47 gaps (12 Critical, 18 High, 17 Medium)
- Blockers: 8 total (4 resolved, 4 specifications needed)
- Estimated effort: 22-32 hours
- Coverage: Architectural soundness, governance clarity, requirement traceability

**v1.1 Review (Second-Pass):**
- Focused on: Data integrity, edge cases, boundary conditions, API integration
- Identified: 65 ADDITIONAL gaps (10 Critical, 25 High, 30 Medium)
- Total gaps: **112** (47 + 65)
- Blockers: **18 total** (4 resolved, 14 specifications needed)
- Estimated effort: **39-58 hours** (increased from 22-32 hours)
- Coverage: Everything in v1.0 + data integrity, transaction safety, concurrency, edge cases

### Key New Findings

1. **Data Integrity Crisis (Category D):**
   - 10 critical issues that could cause silent data corruption
   - CASCADE rules completely missing
   - Transaction boundaries undefined
   - Concurrency conflicts unhandled
   - **Impact:** Cannot safely implement without these specifications

2. **Edge Case Blind Spots (Category E):**
   - 89 boundary conditions not documented
   - Resource limits undefined (file size, chunk count, concurrency)
   - Fault recovery policies missing
   - Extreme values unspecified
   - **Impact:** Runtime failures on boundary conditions

3. **API Usability Gaps (Category F):**
   - No bulk operations (must approve sources one-by-one)
   - No real-time events (UI must poll)
   - No API versioning (cannot evolve API)
   - Limited search/filtering
   - **Impact:** Poor UX, inefficient workflows

### Why v1.0 Missed These Issues

The initial review (v1.0) was **deliberately focused** on:
- Architectural soundness ✓
- Governance model completeness ✓
- Requirements traceability ✓
- API endpoint coverage ✓

The v1.0 review **did not deeply examine**:
- Database constraints and referential integrity ✗
- Transaction semantics and atomicity ✗
- Concurrency and race conditions ✗
- Resource limits and quotas ✗
- Fault recovery and retry policies ✗
- Edge case specifications ✗

**Lesson Learned:** Architectural reviews require **multiple passes** with different focuses:
- **Pass 1:** Architecture, governance, requirements (v1.0)
- **Pass 2:** Data integrity, transactions, concurrency (v1.1 - Category D)
- **Pass 3:** Edge cases, resource limits, fault recovery (v1.1 - Category E)
- **Pass 4:** API usability, integration, UX (v1.1 - Category F)

### Critical Recommendations for v1.1

1. **Start with Data Integrity (Phase 1):**
   - Create DATABASE_CONSTRAINTS_v1.0.md
   - Create TRANSACTION_MODEL_v1.0.md
   - Create CONCURRENCY_MODEL_v1.0.md
   - **This is the foundation** - without it, implementation will produce data corruption bugs

2. **Then Handle Edge Cases (Phase 2):**
   - Create RESOURCE_LIMITS_v1.0.md
   - Create FAULT_RECOVERY_v1.0.md
   - Create EDGE_CASES_v1.0.md
   - **This prevents runtime crashes** - without it, system will fail on boundary conditions

3. **Then Improve API (Phase 3):**
   - Create API_VERSIONING_v1.0.md
   - Expand OPENAPI_v1.0.md with bulk ops and SSE
   - **This enables production UX** - without it, system is usable but inefficient

4. **Finally Complete Original Blockers (Phase 4):**
   - Create remaining v1.0 documents (TOOL_VERSIONS, JWT_SPEC, DEPLOYMENT)
   - Update existing documents
   - **This unblocks implementation** - the final step before coding can begin

### Bottom Line

**v1.0 was architecturally focused** - it validated the design is sound.

**v1.1 is implementation-focused** - it validates the system can be built safely, handle failures gracefully, and operate in production.

**Both reviews are necessary.** Architecture without data integrity = buggy system. Data integrity without architecture = well-built wrong thing.

**Total work required before implementation:** 39-58 hours (across 14 new documents + 12 updated documents)
