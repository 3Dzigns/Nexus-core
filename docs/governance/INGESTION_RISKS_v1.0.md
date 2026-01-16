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

- **doc_id sanitization enforcement**: while the character set (`A-Z a-z 0-9 . _ -`) and max length (120 chars) are specified in CLAUDE.md, the implementation of sanitization logic and handling of non-conforming filenames is not yet defined.
- **Retention policy**: long-term retention limits for artifacts and reports are not defined in MVP1.

---

## 5. Not Addressed in MVP1

- Canonical merge of Docling + Unstructured into one manifest
- Cross-game state persistence
- Graph reasoning or world-state inference
- Automated billing and payments
- Player-visible module content

---

## 6. Change Control

This document is versioned.
- Any change requires a version bump
- Risk changes MUST update affected plans if mitigation changes scope

---

## 7. Planning Review & Completion

### Planning Tasks Completed

All ingestion planning tasks have been completed:

| Task | Commit | Document | Purpose |
|------|--------|----------|---------|
| ING-PLAN-000 | 3859fa0 | MEMORY_SUMMARY.md | Repository memory initialization |
| ING-PLAN-001 | 3227ab0 | PHASE_MAP_v1.0.md | Phase-to-requirement mapping with agent guidance |
| ING-PLAN-002 | 9e93165 | INGESTION_DEPENDENCIES_v1.0.md | Dependency order with source citations |
| ING-PLAN-003 | 20ff33f | GOVERNANCE_FLOW_v1.0.md | State transitions with verification |
| ING-PLAN-004 | 4f25325 | ARTIFACT_CONTRACT_v1.0.md | Artifact requirements with design rationale |
| ING-PLAN-005 | 29dc0d7 | VALIDATION_PLAN_v1.0.md | Validation checks with philosophy |
| ING-PLAN-006 | 97561b0 | CLEANUP_STRATEGY_v1.0.md | Cleanup rules with safety rationale |
| ING-PLAN-007 | (current) | INGESTION_RISKS_v1.0.md | Risk register and planning review |

### Cross-Document Consistency Review

All planning documents have been reviewed for contradictions:
- ✅ No conflicting state definitions
- ✅ No conflicting artifact requirements
- ✅ No conflicting dependency orders
- ✅ Consistent scope boundaries (MVP1 vs deferred)
- ✅ All documents include source citations per Git Memory Protocol

### Justification for Risk Assessment

Known risks are minimal because:
1. **Comprehensive Specification**: INGESTION_ARCHITECTURE_v1.0.md defines all components before implementation
2. **Explicit Constraints**: Non-negotiable rules prevent ambiguity
3. **Phase-Gated Approach**: Phase boundaries prevent scope creep
4. **Artifact-First Design**: Observable artifacts enable verification
5. **Governance Enforcement**: State machine prevents illegal transitions
6. **Test Repeatability**: Cleanup strategy ensures deterministic tests

Risks that remain are implementation-level details (e.g., sanitization logic, storage limits) that will be addressed during coding.

### Source Citations

| Section | Source Document | Reference |
|---------|-----------------|-----------|
| Open Questions (Section 2) | All planning commits | None identified after full review |
| Known Risks (Section 3) | CLAUDE.md, ARTIFACT_CONTRACT_v1.0.md | Document identity constraints |
| Deferred Decisions (Section 4) | CLAUDE.md, Database constraints | Sanitization enforcement |
| Not Addressed in MVP1 (Section 5) | MEMORY_SUMMARY.md, ARCHITECTURE_v1.0.md | MVP1 scope boundaries |
| Planning Review (Section 7) | All ING-PLAN commits | Planning task verification |

### Planning-Related Commits

- `895e6d9` - Initial commit: Nexus Core MVP1 specification documents
- `3859fa0` - [ING-PLAN-000] Initialize ingestion memory context
- `3227ab0` - [ING-PLAN-001] Add implementation agent guidance to phase map
- `9e93165` - [ING-PLAN-002] Add source citations to ingestion dependency graph
- `20ff33f` - [ING-PLAN-003] Add verification and source citations to governance flow
- `4f25325` - [ING-PLAN-004] Add design rationale and source citations to artifact contract
- `29dc0d7` - [ING-PLAN-005] Add validation philosophy and source citations
- `97561b0` - [ING-PLAN-006] Add safety rationale and source citations to cleanup strategy

