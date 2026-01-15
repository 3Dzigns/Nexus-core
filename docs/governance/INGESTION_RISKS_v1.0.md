# INGESTION_RISKS_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** INGESTION_ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document records **open questions, known risks, and deferred decisions** for ingestion in MVP1.
It forces explicit acknowledgment of uncertainty and scope boundaries.

---

## 2. Open Questions

- None identified at this time.

---

## 3. Known Risks

- **doc_id construction**: using `<original_filename>__<sha256>` risks invalid path characters or excessive length on Windows; a sanitization rule may be needed.
- **Artifact volume**: dual extractor outputs plus chunking can create large artifact trees; storage limits are not yet defined.
- **Manual approval bottleneck**: admin-gated retries and approvals can slow ingestion throughput during testing.

---

## 4. Deferred Decisions

- **doc_id sanitization**: allowed character set and max length are not yet specified.
- **Retention policy**: long-term retention limits for artifacts and reports are not defined in MVP1.

---

## 5. Not Addressed in MVP1

- Cross-game state persistence
- Graph reasoning or world-state inference
- Automated billing and payments
- Player-visible module content

---

## 6. Change Control

This document is versioned.
- Any change requires a version bump
- Risk changes MUST update affected plans if mitigation changes scope

