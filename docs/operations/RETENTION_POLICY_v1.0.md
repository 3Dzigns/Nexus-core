# RETENTION_POLICY_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines **artifact and report retention** for MVP1.

---

## 2. Retention Rules

- Ingestion artifacts are retained indefinitely by default.
- Validation reports are retained indefinitely by default.
- Deactivation does not delete artifacts.
- Admin removal is the only approved path for deletion.

---

## 3. Test Data Retention

- Test artifacts and reports are removed by cleanup scripts.
- Cleanup must be scoped to test `doc_id`s only.

---

## 4. Change Control

This document is versioned.
- Any change requires a version bump
