# Sprint Change Proposal: ADW-SDK Feature Alignment

**Date:** 2026-01-03
**Author:** John (PM Agent)
**Stakeholder:** Ivo
**Status:** APPROVED

---

## Section 1: Issue Summary

### Problem Statement

The adw-final implementation, while architecturally cleaner than its predecessor, is missing critical operational features from adw-sdk that are necessary for production-grade agentic development workflows.

### Trigger Context

During a comprehensive gap analysis comparing adw-final to adw-sdk, **53 features** were identified as NOT PLANNED in adw-final. The most critical gaps affect:

1. **Concurrent execution** — adw-final is single-run only
2. **Quality assurance** — No iterative validation/fix loop
3. **Safety** — No guardrails on LLM tool usage
4. **Delivery automation** — No Ship phase for PR merge
5. **Event-driven triggers** — No webhook infrastructure

### Evidence

| Evidence | Source |
|----------|--------|
| 53 features NOT PLANNED | Gap analysis (2026-01-03) |
| 30 features PLANNED but incomplete | Epic review |
| adw-sdk worktree system (15 concurrent slots) | `worktree_ops.py` |
| adw-sdk security hooks | `pre_tool_use.py` |
| adw-sdk validation loop with triage | `validators.py` |

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact Type | Description |
|------|-------------|-------------|
| Epic 3 | EXTEND | Add security hooks (3 new stories) |
| Epic 5 | AFFECTED | Pipeline flow changes for validation loop |
| Epic 7 | EXTEND | Add workflow index (1 new story, MVP priority) |
| Epic 11 | EXTEND | Full task lifecycle (5 new stories) |
| NEW Epic 12 | NEW | Worktree Isolation (6 stories) |
| NEW Epic 13 | NEW | Ship Phase & Deployment (6 stories) |
| NEW Epic 14 | NEW | Webhook Infrastructure (7 stories) |
| NEW Epic 15 | NEW | Validation Loop (7 stories) |

### Story Impact

| Category | Count |
|----------|-------|
| New Stories (MVP) | 17 |
| New Stories (Post-MVP) | 18 |
| Extended Stories | 9 |
| **Total New/Modified** | **44** |

### Artifact Conflicts

| Artifact | Conflict | Resolution |
|----------|----------|------------|
| PRD | Missing features | Add model config per phase, security hooks |
| Architecture | Pipeline flow | Update for validation loop |
| Epic List | Missing epics | Add 4 new epics, update 3 existing |

### Technical Impact

| Area | Impact |
|------|--------|
| Pipeline Flow | Verify+Validate → Unified Validation Loop |
| Concurrency | Single-run → 15 concurrent via worktrees |
| Configuration | Add phase-level model config, security patterns |
| CLI Commands | Add `adw cleanup`, `adw webhook start` |

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment

**Rationale:**

1. MVP scope is already well-defined (Epics 1-6 complete)
2. New features are additive, not replacing existing work
3. No rollback needed — current implementation is solid foundation
4. Clear separation between MVP additions and Post-MVP features

### Effort Assessment

| Timeline | Scope | Effort |
|----------|-------|--------|
| MVP Additions | Epics 12, 15 + Extensions | Medium-High |
| Post-MVP | Epics 13, 14 | Medium |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Validation loop complexity | Medium | High | Start with simple triage, iterate |
| Worktree edge cases | Medium | Medium | Comprehensive testing, fallback mode |
| Webhook security | Low | High | Signature verification from day 1 |

---

## Section 4: Detailed Change Proposals

### 4.1 New MVP Epics

#### Epic 12: Worktree Isolation
- **Goal:** Enable concurrent workflow execution via git worktrees
- **Stories:** 6
- **Key Features:**
  - Git worktree creation/cleanup
  - Deterministic port allocation (9100-9214)
  - Concurrent run management (max 15)
  - Worktree context in phases

#### Epic 15: Validation Loop
- **Goal:** Iterative review→fix cycle with issue triage
- **Stories:** 7
- **Key Features:**
  - Unified validation phase (evidence + review + tests)
  - Issue triage (FIX/DISMISS/DEFER)
  - Fix iteration with max attempts
  - Validation report generation

### 4.2 New Post-MVP Epics

#### Epic 13: Ship Phase & Deployment
- **Goal:** Automate PR approval, merge, and deployment
- **Stories:** 6
- **Key Features:**
  - PR approval/merge automation
  - Project-specific deployment hooks
  - Issue closing on merge

#### Epic 14: Webhook Infrastructure
- **Goal:** Event-driven workflow triggers
- **Stories:** 7
- **Key Features:**
  - Generic webhook server (FastAPI)
  - Linear provider (first)
  - GitHub provider (future)
  - Bot loop prevention

### 4.3 Epic Extensions

#### Epic 3: Security Hooks
- **New Stories:** 3.X, 3.Y, 3.Z
- **Features:**
  - Block dangerous commands (`rm -rf`, etc.)
  - Block `.env` file access
  - Tool execution logging

#### Epic 7: Workflow Index
- **New Story:** 7.0 (MVP priority)
- **Features:**
  - Global workflow index (`~/.adw/index.jsonl`)
  - Cross-project run listing

#### Epic 11: Full Task Lifecycle
- **New Stories:** 11.6-11.10
- **Features:**
  - Status update comments
  - Label management
  - Issue closing
  - GitHub Issues provider

### 4.4 Architecture Updates

#### Model Configuration Per Phase
```yaml
phases:
  plan:
    model: opus
  build:
    model: opus
  validation:
    model: sonnet
  document:
    model: sonnet
```

#### Pipeline Flow Change
```
OLD: Plan → Build → Verify → Validate → Document
NEW: Plan → Build → Validation Loop → Document → Ship
```

---

## Section 5: Implementation Handoff

### Change Scope Classification

**Scope:** MODERATE

This requires backlog reorganization and prioritization adjustments, but no fundamental replan of the project.

### Handoff Recipients

| Role | Responsibility |
|------|----------------|
| Development Team | Implement new epics and story extensions |
| Product Owner | Prioritize MVP additions within current sprint |
| Solution Architect | Review architecture updates |

### Implementation Sequence

#### MVP Additions (Priority Order)

1. **Epic 12: Worktree Isolation** — Do FIRST (foundational)
2. **Epic 3 Extension: Security Hooks** — Do EARLY (safety)
3. **Story 7.0: Workflow Index** — Quick win
4. **Model Config Per Phase** — Quick win
5. **Epic 15: Validation Loop** — Do LAST (most complex)

#### Post-MVP (Future Sprints)

1. Epic 11 Extension (Full Task Manager)
2. Epic 13 (Ship Phase)
3. Epic 14 (Webhooks)

### Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Concurrent runs work | 3+ simultaneous runs without conflict |
| Validation loop functions | Issues triaged and fixed automatically |
| Security hooks active | Dangerous commands blocked in tests |
| Workflow index populated | `adw list` shows cross-project runs |

---

## Section 6: Deliverables Produced

### New Epic Files Created
- `epic-12-worktree-isolation.md`
- `epic-13-ship-phase-deployment.md`
- `epic-14-webhook-infrastructure.md`
- `epic-15-validation-loop.md`

### Updated Files
- `epic-list.md` — Updated with new epics and extensions

### Pending Updates (To Be Applied)
- `epic-3-hook-phase-execution.md` — Add security hook stories
- `epic-7-observability-logging.md` — Add Story 7.0
- `epic-11-task-manager-integration.md` — Add Stories 11.6-11.10
- `prd.md` — Add model config per phase
- `architecture.md` — Add model config decision, update pipeline flow

---

## Approval

**Status:** ✅ APPROVED by Ivo (2026-01-03)

**Next Steps:**
1. Apply pending updates to existing epic files
2. Update PRD and Architecture documents
3. Re-prioritize sprint backlog
4. Begin implementation with Epic 12 (Worktree Isolation)

---

✅ **Correct Course workflow complete, Ivo!**
