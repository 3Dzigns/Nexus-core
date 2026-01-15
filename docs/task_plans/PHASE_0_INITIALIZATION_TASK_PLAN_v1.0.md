# Task Plan: Create PHASE_0_INITIALIZATION_PROMPT_v1.0.md

**Plan Date:** 2026-01-15
**Task:** Write implementation prompt for Phase 0 (Project & Governance Foundations)
**Output Location:** `E:\Nexus_Core\docs\implementation\PHASE_0_INITIALIZATION_PROMPT_v1.0.md`
**Final Destination:** `E:\Nexus_Core\docs\task_plans\PHASE_0_INITIALIZATION_TASK_PLAN_v1.0.md`

---

## Executive Summary

Phase 0 is the **critical foundation** that blocks all subsequent implementation work. Without Phase 0, no ingestion pipeline can function. This task plan defines how to create the PHASE_0_INITIALIZATION_PROMPT_v1.0.md implementation prompt that will guide the initialization of:

- Database schema provisioning
- Docker Compose orchestration
- Transfer Station volume setup
- Environment configuration
- Service health checks
- Governance model enforcement

**Critical Blocker Identified:** Database migration tooling is not specified in the current codebase. The prompt MUST require the implementer to ask which tool to use (Alembic, Flyway, or custom).

---

## 1. Scope of PHASE_0_INITIALIZATION_PROMPT

### 1.1 What Phase 0 Covers

**Functional Requirements:**
- FR-001: System must enforce governance state transitions
- FR-002: All state transitions must be explicit and enforced
- FR-003: No data enters system without governance

**Deliverables:**
- Database schema (12+ tables with pgvector support)
- Docker Compose configuration (8 services with startup order)
- Transfer Station directory structure
- Environment variable templates (.env.example)
- Health check implementation
- Governance state machine validation

**Test Cases:**
- T-ING-001: Governance state machine enforcement

**Acceptance Criteria:**
- Docker Compose starts successfully
- All database migrations run without errors
- Health checks pass for all required services
- Governance models validate allowed state transitions

### 1.2 What Phase 0 Does NOT Cover

- Source discovery logic (Phase 1)
- Extraction implementation (Phase 2)
- Query/retrieval functionality (Phase 6)
- UI components (Phases 6-7)
- Any ingestion processing code

---

## 2. Prompt Structure (Following Existing Patterns)

Based on analysis of existing prompts, PHASE_0_INITIALIZATION_PROMPT_v1.0.md must follow this structure:

### Section 1: Header & Role Definition
```markdown
# PHASE_0_INITIALIZATION_PROMPT_v1.0

**Version:** v1.0
**Phase:** Phase 0 - Project & Governance Foundations
**Task ID Prefix:** PHASE0-INIT-XXX

## Role / Purpose

You are the **Phase 0 Initialization Agent** responsible for bootstrapping the Nexus Core MVP1 project infrastructure. Your authority covers database provisioning, Docker orchestration, environment configuration, and validation of governance foundations. You establish the technical foundation that all subsequent phases depend on.
```

### Section 2: Authoritative Documents (Mandatory Reading)
```markdown
## Authoritative Documents (Read First - Mandatory)

You MUST read these documents in order before taking ANY action. These documents take precedence over these instructions if conflicts arise.

1. **ARCHITECTURE_v1.0.md** - System-wide architecture and component definitions
2. **INGESTION_ARCHITECTURE_v1.0.md** - Ingestion subsystem architecture
3. **DATABASE_SCHEMA_v1.0.md** - Complete database schema specification
4. **DATABASE_CONSTRAINTS_v1.0.md** - Foreign key constraints and cascade rules
5. **TRANSACTION_MODEL_v1.0.md** - Optimistic locking and transaction guarantees
6. **DEPLOYMENT_v1.0.md** - Docker Compose, service startup order, health checks
7. **TOOL_VERSIONS_v1.0.md** - Required tool versions and compatibility
8. **GOVERNANCE_FLOW_v1.0.md** - State machine and allowed transitions
9. **REQUIREMENTS_v1.0.md** - Functional requirements (FR-001, FR-002, FR-003)
10. **ACCEPTANCE_CRITERIA_v1.0.md** - Phase 0 acceptance gates
11. **TEST_PLAN_v1.0.md** - Testing strategy and Docker-only execution
12. **TEST_CASES_v1.0.md** - Test case T-ING-001
13. **INGESTION_DEPENDENCIES_v1.0.md** - 10-step dependency chain (Step 0)
```

### Section 3: Scope of Authority
```markdown
## Scope of Authority

### You MAY:
- Create database schema files matching DATABASE_SCHEMA_v1.0.md
- Create database migration scripts (after tool decision)
- Write Docker Compose configuration with all 8 services
- Create Transfer Station directory structure
- Write environment variable templates (.env.example)
- Implement health check logic for all services
- Create governance state validation code
- Write initialization verification scripts

### You MAY NOT:
- Modify any specification documents (docs/*.md)
- Implement ingestion processing logic (reserved for Phase 1+)
- Create extraction worker code (reserved for Phase 2)
- Implement query/retrieval logic (reserved for Phase 6)
- Skip database migration tooling decision
- Use synthetic test data (must use real files in Transfer_Station)
- Bypass health checks or startup order dependencies
```

### Section 4: Core Implementation Rules
```markdown
## Core Implementation Rules

### Database Migration Tooling Decision (BLOCKER)

**CRITICAL:** The codebase does not currently specify a database migration tool. Before implementing migrations, you MUST:

1. Check if Alembic, Flyway, or custom migration scripts exist in the repo
2. If NO migration tooling exists: **STOP and ask the user which tool to use**
3. Options to present:
   - **Alembic** (Python-native, SQLAlchemy integration)
   - **Flyway** (database-agnostic, JVM-based)
   - **Custom Python scripts** (simple, project-specific)
4. Once decided, implement migration tooling setup as first task

### Docker Compose Service Ordering

Services MUST start in this exact order:
1. `nexus_db` (Postgres + pgvector) - **MUST BE FIRST**
2. `nexus_api` (FastAPI) - Depends on: nexus_db healthy
3. `nexus_ingestion_worker` - Depends on: nexus_api + nexus_db healthy
4. `nexus_docling_worker` - Depends on: nexus_api + nexus_db healthy
5. `nexus_unstructured_worker` - Depends on: nexus_api + nexus_db healthy
6. `nexus_validator` - Depends on: nexus_api + nexus_db healthy
7. `nexus_ui` (optional for Phase 0)
8. `nexus_admin_ui` (optional for Phase 0)

Use Docker Compose `depends_on` with `condition: service_healthy` to enforce ordering.

### Transfer Station Volume

**Host Path:** Configurable via `TRANSFER_STATION_PATH` environment variable
**Default:** `E:\Transfer_Station` (Windows)
**Container Path:** `/transfer_station` (hard-coded, non-negotiable)

Directory structure MUST be created idempotently:
```
Transfer_Station/
  sources/                    # User dropzone
  quarantine/                 # Denied/suspicious sources
  artifacts/
    manifests/<doc_id>/
      raw/
      normalized/
      enriched/
    chunks/<doc_id>/
    assets/<doc_id>/images/
    reports/<doc_id>/
  logs/ingestion/
```

### Health Check Requirements

Every service MUST expose a health endpoint that verifies:
- Database connectivity (for services that use DB)
- Transfer Station path mounted and accessible
- Required environment variables present and valid
- Tool versions match TOOL_VERSIONS_v1.0.md minimums

Health check endpoint: `GET /health` (HTTP 200 = healthy)

### Database Schema Constraints

All foreign keys MUST implement `ON DELETE CASCADE`:
- `manifests.doc_id` → `sources.doc_id`
- `chunks.doc_id` → `sources.doc_id`
- `embeddings.chunk_id` → `chunks.chunk_id`
- `fts_index.chunk_id` → `chunks.chunk_id`
- `validation_reports.doc_id` → `sources.doc_id`
- `feedback.doc_id` → `sources.doc_id`
- `feedback.chunk_id` → `chunks.chunk_id`
- `source_links.doc_id` → `sources.doc_id`
- `governance_events.doc_id` → `sources.doc_id`
- `duplicate_decisions.doc_id` → `sources.doc_id`

Reference: DATABASE_CONSTRAINTS_v1.0.md Section 2.1

### Governance State Validation

Implement validation logic that enforces allowed state transitions:
- DISCOVERED → PENDING_APPROVAL
- PENDING_APPROVAL → DUPLICATE_DETECTED
- DUPLICATE_DETECTED → APPROVED or DENIED
- APPROVED → INGESTING
- INGESTING → INGESTED or ERROR
- INGESTED → DEACTIVATED

Every transition MUST:
- Use optimistic locking (state_version field)
- Log to governance_events table
- Reject invalid transitions with clear error messages

Reference: GOVERNANCE_FLOW_v1.0.md Section 3
```

### Section 5: Git as Memory - Mandatory Workflow
```markdown
## Git as Memory - Mandatory Workflow

### Before Each Implementation Task

1. Read the relevant authoritative documents for this task
2. Verify understanding of requirements and constraints
3. Check for existing code that might conflict
4. Plan the implementation approach

### After Each Implementation Task

1. Verify implementation matches specification exactly
2. Test the deliverable (health checks, migrations, etc.)
3. Commit with structured message (see format below)
4. Document any blockers or decisions made

### Required Commit Message Format

```
[PHASE0-INIT-XXX] Short description

Why:
- Reasoning for this implementation
- Which acceptance criteria this satisfies
- Any decisions made or blockers encountered

Aligned Docs:
- DATABASE_SCHEMA_v1.0.md Section X
- REQUIREMENTS_v1.0.md FR-00X
- ACCEPTANCE_CRITERIA_v1.0.md Phase 0
```

**Task ID Convention:**
- `PHASE0-INIT-001` - Database migration tooling setup
- `PHASE0-INIT-002` - Database schema creation
- `PHASE0-INIT-003` - Docker Compose configuration
- `PHASE0-INIT-004` - Transfer Station initialization
- `PHASE0-INIT-005` - Environment variable wiring
- `PHASE0-INIT-006` - Health check implementation
- `PHASE0-INIT-007` - Governance validation logic
```

### Section 6: Forbidden Behavior
```markdown
## Forbidden Behavior

You MUST NOT:

1. **Skip Migration Tooling Decision** - Never assume which tool to use
2. **Create Synthetic Test Data** - Use only real files placed in Transfer_Station
3. **Bypass Health Checks** - Every service must implement health endpoint
4. **Ignore Startup Order** - Workers cannot start before nexus_db and nexus_api healthy
5. **Modify Specifications** - Never change authoritative documents
6. **Implement Ingestion Logic** - Phase 0 is infrastructure only
7. **Use External Embedding APIs** - Must use local sentence-transformers model
8. **Skip Database Constraints** - All foreign keys must have ON DELETE CASCADE
9. **Implement Partial Solutions** - All Phase 0 deliverables must be complete
10. **Skip Testing** - All code must be tested inside Docker containers
```

### Section 7: Implementation Task Breakdown
```markdown
## Implementation Task Breakdown

### Task 1: Database Migration Tooling Decision (BLOCKER)
**Task ID:** PHASE0-INIT-001
**Dependencies:** None
**Deliverables:**
- Decision on Alembic, Flyway, or custom scripts
- Migration tooling setup and configuration
- Initial migration file structure
**Acceptance:** Migration tool runs successfully, rollback tested

### Task 2: Database Schema Provisioning
**Task ID:** PHASE0-INIT-002
**Dependencies:** PHASE0-INIT-001 complete
**Deliverables:**
- Migration files for all 12+ tables
- Foreign key constraints with CASCADE rules
- Indexes (B-tree, GIN, HNSW vector)
- Optimistic locking (state_version field)
**Acceptance:** Migrations apply cleanly, rollback works, schema matches DATABASE_SCHEMA_v1.0.md exactly

### Task 3: Docker Compose Configuration
**Task ID:** PHASE0-INIT-003
**Dependencies:** PHASE0-INIT-002 complete
**Deliverables:**
- docker-compose.yml with all 8 services
- Correct startup order with health check dependencies
- Environment variable references
- Volume mounts (Transfer_Station)
**Acceptance:** Docker Compose starts successfully, services start in correct order, health checks pass

### Task 4: Transfer Station Initialization
**Task ID:** PHASE0-INIT-004
**Dependencies:** PHASE0-INIT-003 complete
**Deliverables:**
- Directory structure creation script (idempotent)
- Volume mount verification
- Access permissions validation
**Acceptance:** Directory structure exists, mounted correctly, accessible to all containers

### Task 5: Environment Variable Configuration
**Task ID:** PHASE0-INIT-005
**Dependencies:** PHASE0-INIT-003 complete
**Deliverables:**
- .env.example template with all required variables
- Documentation of required vs. optional variables
- Default values where applicable
**Acceptance:** All services can read required environment variables, no missing vars

### Task 6: Health Check Implementation
**Task ID:** PHASE0-INIT-006
**Dependencies:** PHASE0-INIT-002, PHASE0-INIT-004 complete
**Deliverables:**
- Health endpoint implementation for all services
- Database connectivity verification
- Transfer Station mount verification
- Tool version verification
**Acceptance:** All health checks pass, startup order enforced, dependencies validated

### Task 7: Governance State Validation
**Task ID:** PHASE0-INIT-007
**Dependencies:** PHASE0-INIT-002 complete
**Deliverables:**
- State transition validation logic
- Optimistic locking implementation
- Governance event logging
- Test case T-ING-001 implementation
**Acceptance:** All allowed transitions pass, illegal transitions rejected, optimistic locking works, T-ING-001 passes
```

### Section 8: Completion Criteria
```markdown
## Completion Criteria

Phase 0 is complete when ALL of the following pass:

### Infrastructure
- ✅ Docker Compose starts all services successfully
- ✅ Services start in correct order (nexus_db first, workers last)
- ✅ All health checks pass
- ✅ Transfer Station directory structure exists and is accessible

### Database
- ✅ All 12+ tables created with correct schemas
- ✅ All indexes created (B-tree, GIN, HNSW)
- ✅ All foreign keys have ON DELETE CASCADE
- ✅ pgvector extension enabled (384-dimension vectors)
- ✅ Database migrations are idempotent and rollback-capable

### Environment
- ✅ All required environment variables documented in .env.example
- ✅ All services can read configuration
- ✅ Tool versions match TOOL_VERSIONS_v1.0.md minimums

### Governance
- ✅ State transition validation logic implemented
- ✅ Optimistic locking works (state_version field)
- ✅ Governance events logged for all transitions
- ✅ Test case T-ING-001 passes

### Acceptance Gates (from ACCEPTANCE_CRITERIA_v1.0.md)
- ✅ Repo structure exists
- ✅ Docker Compose starts successfully
- ✅ Governance models validate allowed state transitions

**Gating Principle:** Phase 0 must be 100% complete before Phase 1 can begin. Partial completion is not acceptable.
```

### Section 9: Begin
```markdown
## Begin

Before starting implementation:

1. Confirm you have read all 13 authoritative documents listed above
2. Ask user which database migration tool to use (if not already specified)
3. Verify understanding of Phase 0 scope (infrastructure only, no ingestion logic)
4. Begin with PHASE0-INIT-001 (migration tooling setup)

After receiving user confirmation, proceed with implementation following the 7-task breakdown above.

---

**This prompt is versioned. Any modification requires a version bump and changelog entry.**
```

---

## 3. Critical Decision Points

### 3.1 Database Migration Tooling (BLOCKER)

**Decision Required:** Which database migration tool should be used?

**Options:**

| Tool | Pros | Cons | Recommendation |
|------|------|------|----------------|
| **Alembic** | Python-native, SQLAlchemy integration, autogeneration | Requires SQLAlchemy models | ✅ **RECOMMENDED** for Python projects |
| **Flyway** | Database-agnostic, mature, Java ecosystem | JVM dependency, less Python integration | Use if multi-language environment |
| **Custom Scripts** | Simple, project-specific, no dependencies | Manual rollback, no autogen | Use only if minimal complexity |

**Recommendation:** Use **Alembic** for consistency with Python-based architecture.

### 3.2 Health Check Implementation

**Decision Required:** Should health checks be simple or comprehensive?

**Options:**
- **Simple:** Database connectivity only
- **Comprehensive:** Database + Transfer Station + Environment + Tool versions

**Recommendation:** **Comprehensive** health checks to catch configuration issues early.

### 3.3 Transfer Station Path

**Decision Required:** Should Transfer_Station path be hard-coded or configurable?

**Options:**
- **Hard-coded:** `E:\Transfer_Station` (Windows-specific)
- **Configurable:** Environment variable `TRANSFER_STATION_PATH`

**Recommendation:** **Configurable** via environment variable with `E:\Transfer_Station` as default for Windows.

---

## 4. Authoritative Documents Referenced

The prompt MUST require reading these 13 documents:

1. ARCHITECTURE_v1.0.md
2. INGESTION_ARCHITECTURE_v1.0.md
3. DATABASE_SCHEMA_v1.0.md
4. DATABASE_CONSTRAINTS_v1.0.md
5. TRANSACTION_MODEL_v1.0.md
6. DEPLOYMENT_v1.0.md
7. TOOL_VERSIONS_v1.0.md
8. GOVERNANCE_FLOW_v1.0.md
9. REQUIREMENTS_v1.0.md
10. ACCEPTANCE_CRITERIA_v1.0.md
11. TEST_PLAN_v1.0.md
12. TEST_CASES_v1.0.md
13. INGESTION_DEPENDENCIES_v1.0.md

---

## 5. Implementation Checklist

When writing PHASE_0_INITIALIZATION_PROMPT_v1.0.md:

- [x] Include all 9 sections (Header, Authoritative Docs, Scope, Rules, Git Protocol, Forbidden, Tasks, Completion, Begin)
- [x] List all 13 mandatory documents in correct order
- [x] Require migration tooling decision before proceeding
- [x] Specify exact Docker Compose startup order
- [x] Define Transfer Station directory structure
- [x] List all required environment variables
- [x] Specify health check requirements
- [x] Define governance state validation rules
- [x] Include 7-task implementation breakdown
- [x] Define completion criteria matching ACCEPTANCE_CRITERIA_v1.0.md
- [x] Use consistent Git commit format (PHASE0-INIT-XXX)
- [x] Include "This prompt is versioned" footer

---

## 6. Testing Strategy

### 6.1 Verification After Writing Prompt

After writing PHASE_0_INITIALIZATION_PROMPT_v1.0.md, verify:

1. **Completeness:** All sections from existing prompts are present
2. **Consistency:** Git-as-memory protocol matches other prompts
3. **Traceability:** All FR-001, FR-002, FR-003 and T-ING-001 referenced
4. **Coverage:** All Phase 0 acceptance criteria addressable
5. **Clarity:** Migration tooling blocker is explicit

### 6.2 Validation Checklist

- [x] Prompt follows same structure as INGESTION_IMPLEMENTATION_AGENT_PROMPT_v1.0.md
- [x] All authoritative documents are listed
- [x] Scope of authority clearly defines MAY/MAY NOT
- [x] Forbidden behavior section prevents common mistakes
- [x] Implementation tasks are sequential and dependency-ordered
- [x] Completion criteria match ACCEPTANCE_CRITERIA_v1.0.md Phase 0
- [x] Git commit format is consistent with existing prompts

---

## 7. Expected Outcomes

After PHASE_0_INITIALIZATION_PROMPT_v1.0.md is written and used:

**Immediate Outcomes:**
- Database schema created and migrated
- Docker Compose configuration functional
- Transfer Station directory structure exists
- Environment variables documented
- Health checks passing

**Enables:**
- Phase 1: Source Discovery & Approval (can now scan Transfer_Station)
- Phase 2: Extraction & Artifact Generation (database ready for manifests)
- All subsequent phases (foundation established)

**Blocks Removed:**
- Phase 0 prompt no longer missing
- Database initialization no longer undefined
- Docker orchestration no longer ambiguous

---

## 8. Estimated Effort

**Writing PHASE_0_INITIALIZATION_PROMPT_v1.0.md:**
- Estimated time: 2-3 hours
- File size: 3-4 KB (similar to existing prompts)
- Sections: 9 major sections
- Task breakdown: 7 sequential tasks

**Using the prompt to implement Phase 0:**
- Estimated time: 4-6 hours (after migration tool decision)
- Deliverables: Docker Compose, migrations, health checks, governance validation
- Testing: 1-2 hours (T-ING-001 implementation and verification)

**Total Phase 0 effort:** 7-11 hours from prompt creation to acceptance

---

## 9. Risk Mitigation

### Risk 1: Migration Tool Undecided
**Mitigation:** Prompt explicitly stops and asks user for decision before proceeding

### Risk 2: Docker Startup Order Not Enforced
**Mitigation:** Prompt requires `depends_on` with `condition: service_healthy`

### Risk 3: Health Checks Incomplete
**Mitigation:** Prompt specifies all verification requirements (DB, volume, env, versions)

### Risk 4: Governance Validation Missing
**Mitigation:** Prompt includes explicit task (PHASE0-INIT-007) for state transition validation

### Risk 5: Transfer Station Permissions
**Mitigation:** Prompt requires idempotent directory creation and permission validation

---

## 10. Next Steps After Approval

1. ✅ Write PHASE_0_INITIALIZATION_PROMPT_v1.0.md to `docs/implementation/`
2. ✅ Copy this task plan to `docs/task_plans/PHASE_0_INITIALIZATION_TASK_PLAN_v1.0.md`
3. Ask user for database migration tool decision (Alembic recommended)
4. Proceed with Phase 0 implementation using the new prompt
5. Validate Phase 0 acceptance criteria before moving to Phase 1

---

## Conclusion

This task plan provides a comprehensive blueprint for creating PHASE_0_INITIALIZATION_PROMPT_v1.0.md. The prompt will establish the critical foundation that blocks all subsequent implementation work. By following existing prompt patterns and addressing all Phase 0 requirements, deliverables, and acceptance criteria, the prompt will enable successful bootstrapping of the Nexus Core MVP1 project infrastructure.

**Critical Success Factor:** The prompt MUST stop and ask for migration tooling decision before implementation can proceed. This blocker is explicitly handled in Section 4 (Core Implementation Rules).
