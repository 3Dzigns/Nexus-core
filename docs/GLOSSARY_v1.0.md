# GLOSSARY_v1.0.md
**Version:** v1.0
**Applies To:** Nexus Core MVP1

---

## 1. Purpose

This document defines the **authoritative terminology** used across Nexus Core MVP1.

---

## 2. Terms

**active_game_id**  
Server-side session context identifying the active game for scoped queries.

**artifact**  
Any stored file produced by ingestion stages (manifests, chunks, reports, assets).

**chunk**  
A unit of text derived from a source, stored with embeddings and metadata.

**chunk_id**  
Deterministic identifier for a chunk: `{doc_id}::{tool_id}::{chunk_sha256[:16]}`.

**chunk_sha256**  
SHA-256 hash of the chunk text content.

**deactivation**  
Soft-disablement of a source and its derived data (not deletion).

**doc_id**  
Human-identifiable identifier derived from filename and SHA-256.

**duplicate_detected**  
Governance status indicating a duplicate source was found.

**governance status**  
State of a source in the approval and ingestion lifecycle (e.g., PENDING_APPROVAL).

**manifest (raw)**  
Tool-specific extraction output before normalization.

**manifest (normalized)**  
Canonical schema created from raw tool outputs.

**manifest (enriched)**  
Normalized manifest augmented with rule-based metadata.

**owner_user_id**  
Primary owner of a source, stored in the sources table.

**source**  
A file discovered in the transfer station and governed for ingestion.

**source_links**  
Secondary access grants for a source across users or games.

**tool_id**  
Identifier for the extraction tool (e.g., docling, unstructured).

**tool_version**  
Semver string identifying the tool release used to produce artifacts.

**transfer station**  
The staging filesystem used for sources and artifacts (`/transfer_station/`).

---

## 3. Change Control

This document is versioned.
- Any change requires a version bump
