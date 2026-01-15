# Nexus Core – UI Wireframe Specification (MVP1)

## 1. Design Principles

### 1.1 Dynamic-by-System
- UI structure is **static**, but content blocks are **schema-driven** by system (Pathfinder, Cyberpunk, etc.)
- Character sheets, terminology, labels, and layouts are generated from **system schemas** derived from source books

- System schemas load from `/schemas/character/<system_id>.json`
### 1.2 Theme-Aware
- UI theme may be:
  - **Auto-selected** based on Active Game primary system
  - **Manually overridden** in User Profile
- Theme affects:
  - Color palette
  - Typography
  - Iconography
  - Decorative framing

### 1.3 Role + Context Driven
Visibility is determined by:
- RBAC role (Player / GM / Admin)
- Context (Global / Game)
- Ownership (GM of *this* game vs GM of another game)

---

## 2. Global UI Elements (All Screens)

### 2.1 Top Banner
- Username (clickable → Profile & Settings)
- Tier Icon (Player / GM shown via icon only)
- Optional buttons (only if permitted):
  - Switch to GM Hub
  - Switch to Admin UI

### 2.2 Theme Engine
- Theme selector:
  - Auto (default)
  - Manual override (profile)
- Auto mode:
  - Player Hub → uses Active Game primary system
  - GM Hub → uses GM-selected focus game or neutral GM theme

---

## 3. Player Hub Wireframe

### 3.1 Resource Bars (Top)
- Character Sheets (usage bar)
- Source Books (usage bar)
- Player Tokens (usage bar)
- Percent-only display (no numbers)

### 3.2 Active Campaign Panel
- List of joined games
- Single active selection (radio behavior)
- Active game indicator (checkmark / glow)

#### Campaign Expand (Twisty)
- Shows sources linked to that game
- Read-only view

### 3.3 Character Selection Panel
- Characters filtered by Active Campaign
- Character cards:
  - Name
  - Class / Role
  - Level
- Click → Character Sheet
- Create New Character button (limit-gated)

### 3.4 AI Query Panel
- Large input + response area (left-to-right flow)
- No submit button
- Enter-to-send
- Orchestrator-controlled:
  - Search mode
  - Top-K
- Response area:
  - Citations
  - Image previews (if applicable)
  - Feedback: 👍 / 👎

---

## 4. Character Sheet Screen (Player)

### 4.1 Dynamic Sheet Builder
- Built from **Primary System schema**
- Schema source: `/schemas/character/<system_id>.json`
- Sections defined by system:
  - Attributes
  - Skills
  - Abilities
  - Equipment
  - Resources

### 4.2 Navigation
- Return to Player Hub button
- Close (X)

### 4.3 Permissions
- Read/write gated by:
  - Game status
  - Player membership
  - Tier violations

---

## 5. GM Hub Wireframe

### 5.1 GM Resource Bars
- Games Owned
- GM-Owned Sources
- GM Tokens

### 5.2 GM Game List
- Owned games highlighted
- Non-owned games read-only
- Select game → loads GM context

### 5.3 GM AI Query Panel
- Same UI as Player
- Contextualized for:
  - Prep
  - Rule lookup
  - Cross-system reasoning

### 5.4 GM Controls Panel (Contextual)
Visible **only if GM owns selected game**:
- Invite/remove players
- Approve player-offered sources
- Link/unlink GM sources
- View game tier & limits

---

## 6. Game Hub Wireframe

### 6.1 Entry Conditions
- Accessed by selecting a game
- Role-aware rendering

### 6.2 Game Overview Panel
- Game name
- Tier
- Systems:
  - Primary
  - Secondary
  - Tertiary

### 6.3 Game Controls (Role-Based)

#### Player View
- Read-only:
  - Sources
  - Characters
  - NPC personas

#### GM View (Owner Only)
- Manage players
- Manage sources
- Manage NPC personas
- Manage modules (stubbed)

### 6.4 No AI Query (MVP1)
- Reserved space for future expansion

---

## 7. Admin UI (Separate App)

### 7.1 User Management
- Assign Player / GM / Admin flags
- Assign tiers
- Tier values and caps come from `tier_limits`
- Grant/revoke à la carte expansions

### 7.2 Governance & Ingestion
- Pending approvals
- Extraction status
- Validation reports

---

## 8. Profile & Settings Screen

### 8.1 Profile
- Username
- Avatar

### 8.2 Preferences
- Theme mode:
  - Auto
  - Manual
- Preferred default system (optional)

### 8.3 Account State
- Tier overview
- Usage bars
- Violation warnings

---

## 9. State Handling

### 9.1 Limit Violation State
- Blocks most navigation
- Redirects to resolution screen

- Resolution uses `tier_limits` caps
### 9.2 Dormant Game State
- Visible but disabled
- GM-only resolution actions

---

## 10. Summary

This wireframe design:
- Fully supports Player / GM / Game separation
- Is schema-driven for system fidelity
- Supports automatic theming
- Is future-proof for payments, agents, and modules

**This document is suitable as a direct handoff to frontend and backend implementation agents.**



