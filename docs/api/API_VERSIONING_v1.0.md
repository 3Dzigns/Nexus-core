# API_VERSIONING_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** OPENAPI_v1.0.md

---

## 1. Purpose

This document defines the **API versioning strategy** for MVP1.

---

## 2. Versioning Mechanism

- Clients MUST send `X-Api-Version` header.
- MVP1 version value: `1`.
- Requests without the header MUST be rejected with `400`.

---

## 3. Deprecation Policy

- New versions will be introduced by incrementing the header value.
- Old versions remain supported for a minimum of 90 days.

---

## 4. Out-of-Scope

- GraphQL is out of scope for MVP1.

---

## 5. Change Control

This document is versioned.
- Any change requires a version bump
