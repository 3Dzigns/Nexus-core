# ARCHITECTURE_v1.0

## 0. Purpose
This document defines the overall system architecture for Nexus Core MVP1. It explains how components fit together end-to-end, with ingestion as the foundational dependency and AI query serving as a controlled consumer of ingested data.

This document is descriptive, not aspirational. Anything not explicitly described here is out of scope for MVP1.

---

## 1. Architectural Principles

### 1.1 Governance First
- No data enters the system without governance
- All state transitions are explicit and enforced
- Deactivation is preferred over deletion

### 1.2 Deterministic Before AI
- Deterministic logic is always preferred over AI
- AI is used only where interpretation or synthesis is required
- AI never mutates authoritative state

### 1.3 Separation of Concerns
- Ingestion ≠ Retrieval ≠ Synthesis
- UI ≠ API ≠ Workers
- Player ≠ GM ≠ Game scopes are strictly separated

### 1.4 Testability and Observability
- Every step must be testable inside Docker
- All failures must be observable
- No silent retries without logs

---

## 2. High-Level System Overview

Nexus Core MVP1 consists of:

1. Source Ingestion Subsystem (authoritative)
2. Governance & Validation Subsystem
3. Storage & Indexing Subsystem
4. AI Query Orchestrator
5. User Interfaces (Player/GM UI, Admin UI)

The ingestion subsystem is a hard dependency for all others.

Governing specifications:
- OPENAPI_v1.0.md
- API_VERSIONING_v1.0.md
- JWT_SPEC_v1.0.md
- DATABASE_SCHEMA_v1.0.md
- DATABASE_CONSTRAINTS_v1.0.md
- TRANSACTION_MODEL_v1.0.md
- TOOL_VERSIONS_v1.0.md
- DEPLOYMENT_v1.0.md
- QUERY_POLICY_v1.0.md
- ACCESS_MATRIX_v1.0.md
- MONITORING_v1.0.md
- LOGGING_v1.0.md
- RETENTION_POLICY_v1.0.md
- FAULT_RECOVERY_v1.0.md

---

## 3. Deployment Architecture

### 3.1 Runtime Environment
- Docker Desktop on Windows
- Docker Compose for orchestration
- Single logical environment (DEV/TEST combined)

### 3.2 Containers (Logical)

- nexus_api  
  - FastAPI application  
  - Governance APIs  
  - Query orchestration APIs  

- nexus_ingestion_worker  
  - Directory scanning  
  - Job orchestration  

- nexus_docling_worker  
  - Docling extraction  

- nexus_unstructured_worker  
  - Unstructured extraction  

- nexus_validator  
  - Post-ingestion validation  

- nexus_db  
  - Postgres + pgvector  

- nexus_ui  
  - Single frontend container  
  - Player, GM, and Game HUDs rendered by role/context  
  - Theme switching handled client-side  

- nexus_admin_ui  
  - Separate admin-only frontend  

---

## 4. Shared Storage Architecture

### 4.1 Transfer Station
Host-mounted volume:
- E:\Transfer_Station → /transfer_station

Used for:
- Source intake
- Artifact persistence
- Cross-container exchange
- Validation reports

No container writes outside this volume for ingestion artifacts.

---

## 5. Ingestion Pipeline (Dependency Chain)

1. Source discovery
2. Governance record creation
3. Admin approval
4. Dual extraction (Docling + Unstructured)
5. Normalization
6. Metadata enrichment
7. Chunking
8. Embedding
9. Indexing
10. Validation & certification

Failure at any step halts progression.

Details are defined in INGESTION_ARCHITECTURE_v1.0.md.

---

## 6. Storage & Indexing

### 6.1 Primary Database
- Postgres
- pgvector for embeddings
- JSONB for metadata

### 6.2 Index Types
- B-tree (IDs, status, system)
- GIN (full-text search)
- pgvector (HNSW preferred)

### 6.3 Deactivation Semantics
- Records are soft-deactivated
- Retrieval filters exclude inactive records
- Historical inspection remains possible

---

## 7. AI Query Architecture

### 7.1 Query Flow

1. UI submits query + context
2. Orchestrator enriches request metadata (if missing), including active game from server session
3. Orchestrator classifies complexity
4. Non-AI resolver short-circuits if possible
5. Retrieval (keyword, vector, or hybrid)
6. Reranking
7. Synthesis
8. Feedback capture

AI never bypasses governance or scope rules.

---

## 8. Role & Context Separation

### 8.1 Roles
- Player
- GM
- Admin

### 8.2 Contexts
- Global (no game)
- Game-scoped

### 8.3 Enforcement
- Role alone is insufficient
- Ownership and context are always required

---

## 9. UI Architecture

### 9.1 Player / GM UI
- Unified UI container
- Role- and context-driven HUDs

### 9.2 Game Hub
- Game-scoped controls
- GM-only features gated by ownership

### 9.3 Admin UI
- Governance
- Tier management
- Validation review

---

## 10. Failure & Recovery Model
- Failures are logged
- Partial ingestion is visible
- Admin intervention required for retries
- No automatic destructive recovery

---

## 11. Out of Scope for MVP1
- Graph reasoning
- Long-term NPC memory
- Automated billing
- Player-visible modules
- Cross-game state sharing

---

## 12. Change Control
This document is versioned.
- Changes require version bump
- Architectural changes require ingestion compatibility review

---

## 13. Acceptance Statement
MVP1 architecture is considered valid when:
- Ingestion can be completed and certified
- Queries never escape allowed scope
- All UI actions respect governance and limits

This document, together with INGESTION_ARCHITECTURE_v1.0.md, defines the architectural contract for MVP1.

