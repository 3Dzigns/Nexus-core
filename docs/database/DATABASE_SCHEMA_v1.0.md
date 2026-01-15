# DATABASE_SCHEMA_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** INGESTION_ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines the **logical database schema** for Nexus Core MVP1.
It specifies required tables, key fields, and relationships to meet ingestion, validation, and query requirements.

---

## 2. Core Entities

### 2.1 sources

Primary record for each ingested document.

**Primary Key:** `doc_id`

**Fields (required):**
- `doc_id` (text, format `<original_filename>__<sha256>`, max 120 chars, sanitized)
- `source_sha256` (text, unique)
- `original_filename` (text)
- `current_path` (text)
- `status` (text enum: DISCOVERED, PENDING_APPROVAL, DUPLICATE_DETECTED, APPROVED, DENIED, INGESTING, INGESTED, ERROR, DEACTIVATED)
- `state_version` (integer, optimistic lock counter)
- `first_seen_at` (timestamp)
- `updated_at` (timestamp)
- `system_id` (text, nullable)
- `game_id` (text, nullable)
- `owner_user_id` (text, NOT NULL)

Ownership rules:
- `owner_user_id` is set on approval
- `game_id` is NULL for user-owned sources and set for game-owned sources

**Indexes:**
- unique index on `source_sha256`
- index on `status`
- index on `system_id`
- index on `game_id`
- index on `owner_user_id`

**Constraints:**
- `doc_id` must match allowed characters `A-Z a-z 0-9 . _ -`
- `owner_user_id` must be set on approval
- `state_version` must increment on every state transition

---

### 2.2 governance_events

Immutable event log for governance state transitions.

**Primary Key:** `event_id` (uuid)

**Fields (required):**
- `event_id` (uuid)
- `doc_id` (text, FK -> sources.doc_id)
- `from_status` (text)
- `to_status` (text)
- `event_type` (text enum: STATUS_CHANGE, REMOVAL_REQUEST)
- `triggered_by` (text)
- `triggered_at` (timestamp)
- `metadata_json` (jsonb)

---

### 2.3 duplicate_decisions

Admin decisions for duplicate detection.

**Primary Key:** `doc_id`

**Fields (required):**
- `doc_id` (text, FK -> sources.doc_id)
- `decision` (text enum: IGNORE_DUPLICATE, ALLOW_SEPARATE_INSTANCE)
- `decided_by` (text)
- `decided_at` (timestamp)

---

## 3. Artifact Metadata

### 3.1 manifests

Metadata about manifests stored on disk.

**Primary Key:** `manifest_id` (uuid)

**Fields (required):**
- `manifest_id` (uuid)
- `doc_id` (text, FK -> sources.doc_id)
- `tool_id` (text enum: docling, unstructured)
- `manifest_type` (text enum: raw, normalized, enriched, original_source)
- `path` (text)
- `run_id` (text)
- `created_at` (timestamp)

**Indexes:**
- index on `doc_id`
- index on `tool_id`
- index on `manifest_type`

**Constraints:**
- One `original_source` manifest is required per `doc_id`

---

### 3.2 chunks

Chunk records for retrieval.

**Primary Key:** `chunk_id` (text)

**Fields (required):**
- `chunk_id` (text)
- `doc_id` (text, FK -> sources.doc_id)
- `tool_id` (text enum: docling, unstructured)
- `chunk_text` (text)
- `chunk_sha256` (text)
- `section_path` (text, nullable)
- `content_type` (text, nullable)
- `system_id` (text, nullable)
- `chunk_index` (integer)
- `active` (boolean)
- `metadata_json` (jsonb)
- `created_at` (timestamp)

**Indexes:**
- index on `doc_id`
- index on `tool_id`
- index on `system_id`
- index on `active`

**Constraints:**
- UNIQUE(doc_id, tool_id, chunk_sha256)

---

### 3.3 embeddings

Vector embeddings per chunk.

**Primary Key:** `chunk_id` (text, FK -> chunks.chunk_id)

**Fields (required):**
- `chunk_id` (text)
- `embedding` (vector(384))
- `created_at` (timestamp)

**Indexes:**
- vector index on `embedding` (HNSW preferred)

---

### 3.4 fts_index

Full-text search index support.

**Primary Key:** `chunk_id` (text, FK -> chunks.chunk_id)

**Fields (required):**
- `chunk_id` (text)
- `tsv` (tsvector)

**Indexes:**
- GIN index on `tsv`

---

## 4. Validation

### 4.1 validation_reports

Metadata for validation reports on disk.

**Primary Key:** `report_id` (uuid)

**Fields (required):**
- `report_id` (uuid)
- `doc_id` (text, FK -> sources.doc_id)
- `run_id` (text)
- `status` (text enum: PASS, FAIL)
- `report_path` (text)
- `report_json` (jsonb)
- `created_at` (timestamp)

**report_json schema (required fields):**
- `doc_id`
- `run_id`
- `status`
- `validator_version`
- `checks` (array of check results with pass/fail)
- `failed_checks` (array)
- `artifact_paths` (array)
- `created_at`

---

## 5. Query and Feedback

### 5.1 feedback

User feedback per chunk.

**Primary Key:** `feedback_id` (uuid)

**Fields (required):**
- `feedback_id` (uuid)
- `doc_id` (text, FK -> sources.doc_id)
- `chunk_id` (text, FK -> chunks.chunk_id)
- `rating` (text enum: UP, DOWN)
- `user_id` (text)
- `created_at` (timestamp)

**Indexes:**
- index on `chunk_id`
- index on `user_id`

---

### 5.2 tier_limits

Tier limit definitions.

**Primary Key:** `tier` (text)

**Fields (required):**
- `tier` (text enum: FREE, BASIC, PRO)
- `max_sources` (integer)
- `max_active_sources` (integer)
- `max_games` (integer)
- `max_storage_mb` (integer)

---

### 5.3 account_tiers

Assigned tier per user.

**Primary Key:** `user_id` (text)

**Fields (required):**
- `user_id` (text)
- `tier` (text enum: FREE, BASIC, PRO)
- `assigned_at` (timestamp)

---

## 6. Access and Scope

### 6.1 source_links

Additional access grants beyond primary ownership.

**Primary Key:** `link_id` (uuid)

**Fields (required):**
- `link_id` (uuid)
- `doc_id` (text, FK -> sources.doc_id)
- `scope_type` (text enum: USER, GAME)
- `owner_user_id` (text, nullable)
- `game_id` (text, nullable)
- `gm_only` (boolean)

Access logic:
- A user can access a source if:
  - `sources.owner_user_id = user_id`, OR
  - a `source_links` row exists for that user or game

**Indexes:**
- index on `doc_id`
- index on `owner_user_id`
- index on `game_id`

---

## 7. Change Control

This document is versioned.
- Any change requires a version bump
- Schema changes MUST update validation logic and tests

Refer to DATABASE_CONSTRAINTS_v1.0.md for required FK cascade rules.
