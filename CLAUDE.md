# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

**GitHub**: https://github.com/3Dzigns/Nexus-core.git

This is a clean repository starting from comprehensive specification documents.

## Project Overview

**Nexus Core MVP1** is a TTRPG (Tabletop RPG) knowledge ingestion and AI query system. The system ingests RPG source material (PDFs, documents), processes them through dual extraction pipelines, and provides AI-assisted querying with strict role-based access control.

**Critical Constraint**: This is a planning and architecture project. No implementation code exists yet. All code is governed by comprehensive specification documents.

## System Architecture

### Core Principles

1. **Governance First**: No data enters without explicit admin approval
2. **Deterministic Before AI**: Prefer deterministic logic over AI where possible
3. **Separation of Concerns**: Ingestion ≠ Retrieval ≠ Synthesis
4. **Dual Extraction**: Both Docling and Unstructured extractors run independently; outputs are never merged in MVP1
5. **Testability**: All tests run inside Docker containers only

### Architecture Components

- **Ingestion Subsystem**: Source discovery, governance, dual extraction (Docling + Unstructured), normalization, enrichment, chunking
- **Governance & Validation**: State machine enforcement (Pydantic), approval workflows, post-ingestion certification
- **Storage & Indexing**: Postgres + pgvector for embeddings, full-text search (FTS), dual chunk sets
- **Query Orchestrator**: Complexity classification, keyword/vector/hybrid retrieval, role/context/scope enforcement
- **User Interfaces**: Unified Player/GM UI (role-driven), separate Admin UI

### Deployment Environment

- **Runtime**: Docker Desktop on Windows
- **Orchestration**: Docker Compose
- **Host Volume**: `E:\Transfer_Station` → `/transfer_station` (container mount)
- **Environment**: Single DEV/TEST combined (no production)

### Transfer Station Structure

```
Transfer_Station/
  sources/                 # dropzone for user files
  quarantine/              # denied sources
  artifacts/
    manifests/<doc_id>/    # raw, normalized, enriched manifests (dual)
    chunks/<doc_id>/       # docling_chunks.jsonl, unstructured_chunks.jsonl
    assets/<doc_id>/       # extracted images
    reports/<doc_id>/      # validation reports (md + json)
  logs/ingestion/
```

### Document Identity

- **doc_id format**: `<original_filename>__<sha256>` (max 120 chars, sanitized)
- **Allowed characters**: `A-Z a-z 0-9 . _ -`
- All artifacts are traceable via `doc_id` and `source_sha256`

## Ingestion Pipeline (Sequential Phases)

1. **Source Discovery**: Scan `/transfer_station/sources/`, compute SHA-256
2. **Governance Record**: Create record with status `PENDING_APPROVAL`
3. **Admin Approval**: Explicit approve/deny via Admin UI
4. **Dual Extraction**: Run Docling AND Unstructured (both required)
5. **Normalization**: Convert tool outputs to canonical internal schema (separate per tool)
6. **Enrichment**: Content-aware metadata (deterministic, no per-chunk LLM)
7. **Chunking**: Create dual chunk sets (Docling + Unstructured)
8. **Embedding & Storage**: Store in Postgres with pgvector, create FTS indexes
9. **Validation & Certification**: Validator must PASS before marking `INGESTED`

### Governance State Machine

States: `DISCOVERED` → `PENDING_APPROVAL` → `APPROVED` → `INGESTING` → `INGESTED` | `ERROR` | `DEACTIVATED`

- Illegal transitions are prevented via Pydantic
- Duplicate SHA-256 detection requires admin decision
- Source file removal triggers automatic `DEACTIVATED` status (soft deactivation)

## Role & Context Enforcement

### Roles
- **Player**: Limited access, game-scoped only
- **GM**: Game ownership controls, access to GM-only sources
- **Admin**: Governance, validation, tier management

### Access Rules
- **Game Context**: Queries use only sources linked to that game
- **No Game Context**: Queries use only sources linked to user account
- **GM-Only Sources**: Accessible only to GM owner of linked game

## Database Schema (Key Tables)

- `sources`: Primary source records (doc_id, source_sha256, status, system_id, game_id, owner_user_id)
- `governance_events`: Immutable state transition log
- `duplicate_decisions`: Admin duplicate resolution
- `manifests`: Artifact metadata (tool_id, manifest_type, path)
- `chunks`: Dual chunk records (tool_id: docling|unstructured, active flag)
- `embeddings`: Vector embeddings per chunk (pgvector HNSW index)
- `fts_index`: Full-text search (tsvector + GIN index)
- `validation_reports`: Certification records (PASS/FAIL)
- `source_links`: Ownership and scope enforcement (USER|GAME, gm_only flag)
- `feedback`: Thumbs up/down per chunk (system-scoped ranking)

## Testing Rules (Non-Negotiable)

1. **Container-Only Execution**: All tests run inside Docker (including unit tests)
2. **No Synthetic Data**: Test sources placed manually in `/transfer_station/sources/`
3. **Mandatory Cleanup**: Scripts must restore environment to clean state
4. **Phase-Gated**: Tests execute according to phase boundaries (see PHASE_MAP_v1.0.md)

### PowerShell Test Scripts
- May invoke container commands
- Must NOT contain business logic
- Must NOT execute tests on host OS

## Development Commands

**Note**: No implementation exists yet. When code is implemented:

### Expected Container Commands
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f nexus_api
docker-compose logs -f nexus_ingestion_worker

# Run tests (inside containers)
docker exec nexus_api pytest /app/tests
docker exec nexus_validator pytest /app/tests

# Run validation
docker exec nexus_validator python -m validator --doc-id <doc_id>

# Database access
docker exec -it nexus_db psql -U nexus -d nexus_core

# Cleanup test data (via PowerShell invoking container commands)
# Script location: TBD during implementation
```

## Phase-Based Implementation Order

Implementation MUST proceed in strict phase order (no skipping):

0. **Project & Governance Foundations**: DB schema, governance state machine
1. **Source Discovery & Approval**: Filesystem scanning, admin approval workflow
2. **Extraction & Artifact Generation**: Docling + Unstructured integration, artifact preservation
3. **Normalization, Enrichment & Chunking**: Canonical schema, content-aware metadata, dual chunk sets
4. **Storage, Indexing & Validation**: Postgres persistence, pgvector indexes, certification
5. **Deactivation & Removal**: Soft deactivation logic, removal detection
6. **Query & Action Safety**: Orchestration, scope enforcement, role checks
7. **Feedback, Limits & UI Enforcement**: Feedback loops, tier limits

## Authoritative Documents

All implementation must align with versioned specifications in `docs/`:

### Architecture
- `ARCHITECTURE_v1.0.md`: System-wide architecture
- `INGESTION_ARCHITECTURE_v1.0.md`: Authoritative ingestion specification
- `UI_WIREFRAME_SPEC_v1.0.md`: UI component specifications

### Requirements & Acceptance
- `REQUIREMENTS_v1.0.md`: Testable functional/non-functional requirements (FR-001 to FR-041, NFR-001 to NFR-009)
- `ACCEPTANCE_CRITERIA_v1.0.md`: Phase acceptance gates

### Governance & Contracts
- `GOVERNANCE_FLOW_v1.0.md`: State machine and transition rules
- `ARTIFACT_CONTRACT_v1.0.md`: Mandatory artifact types and structure
- `PHASE_MAP_v1.0.md`: Phase-to-requirement-to-test mapping
- `CLEANUP_STRATEGY_v1.0.md`: Deactivation and cleanup semantics

### Testing & Validation
- `TEST_PLAN_v1.0.md`: Testing strategy and execution rules
- `TEST_CASES_v1.0.md`: Concrete test case definitions
- `VALIDATION_PLAN_v1.0.md`: Post-ingestion certification requirements

### Data & API
- `DATABASE_SCHEMA_v1.0.md`: Postgres schema with pgvector
- `OPENAPI_v1.0.md`: API contract (FastAPI)
- `QUERY_POLICY_v1.0.md`: Query classification and routing
- `ACCESS_MATRIX_v1.0.md`: Role-based access control matrix

### Planning & Dependencies
- `INGESTION_DEPENDENCIES_v1.0.md`: Dependency chain and ordering
- `INGESTION_RISKS_v1.0.md`: Risk register

### Implementation Prompts
- `INGESTION_PLANNING_TASK_PROMPTS_v1.0.md`: Agent prompts for planning tasks
- `INGESTION_IMPLEMENTATION_AGENT_PROMPT_v1.0.md`: Implementation agent guidance
- `INGESTION_VALIDATION_AGENT_PROMPT_v1.0.md`: Validation agent guidance
- `POWERSHELL_TEST_RUNNER_AGENT_PROMPT_v1.0.md`: Test runner agent guidance

## Critical Implementation Rules

1. **Never Skip Governance**: All sources require explicit approval before processing
2. **Dual Extraction is Mandatory**: Both Docling and Unstructured must succeed; never merge outputs
3. **Artifacts Before State Transitions**: Write artifacts to disk before advancing governance state
4. **Validation is Required**: Source cannot be marked `INGESTED` without validator PASS
5. **Container-Only Testing**: No test execution on Windows host
6. **Idempotency**: Pipeline stages must be safe to retry without creating duplicates
7. **Soft Deactivation**: Never delete artifacts; use active flags and governance status
8. **Deterministic Enrichment**: No per-chunk LLM calls in MVP1
9. **Phase Order Enforcement**: No implementation out of phase sequence
10. **Traceability**: Every requirement (FR/NFR) must map to test cases

## Out of Scope for MVP1

- Graph reasoning or multi-step world state
- Automated billing/payments (tiers exist but no payment flow)
- Player-visible module content (concepts exist but pipeline deferred)
- Long-term NPC memory
- Cross-game state persistence
- Canonical merge of Docling + Unstructured outputs
- Performance optimization (targets deferred until production environment)

## Version Control

- All specification documents are versioned (v1.0 suffix)
- Any change to a spec requires version bump
- Changes must update CHANGELOG.md
- Specification changes require updates to affected tests and validation logic

## Getting Started (When Implementation Begins)

1. Read `ARCHITECTURE_v1.0.md` and `INGESTION_ARCHITECTURE_v1.0.md` first
2. Review `REQUIREMENTS_v1.0.md` for testable obligations
3. Check `PHASE_MAP_v1.0.md` to understand current phase boundaries
4. Consult `TEST_PLAN_v1.0.md` for testing strategy
5. Reference `ARTIFACT_CONTRACT_v1.0.md` for expected outputs
6. Follow phase order strictly (no skipping)
7. Write tests inside containers before implementing features
8. Run validation after every ingestion to certify correctness
