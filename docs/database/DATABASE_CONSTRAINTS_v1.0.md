# DATABASE_CONSTRAINTS_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** DATABASE_SCHEMA_v1.0.md

---

## 1. Purpose

This document defines **foreign key and cascade rules** required to prevent orphaned data.

---

## 2. Cascade Rules (Required)

- `manifests.doc_id` -> `sources.doc_id` ON DELETE CASCADE
- `chunks.doc_id` -> `sources.doc_id` ON DELETE CASCADE
- `embeddings.chunk_id` -> `chunks.chunk_id` ON DELETE CASCADE
- `fts_index.chunk_id` -> `chunks.chunk_id` ON DELETE CASCADE
- `validation_reports.doc_id` -> `sources.doc_id` ON DELETE CASCADE
- `feedback.doc_id` -> `sources.doc_id` ON DELETE CASCADE
- `feedback.chunk_id` -> `chunks.chunk_id` ON DELETE CASCADE
- `source_links.doc_id` -> `sources.doc_id` ON DELETE CASCADE
- `governance_events.doc_id` -> `sources.doc_id` ON DELETE CASCADE
- `duplicate_decisions.doc_id` -> `sources.doc_id` ON DELETE CASCADE

All FK updates use ON UPDATE RESTRICT.

---

## 3. Orphan Prevention

Any write that would create an orphan row MUST be rejected by the database.

---

## 4. Change Control

This document is versioned.
- Any change requires a version bump
