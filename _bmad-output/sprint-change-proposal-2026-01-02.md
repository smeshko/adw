# Sprint Change Proposal: Task Manager Integration

**Date:** 2026-01-02
**Author:** John (PM Agent)
**Requester:** Ivo
**Status:** APPROVED

---

## 1. Issue Summary

### Problem Statement

The ADW SDK currently requires manual feature descriptions when starting runs (`adw run "Add user authentication"`). Developers who use task management systems like Linear want to:

1. Reference tasks directly by ID (`adw run RULE-123`)
2. Have task content fetched automatically from the task manager
3. Keep task status synchronized as the run progresses
4. Support multiple task managers with a pluggable architecture

### Discovery Context

- **Trigger:** New requirement from user during active development
- **Type:** Feature enhancement (not bug or failed approach)
- **Evidence:** User already has Linear integration skills in their toolkit, indicating existing workflow reliance on Linear

### Business Value

- Reduces manual copy-paste of task descriptions
- Maintains single source of truth in task manager
- Enables workflow automation and team visibility
- Aligns with PRD 12-month goal: "Full integration suite (Linear, GitHub webhooks)"

---

## 2. Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| 1-9 (MVP) | ✅ None | No changes to MVP scope |
| 10 (Post-MVP) | ✅ None | Dashboard unaffected |
| **11 (NEW)** | ➕ Created | New post-MVP epic for Task Manager Integration |

### Artifact Conflicts

| Artifact | Conflict | Resolution |
|----------|----------|------------|
| PRD | None | Added to Post-MVP scope (explicit definition) |
| Architecture | None | New section added (Protocol-based pattern) |
| Epics | None | New Epic 11 created |
| UI/UX | Minimal | CLI auto-detects task ID pattern |

### Technical Impact

- **New package:** `src/adw/task_managers/`
- **New model:** `TaskInfo` in `src/adw/models/task.py`
- **Integration points:** CLI (input handling), Orchestrator (status callbacks)
- **External dependency:** Linear API (GraphQL)
- **Configuration:** New `task_manager` and `task_manager_config` in project.yaml

---

## 3. Recommended Approach

### Selected Path: Direct Adjustment (Post-MVP Addition)

**Rationale:**
- Does not affect current MVP implementation
- Follows existing architectural patterns (Protocol-based abstraction)
- Can be implemented any time after Epic 6 (Run Management)
- Low risk, isolated feature

### Effort & Risk Assessment

| Factor | Assessment |
|--------|------------|
| Effort | Medium (5 stories, ~2-3 weeks) |
| Risk | Low (isolated, post-MVP) |
| Timeline Impact | None (MVP unaffected) |
| Dependencies | Epic 6 must complete first |

---

## 4. Detailed Change Proposals

### 4.1 PRD Update

**File:** `_bmad-output/prd.md`
**Section:** Out of Scope (Post-MVP)

✅ **APPLIED** - Added Task Manager Integration with detailed scope:
- `adw run TASK-123` fetches task content
- Configurable state mapping
- Status updates at phase transitions
- Pluggable architecture via TaskManager protocol

### 4.2 Architecture Addition

**File:** `_bmad-output/architecture.md`
**Location:** New section before "Architecture Completion Summary"

✅ **APPLIED** - Added comprehensive section including:
- TaskManager Protocol definition
- Configuration schema
- Integration points table
- File locations
- Data flow diagram

### 4.3 New Epic 11

**File:** `_bmad-output/epics/epic-11-task-manager-integration.md`

✅ **CREATED** - Complete epic with 5 stories:
1. TaskManager Protocol and Configuration
2. Linear Task Manager Implementation
3. Status Synchronization at Phase Transitions
4. Task ID Pattern Detection
5. Task Context in Prompts

Includes dependency analysis, execution waves, and technical notes.

### 4.4 Epic List Update

**File:** `_bmad-output/epics/epic-list.md`

✅ **APPLIED** - Added Epic 11 to Post-MVP Epics table

---

## 5. Implementation Handoff

### Change Scope Classification

**MINOR** - Can be added to post-MVP backlog without immediate action

### Handoff Recipients

| Role | Responsibility |
|------|----------------|
| Product Owner | Prioritize Epic 11 in post-MVP backlog |
| Development Team | No immediate action (post-MVP) |
| Architect | Architecture section already added |

### Success Criteria

1. ✅ PRD updated with Task Manager Integration scope
2. ✅ Architecture document includes TaskManager abstraction
3. ✅ Epic 11 created with complete stories and acceptance criteria
4. ✅ Epic list updated
5. ⏳ (Future) Stories implemented after MVP completion

---

## 6. Files Modified

| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `_bmad-output/prd.md` | Updated | +5 lines (Post-MVP section) |
| `_bmad-output/architecture.md` | Updated | +100 lines (new section) |
| `_bmad-output/epics/epic-11-task-manager-integration.md` | Created | ~280 lines |
| `_bmad-output/epics/epic-list.md` | Updated | +1 line |

---

## 7. Approval

**Approved by:** Ivo
**Approval Method:** YOLO mode (expedited approval)
**Date:** 2026-01-02

---

✅ **Correct Course workflow complete, Ivo!**
