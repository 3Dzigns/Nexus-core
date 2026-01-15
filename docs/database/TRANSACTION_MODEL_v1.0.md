# TRANSACTION_MODEL_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** INGESTION_ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines **transaction boundaries** for ingestion and deactivation.

---

## 2. Transaction Scope (Per Stage)

Each pipeline stage executes in its **own transaction**:
1. Normalization
2. Enrichment
3. Chunking
4. Embedding and storage
5. Indexing
6. Validation reporting

If a stage fails, the transaction must be rolled back and ingestion moves to `ERROR`.

---

## 3. Deactivation Atomicity

Deactivation must be a **single atomic transaction**:
- Update source status to `DEACTIVATED`
- Soft-disable all dependent rows (`active = false`)
- Insert governance event `REMOVAL_REQUEST`

If any part fails, the transaction must be rolled back.

---

## 4. Change Control

This document is versioned.
- Any change requires a version bump
