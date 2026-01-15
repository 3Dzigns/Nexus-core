# JWT_SPEC_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** OPENAPI_v1.0.md

---

## 1. Token Structure

### 1.1 Standard Claims (RFC 7519)
- `iss` (issuer): "nexus-core-api"
- `sub` (subject): user_id (UUID string)
- `exp` (expiration): Unix timestamp
- `iat` (issued at): Unix timestamp
- `jti` (JWT ID): unique token identifier

### 1.2 Custom Claims
- `role`: "PLAYER" | "GM" | "ADMIN"
- `active_game_id`: game_id (UUID string, nullable)
- `games_owned`: [game_id] (array of UUIDs; for GMs)
- `tier`: "FREE" | "BASIC" | "PRO"

---

## 2. Example Token Payload

```json
{
  "iss": "nexus-core-api",
  "sub": "user-uuid-123",
  "role": "GM",
  "active_game_id": "game-uuid-456",
  "games_owned": ["game-uuid-456", "game-uuid-789"],
  "tier": "PRO",
  "exp": 1704067200,
  "iat": 1704063600,
  "jti": "token-uuid-abc"
}
```

---

## 3. Validation Rules

- Validate JWT signature (RS256)
- Reject expired tokens (`exp`)
- Reject tokens missing `role`
- Admin-only endpoints require role == `ADMIN`
- Game-scoped endpoints require `active_game_id`
- For GM role, `active_game_id` must be in `games_owned`
- `active_game_id` is set by the server-side session and must not be accepted from client input

---

## 4. Security Requirements

- Private signing key must be stored in environment variables
- Public key must be available to all services
- Tokens must be transmitted via `Authorization: Bearer` header over HTTPS

---

## 5. Change Control

This document is versioned.
- Any change requires a version bump
- Auth changes MUST update tests and OpenAPI references
