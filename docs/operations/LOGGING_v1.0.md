# LOGGING_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines the **structured logging standard** for MVP1.

---

## 2. Required Fields

Every log entry MUST include:
- `timestamp` (UTC, ISO 8601)
- `level` (DEBUG, INFO, WARN, ERROR)
- `service` (container name)
- `message`
- `correlation_id` (UUID v4)

When applicable, also include:
- `doc_id`
- `tool_id`
- `run_id`
- `event_type`

---

## 3. Correlation ID Rules

- Generated at API entry if not provided
- Propagated via `X-Correlation-Id` header
- Must be UUID v4 format

---

## 4. Error Logging

Errors MUST include:
- error category
- stack trace (if applicable)
- failed operation context

---

## 5. Change Control

This document is versioned.
- Any change requires a version bump
