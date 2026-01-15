# MONITORING_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines **required metrics and alert thresholds** for MVP1.

---

## 2. Required Metrics

### 2.1 Ingestion
- `ingestion_jobs_total`
- `ingestion_jobs_failed_total`
- `ingestion_duration_seconds` (p50, p95)
- `validation_pass_total`
- `validation_fail_total`

### 2.2 Query
- `query_requests_total`
- `query_errors_total`
- `query_latency_seconds` (p50, p95)

### 2.3 System Health
- `db_connections_active`
- `db_errors_total`
- `worker_heartbeat_ok` (per worker)

---

## 3. Alert Thresholds (Baseline)

### 3.1 Critical
- API health check fails for 2 consecutive minutes
- Database unreachable for 1 minute
- Validation failure rate > 20% over 30 minutes

### 3.2 Warning
- Ingestion failure rate > 10% over 30 minutes
- Query p95 latency > 2 seconds over 15 minutes
- Worker heartbeat missing for 2 minutes

---

## 4. Logging Integration

All alerts must reference:
- service name
- correlation_id (if available)
- doc_id (if applicable)

---

## 5. Change Control

This document is versioned.
- Any change requires a version bump
