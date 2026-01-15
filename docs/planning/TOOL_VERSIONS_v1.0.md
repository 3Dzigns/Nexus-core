# TOOL_VERSIONS_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** INGESTION_ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines **minimum supported versions** for MVP1 tooling and runtime dependencies.
Exact versions may vary within the allowed ranges, but must not fall below these minimums.

---

## 2. Minimum Versions

### Extraction Tools
- **Docling:** >= 1.0.0
- **Unstructured:** >= 0.10.0

### Database
- **PostgreSQL:** >= 14.0
- **pgvector extension:** >= 0.5.0

### Runtime
- **Python:** >= 3.11

### Embedding Model
- **Model:** sentence-transformers/all-MiniLM-L6-v2
- **Dimensions:** 384
- **Provider:** Local model (no external API calls)

### Container Base Images (Minimum)
- python:3.11-slim
- postgres:14-alpine (with pgvector extension)

---

## 3. tool_version Field Format

`tool_version` must follow:
```
{name}/{semver}
```

Example:
```
docling/1.2.3
```

---

## 4. Compatibility Rules

- If any tool version is below minimum, ingestion MUST fail validation.
- Tool version changes MUST be recorded in the CHANGELOG.

---

## 5. Change Control

This document is versioned.
- Any change requires a version bump
- Version changes MUST update validation and deployment docs
