# ACCESS_MATRIX_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines the **role and context access matrix** for MVP1.
It formalizes what sources and actions are permitted per role and scope.

---

## 2. Roles

- **PLAYER**
- **GM**
- **ADMIN**

---

## 3. Contexts

- **Global** (no active game)
- **Game-scoped** (active game)

---

## 4. Source Visibility Rules

| Role | Global Context | Game Context | GM-only Sources |
|------|----------------|--------------|-----------------|
| PLAYER | User-linked sources only | Game-linked sources only | Denied |
| GM | User-linked sources only | Game-linked sources only | Allowed if GM is owner of the game |
| ADMIN | All sources (audit only) | All sources (audit only) | Allowed (audit only) |

---

## 5. Action Permissions

| Role | Governance Actions | Ingestion Actions | Query Actions |
|------|---------------------|------------------|---------------|
| PLAYER | None | None | Allowed within scope |
| GM | None | None | Allowed within scope |
| ADMIN | Approve, deny, retry, deactivation | Validation run | Allowed (audit only) |

---

Admin audit-only rules:
- Admin queries must be labeled audit-only in responses
- Admin queries must not be used to drive gameplay actions

## 6. Ownership Rules

- A source linked to a game is visible only within that game context.
- A source linked to a user is visible only to that user in global context.
- GM-only sources require both:
  - GM role
  - GM is the owner of the game

GM-only bypass prevention:
- If role is GM but not the game owner, GM-only sources are denied

---

## 7. Enforcement Requirements

- Role checks must be server-side
- Scope checks must be enforced before retrieval
- Any violation must be logged and denied

---

## 8. Change Control

This document is versioned.
- Any change requires a version bump
- Access changes MUST update scope enforcement tests
