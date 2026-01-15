# INGESTION_PLANNING_TASK_PROMPTS_v1.0

## Purpose
This document defines the **task-level prompts** for the *Ingestion Planning Agent* for Nexus Core MVP1.

These prompts are designed to:
- Break ingestion planning into **atomic, verifiable tasks**
- Prevent agent drift
- Use the **Git repository as persistent memory**
- Preserve intent, rationale, and decision history

This document is authoritative for planning ingestion work. It does **not** authorize implementation.

---

## Global Rules (Apply to Every Task)

### Mandatory Pre-Task Steps
Before starting any task, the agent MUST:
1. Pull the latest changes from the main branch
2. Read commit history for files it will touch
3. Summarize prior intent in its own words
4. Abort and ask a clarifying question if intent is unclear

### Mandatory Post-Task Steps
After completing any task, the agent MUST:
1. Commit all changes
2. Use the required commit message format
3. Push changes to the repository

Failure to follow these steps invalidates the task.

---

## Git as Memory Protocol

### Why Git Is the Memory Layer
- AI agents do not retain long-term memory
- Git commit history provides durable intent tracking
- Commit messages record *why*, not just *what*

### Required Commit Message Format
```
[ING-PLAN-XXX] Short title

Why:
- Decision context
- Constraint reference

Aligned Docs:
- INGESTION_ARCHITECTURE_v1.0.md �X
- REQUIREMENTS_v1.0.md FR-###
```

### Prohibited Behaviors
- Overwriting files without reading history
- Squashing planning commits
- Refactoring planning documents
- Inventing undocumented behavior

---

## Task ING-PLAN-000 — Repository Memory Initialization

### Purpose
Establish Git as the authoritative memory context for ingestion planning.

### Prompt
```
You are the Ingestion Planning Agent.

Task ID: ING-PLAN-000

Your task is to:
- Inspect the repository structure
- Identify where architectural and planning documents live
- Verify that the following documents exist and are readable:
  - INGESTION_ARCHITECTURE_v1.0.md
  - ARCHITECTURE_v1.0.md
  - REQUIREMENTS_v1.0.md
  - TEST_PLAN_v1.0.md
  - TEST_CASES_v1.0.md
  - ACCEPTANCE_CRITERIA_v1.0.md

Steps:
1. Pull latest from main
2. Read commit history related to /docs
3. Produce a short MEMORY_SUMMARY.md containing:
   - Purpose of MVP1 ingestion
   - Non-negotiable constraints
   - Phasing expectations

Do NOT modify existing docs.
Create MEMORY_SUMMARY.md only if it does not exist.

Commit message must include:
- Task ID
- "Initialize ingestion memory context"
```

---

## Task ING-PLAN-001 — Phase Mapping

### Purpose
Create a single source of truth mapping documents, phases, and tests.

### Prompt
```
Task ID: ING-PLAN-001

Create a PHASE_MAP_v1.0.md document.

It must:
- List Phase 0–7 exactly as defined in ACCEPTANCE_CRITERIA_v1.0.md
- For each phase, list:
  - Governing document(s)
  - Related FR IDs
  - Related test case IDs

Rules:
- Do not invent phases
- Do not merge phases
- Do not add implementation details

Before writing:
- Review commit history for similar planning artifacts
- Reference prior intent explicitly

After writing:
- Commit PHASE_MAP_v1.0.md
- Explain how it will be used by implementation agents
```

---

## Task ING-PLAN-002 — Ingestion Dependency Graph

### Purpose
Make ingestion dependencies explicit to prevent step reordering.

### Prompt
```
Task ID: ING-PLAN-002

Create INGESTION_DEPENDENCIES_v1.0.md.

Content requirements:
- Linear dependency list
- Explicit blockers
- Explicit outputs required to proceed

Rules:
- No diagrams
- No code
- No speculation

Git Memory Rule:
- Cite previous commits or docs where dependencies were implied

Commit with rationale.
```

---

## Task ING-PLAN-003 — Governance State Transition Plan

### Purpose
Prevent illegal ingestion shortcuts.

### Prompt
```
Task ID: ING-PLAN-003

Create GOVERNANCE_FLOW_v1.0.md.

Must include:
- All allowed states
- All allowed transitions
- Which component triggers each transition
- Which transitions are admin-only

Constraints:
- Must match INGESTION_ARCHITECTURE_v1.0.md exactly
- Any discrepancy must be flagged as a question, not corrected

Before commit:
- Re-read all governance-related commits
- Confirm no implicit transitions exist

Commit with explanation of enforcement intent.
```

---

## Task ING-PLAN-004 — Artifact & Manifest Contract Plan

### Purpose
Lock artifact expectations before code exists.

### Prompt
```
Task ID: ING-PLAN-004

Create ARTIFACT_CONTRACT_v1.0.md.

Must specify:
- Required artifact types
- Required directory locations
- Required metadata fields per artifact
- Human-readable traceability rules

Explicitly include:
- Dual-manifest rule
- No canonical merge rule
- Tool provenance requirements

Git-as-memory:
- Reference why artifacts are preserved separately
- Cite decision history from commits or docs

Commit with justification.
```

---

## Task ING-PLAN-005 — Validation & Certification Plan

### Purpose
Define proof of ingestion correctness.

### Prompt
```
Task ID: ING-PLAN-005

Create VALIDATION_PLAN_v1.0.md.

Must include:
- Preconditions for validation
- Required checks mapped to FRs
- Failure conditions
- Certification criteria

Rules:
- Validation must block INGESTED state
- Validation must be repeatable
- Validation must be non-destructive

After writing:
- Map checks to T-ING-012 and T-ING-013
- Commit with validation philosophy summary
```

---

## Task ING-PLAN-006 — Cleanup & Reset Strategy

### Purpose
Guarantee safe iteration and repeatable tests.

### Prompt
```
Task ID: ING-PLAN-006

Create CLEANUP_STRATEGY_v1.0.md.

Must define:
- What constitutes test data
- What must be removed
- What must remain
- How to verify a clean state

Constraints:
- No silent deletes
- No schema resets without confirmation
- Must support repeated test runs

Git memory:
- Explain why cleanup is mandatory
- Cite TEST_PLAN_v1.0.md

Commit with safety rationale.
```

---

## Task ING-PLAN-007 — Final Planning Review & Risk Register

### Purpose
Force explicit acknowledgment of uncertainty and risk.

### Prompt
```
Task ID: ING-PLAN-007

Create INGESTION_RISKS_v1.0.md.

Must include:
- Open questions
- Known risks
- Deferred decisions
- Explicit "not addressed in MVP1" list

If no risks exist, state that explicitly and justify why.

Before committing:
- Review all prior planning commits
- Ensure no contradictions exist

Final commit message must include:
- "Ingestion planning complete"
```

---

## Completion Criteria

Ingestion planning is considered complete when:
- All tasks ING-PLAN-000 through ING-PLAN-007 are completed
- All generated planning documents are committed
- Commit history clearly reflects decision intent
- No open ingestion ambiguities remain unaddressed

This document is versioned. Any modification requires a version bump.




