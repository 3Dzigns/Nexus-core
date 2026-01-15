# Nexus Core MVP1

A TTRPG (Tabletop RPG) knowledge ingestion and AI query system for intelligent rules lookup and character action resolution.

## Overview

Nexus Core ingests RPG source material (PDFs, documents), processes them through dual extraction pipelines, and provides AI-assisted querying with strict role-based access control. The system enforces governance-first principles, ensuring all content is explicitly approved before processing.

## Status

**Current Phase**: Planning and Architecture

This repository contains comprehensive specification documents that define the complete system architecture, requirements, and implementation contracts. No implementation code exists yet.

## Key Features

- **Dual Extraction Pipeline**: Parallel processing using Docling and Unstructured extractors
- **Governance-First Architecture**: Explicit admin approval required for all sources
- **Role-Based Access Control**: Player/GM/Admin roles with strict context enforcement
- **Vector + Full-Text Search**: Postgres with pgvector for semantic search and FTS
- **Docker-Native**: All services run in containers; tests execute in Docker only
- **Deterministic Processing**: Content-aware metadata enrichment without per-chunk LLM calls

## Architecture

### Core Components

- **Ingestion Subsystem**: Source discovery, governance, extraction, normalization, enrichment, chunking
- **Governance & Validation**: Pydantic-enforced state machine, approval workflows, certification
- **Storage & Indexing**: Postgres + pgvector, dual chunk sets, FTS indexes
- **Query Orchestrator**: Complexity classification, hybrid retrieval, scope enforcement
- **User Interfaces**: Unified Player/GM UI (role-driven), separate Admin UI

### Deployment

- **Runtime**: Docker Desktop on Windows
- **Orchestration**: Docker Compose
- **Database**: Postgres + pgvector
- **Environment**: Single DEV/TEST combined

## Documentation

All architecture and requirements are defined in versioned specification documents:

### Core Architecture
- `docs/architecture/ARCHITECTURE_v1.0.md` - System-wide architecture
- `docs/architecture/INGESTION_ARCHITECTURE_v1.0.md` - Authoritative ingestion specification

### Requirements
- `docs/requirements/REQUIREMENTS_v1.0.md` - Functional/non-functional requirements (FR-001 to FR-041)
- `docs/requirements/ACCEPTANCE_CRITERIA_v1.0.md` - Phase acceptance gates

### Testing
- `docs/testing/TEST_PLAN_v1.0.md` - Testing strategy and execution rules
- `docs/testing/TEST_CASES_v1.0.md` - Concrete test case definitions
- `docs/testing/VALIDATION_PLAN_v1.0.md` - Post-ingestion certification

### Data & API
- `docs/database/DATABASE_SCHEMA_v1.0.md` - Postgres schema with pgvector
- `docs/api/OPENAPI_v1.0.md` - FastAPI contract

### Governance
- `docs/governance/GOVERNANCE_FLOW_v1.0.md` - State machine and transitions
- `docs/governance/ARTIFACT_CONTRACT_v1.0.md` - Mandatory artifact types
- `docs/governance/PHASE_MAP_v1.0.md` - Phase-to-requirement-to-test mapping

See `CLAUDE.md` for comprehensive guidance on working with this codebase.

## Development Principles

1. **Governance First**: No data enters without explicit admin approval
2. **Deterministic Before AI**: Prefer deterministic logic over AI where possible
3. **Separation of Concerns**: Ingestion ≠ Retrieval ≠ Synthesis
4. **Dual Extraction**: Both Docling and Unstructured run independently; never merged in MVP1
5. **Container-Only Testing**: All tests run inside Docker (including unit tests)
6. **Phase-Gated Implementation**: Strict 8-phase sequential implementation order
7. **Artifacts Before State Transitions**: Write to disk before advancing governance state
8. **Soft Deactivation**: Never delete artifacts; use active flags
9. **Traceability**: Every requirement maps to test cases

## Implementation Phases

Implementation MUST proceed in strict order (no skipping):

0. **Project & Governance Foundations** - DB schema, governance state machine
1. **Source Discovery & Approval** - Filesystem scanning, admin approval workflow
2. **Extraction & Artifact Generation** - Docling + Unstructured integration
3. **Normalization, Enrichment & Chunking** - Canonical schema, content-aware metadata
4. **Storage, Indexing & Validation** - Postgres persistence, certification
5. **Deactivation & Removal** - Soft deactivation logic
6. **Query & Action Safety** - Orchestration, scope enforcement
7. **Feedback, Limits & UI Enforcement** - Feedback loops, tier limits

## Getting Started

When implementation begins:

1. Read `docs/architecture/ARCHITECTURE_v1.0.md` and `docs/architecture/INGESTION_ARCHITECTURE_v1.0.md`
2. Review `docs/requirements/REQUIREMENTS_v1.0.md` for testable obligations
3. Check `docs/governance/PHASE_MAP_v1.0.md` for current phase boundaries
4. Consult `docs/testing/TEST_PLAN_v1.0.md` for testing strategy
5. Reference `docs/governance/ARTIFACT_CONTRACT_v1.0.md` for expected outputs
6. Follow phase order strictly (no skipping)

## License

[To be determined]

## Contact

[To be determined]
