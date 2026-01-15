# FAULT_RECOVERY_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** INGESTION_ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines **fault recovery and retry policies** for MVP1.

---

## 2. Retry Policy (Default)

- Maximum retries: 3
- Backoff: exponential (1s, 4s, 9s)
- After max retries: set status to `ERROR`

---

## 3. Network Failure Handling

- Detect transient network failures (timeouts, connection resets)
- Apply default retry policy
- If retries exhausted, log and set status to `ERROR`

---

## 4. Worker Crash Recovery

- On worker crash, the job is re-queued once
- If job fails again, set status to `ERROR`

---

## 5. Embedding Model Failures

- No fallback model is used in MVP1
- If the embedding model fails or is unavailable, apply the default retry policy
- If retries are exhausted, set status to `ERROR` and require admin retry

---

## 6. Change Control

This document is versioned.
- Any change requires a version bump
