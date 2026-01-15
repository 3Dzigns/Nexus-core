# QUERY_POLICY_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines the **query classification and routing policy** for MVP1.
It enforces deterministic short-circuit behavior before any AI invocation.

---

## 2. Inputs

Query policy operates on:
- `query_text`
- `role` (PLAYER, GM, ADMIN)
- `game_id` (nullable, resolved from server-side session)
- `system_id` (nullable)
- available sources in scope

---

## 3. Classification Levels

1. **DIRECT**
   - Deterministic or trivial lookup
   - No synthesis required

2. **RETRIEVAL**
   - Requires retrieval and ranking
   - No synthesis required (return top results)

3. **SYNTHESIS**
   - Requires AI synthesis across multiple chunks

---

## 4. Routing Rules (Deterministic)

Apply in order:

0. **Scope validation**
   - Resolve scope (user or game) before any retrieval
   - Deny if scope is invalid or unauthorized

1. **No-scope rule**
   - If no sources are linked to the user/game scope, return a friendly "no authoritative sources" response.
   - Do not invoke AI.

2. **Direct command rule**
   - If the query matches a deterministic command (e.g., "list sources", "show active character"),
     execute locally and return.

3. **Single-chunk rule**
   - If a single chunk satisfies the query with high confidence (exact keyword match or exact title match),
     return the chunk without AI synthesis.

4. **Multi-chunk rule**
   - If multiple chunks are required or results are ambiguous, classify as SYNTHESIS and invoke AI.

---

## 5. Metadata Enrichment

If missing:
- Infer `system_id` from scoped sources
- Infer `game_id` from active session context
- Enforce role and ownership checks before retrieval

Enrichment must be logged with:
- `doc_id` set
- inferred fields
- decision path

---

## 6. Non-Negotiable Constraints

- AI is never invoked if a deterministic response is possible
- AI must not bypass scope or governance rules
- Query decisions must be auditable (logged with classification and rule path)

---

## 7. Policy Precedence

When policies conflict, enforcement order is:
1. Governance state rules
2. Access matrix (role and scope)
3. Query policy routing

Any denial at a higher-precedence layer blocks lower layers.

---

## 8. Change Control

This document is versioned.
- Any change requires a version bump
- Policy changes MUST update tests that assert routing behavior
