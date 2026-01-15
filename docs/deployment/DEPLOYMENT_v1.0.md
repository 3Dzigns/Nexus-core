# DEPLOYMENT_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines the **deployment, startup order, environment variables, and health checks** for MVP1.

---

## 2. Startup Order

1. `nexus_db` (Postgres + pgvector)
2. `nexus_api` (FastAPI)
3. `nexus_ingestion_worker`
4. `nexus_docling_worker`
5. `nexus_unstructured_worker`
6. `nexus_validator`
7. `nexus_ui`
8. `nexus_admin_ui`

Workers MUST wait for `nexus_api` and `nexus_db` to be healthy before starting jobs.

---

## 3. Required Environment Variables

### 3.1 Core
- `TRANSFER_STATION_PATH` (host path to Transfer_Station)
- `DATABASE_URL` (Postgres connection string)
- `INGESTION_WORKER_POLL_INTERVAL` (seconds, default 60)

### 3.2 Security
- `JWT_PUBLIC_KEY` (public key for JWT validation)
- `JWT_PRIVATE_KEY` (private signing key; API only)
- `JWT_ISSUER` (default: `nexus-core-api`)

### 3.3 Extraction Tools
- `DOCLING_VERSION`
- `UNSTRUCTURED_VERSION`

### 3.4 Embeddings
- `EMBEDDING_MODEL` (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `EMBEDDING_DIMENSIONS` (default: `384`)

---

## 4. Health Checks

Each service must expose a health endpoint:
- `nexus_api`: `GET /health`
- `nexus_ingestion_worker`: `/health`
- `nexus_docling_worker`: `/health`
- `nexus_unstructured_worker`: `/health`
- `nexus_validator`: `/health`

Health checks must verify:
- database connectivity
- transfer_station path mounted
- required environment variables present

---

## 5. Database Migrations

- Migrations must run before ingestion jobs start
- Migration failures block deployment

---

## 6. Change Control

This document is versioned.
- Any change requires a version bump
- Deployment changes MUST update compose and test scripts
