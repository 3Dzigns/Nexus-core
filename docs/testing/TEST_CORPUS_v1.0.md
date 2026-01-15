# TEST_CORPUS_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** TEST_PLAN_v1.0.md

---

## 1. Purpose

This document defines the **standard test corpus** for MVP1 ingestion and validation.

---

## 2. Required Source Types

Minimum corpus must include:
- 1 native PDF (text-based)
- 1 scanned PDF (OCR required)
- 1 plain text file
- 1 image-only source (PNG or JPG)

## 3. Corpus Location

The canonical test corpus lives in `e:\Transfer_Station\sources`.

- Do not enumerate files in this document.
- Tests must read from this directory when sample data is required.
- Do not hard-code expected results derived from specific files.

---

## 4. Naming Rules

- Filenames may vary
- SHA-256 is authoritative
- Each corpus item must be tracked by `doc_id`

---

## 5. Change Control

This document is versioned.
- Any change requires a version bump
