# OPENAPI_v1.0
**Version:** v1.0
**Applies To:** Nexus Core MVP1
**Authoritative Parent:** ARCHITECTURE_v1.0.md

---

## 1. Purpose

This document defines the **formal API contract** for Nexus Core MVP1.
It is an OpenAPI 3.0 specification focused on ingestion governance, validation, and query orchestration.

---

## 2. OpenAPI Specification (YAML)

```yaml
openapi: 3.0.3
info:
  title: Nexus Core MVP1 API
  version: v1.0
  description: |
    JWT claims and validation rules are defined in JWT_SPEC_v1.0.md.
    API versioning uses X-Api-Version header (see API_VERSIONING_v1.0.md).
servers:
  - url: /api
security:
  - bearerAuth: []
tags:
  - name: governance
  - name: ingestion
  - name: validation
  - name: query
  - name: feedback
paths:
  /governance/sources:
    get:
      tags: [governance]
      summary: List sources with governance status
      parameters:
        - in: query
          name: status
          schema:
            $ref: '#/components/schemas/GovernanceStatus'
        - in: query
          name: system_id
          schema:
            type: string
        - in: query
          name: game_id
          schema:
            type: string
        - in: query
          name: limit
          schema:
            type: integer
            minimum: 1
            maximum: 200
        - in: query
          name: offset
          schema:
            type: integer
            minimum: 0
      responses:
        '200':
          description: Source list
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/SourceRecord'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '500':
          $ref: '#/components/responses/ServerError'
  /governance/sources/{doc_id}:
    get:
      tags: [governance]
      summary: Get a source record by doc_id
      parameters:
        - in: path
          name: doc_id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Source record
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SourceRecord'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/ServerError'
  /governance/sources/{doc_id}/approve:
    post:
      tags: [governance]
      summary: Approve a source for ingestion
      parameters:
        - in: path
          name: doc_id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Approved
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'
        '500':
          $ref: '#/components/responses/ServerError'
  /governance/sources/{doc_id}/deny:
    post:
      tags: [governance]
      summary: Deny a source with reason
      parameters:
        - in: path
          name: doc_id
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [reason]
              properties:
                reason:
                  type: string
      responses:
        '200':
          description: Denied
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'
        '500':
          $ref: '#/components/responses/ServerError'
  /governance/sources/{doc_id}/reopen:
    post:
      tags: [governance]
      summary: Reopen a denied source for approval
      parameters:
        - in: path
          name: doc_id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Reopened
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'
        '500':
          $ref: '#/components/responses/ServerError'
  /governance/sources/{doc_id}/retry:
    post:
      tags: [governance]
      summary: Admin-gated retry after ERROR
      parameters:
        - in: path
          name: doc_id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Retry queued
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'
        '500':
          $ref: '#/components/responses/ServerError'
  /governance/duplicates/{doc_id}/decision:
    post:
      tags: [governance]
      summary: Resolve duplicate decision
      parameters:
        - in: path
          name: doc_id
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [decision]
              properties:
                decision:
                  type: string
                  enum: [IGNORE_DUPLICATE, ALLOW_SEPARATE_INSTANCE]
      responses:
        '200':
          description: Duplicate decision recorded
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'
        '500':
          $ref: '#/components/responses/ServerError'
  /governance/events:
    get:
      tags: [governance]
      summary: List governance events
      parameters:
        - in: query
          name: event_type
          schema:
            type: string
            enum: [STATUS_CHANGE, REMOVAL_REQUEST]
        - in: query
          name: doc_id
          schema:
            type: string
        - in: query
          name: limit
          schema:
            type: integer
            minimum: 1
            maximum: 200
        - in: query
          name: offset
          schema:
            type: integer
            minimum: 0
      responses:
        '200':
          description: Event list
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/GovernanceEvent'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '500':
          $ref: '#/components/responses/ServerError'
  /ingestion/jobs/{doc_id}/status:
    get:
      tags: [ingestion]
      summary: Get ingestion status by doc_id
      parameters:
        - in: path
          name: doc_id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Status
          content:
            application/json:
              schema:
                type: object
                properties:
                  doc_id:
                    type: string
                  status:
                    $ref: '#/components/schemas/GovernanceStatus'
                  updated_at:
                    type: string
                    format: date-time
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/ServerError'
  /validation/{doc_id}/run:
    post:
      tags: [validation]
      summary: Run validation for a doc_id
      parameters:
        - in: path
          name: doc_id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Validation started
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '409':
          $ref: '#/components/responses/Conflict'
        '500':
          $ref: '#/components/responses/ServerError'
  /validation/{doc_id}/reports:
    get:
      tags: [validation]
      summary: List validation reports for a doc_id
      parameters:
        - in: path
          name: doc_id
          required: true
          schema:
            type: string
        - in: query
          name: limit
          schema:
            type: integer
            minimum: 1
            maximum: 200
        - in: query
          name: offset
          schema:
            type: integer
            minimum: 0
      responses:
        '200':
          description: Report list
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/ValidationReport'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/ServerError'
  /query:
    post:
      tags: [query]
      summary: Execute a query
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/QueryRequest'
      responses:
        '200':
          description: Query response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/QueryResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '500':
          $ref: '#/components/responses/ServerError'
  /feedback:
    post:
      tags: [feedback]
      summary: Submit feedback for a response
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/FeedbackRequest'
      responses:
        '200':
          description: Feedback accepted
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '403':
          $ref: '#/components/responses/Forbidden'
        '404':
          $ref: '#/components/responses/NotFound'
        '500':
          $ref: '#/components/responses/ServerError'
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  responses:
    BadRequest:
      description: Invalid request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    Unauthorized:
      description: Missing or invalid authentication
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    Forbidden:
      description: Not authorized for this action
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    Conflict:
      description: Invalid state transition or conflict
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    ServerError:
      description: Internal server error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
  schemas:
    Error:
      type: object
      required: [code, message]
      properties:
        code:
          type: string
        message:
          type: string
    GovernanceStatus:
      type: string
      enum:
        - DISCOVERED
        - PENDING_APPROVAL
        - DUPLICATE_DETECTED
        - APPROVED
        - DENIED
        - INGESTING
        - INGESTED
        - ERROR
        - DEACTIVATED
    GovernanceEvent:
      type: object
      properties:
        event_id:
          type: string
        doc_id:
          type: string
        event_type:
          type: string
          enum: [STATUS_CHANGE, REMOVAL_REQUEST]
        from_status:
          type: string
        to_status:
          type: string
        triggered_by:
          type: string
        triggered_at:
          type: string
          format: date-time
        metadata_json:
          type: object
    SourceRecord:
      type: object
      required: [doc_id, source_sha256, status, original_filename, first_seen_at, state_version]
      properties:
        doc_id:
          type: string
        source_sha256:
          type: string
        status:
          $ref: '#/components/schemas/GovernanceStatus'
        state_version:
          type: integer
        original_filename:
          type: string
        first_seen_at:
          type: string
          format: date-time
        current_path:
          type: string
        system_id:
          type: string
        game_id:
          type: string
        owner_user_id:
          type: string
    ValidationReport:
      type: object
      properties:
        doc_id:
          type: string
        run_id:
          type: string
        status:
          type: string
          enum: [PASS, FAIL]
        validator_version:
          type: string
        report_path:
          type: string
        created_at:
          type: string
          format: date-time
    QueryRequest:
      type: object
      required: [query_text]
      properties:
        query_text:
          type: string
        user_id:
          type: string
        game_id:
          type: string
        system_id:
          type: string
        role:
          type: string
          enum: [PLAYER, GM, ADMIN]
    QueryResponse:
      type: object
      properties:
        response_text:
          type: string
        sources:
          type: array
          items:
            type: object
            properties:
              doc_id:
                type: string
              chunk_id:
                type: string
              tool_id:
                type: string
    FeedbackRequest:
      type: object
      required: [doc_id, chunk_id, rating]
      properties:
        doc_id:
          type: string
        chunk_id:
          type: string
        rating:
          type: string
          enum: [UP, DOWN]
        user_id:
          type: string
```
