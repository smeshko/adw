# Sprint Change Proposal: Simplify Validation Phase (New Epic 16)

**Date:** 2026-01-08
**Author:** AI Change Navigator
**Approved By:** Ivo
**Change Scope:** Moderate

---

## Section 1: Issue Summary

### Problem Statement

Epic 11 (Validation Loop) as **implemented** is over-engineered for the intended use case. The design includes:

- 7 stories with complex interdependencies
- Up to 5 validation iterations
- Full triage system (FIX/DISMISS/DEFER decisions)
- Stall detection (2 consecutive identical failure sets)
- Complex state persistence for mid-validation resume
- Evidence gathering integration

**Root Cause:** The design anticipated edge cases that rarely occur in practice. The 80/20 rule applies: 80% of validation issues are simple (test failure, lint error, obvious bug) and get fixed in iteration 1. The remaining 20% likely need human intervention regardless of iteration count.

### Discovery Context

Emerged during implementation planning discussions. Multiple iterations of design refinement revealed increasing complexity without proportional value. Claude's assessment: "Loops burn money and oscillate. Every iteration past 2 has diminishing returns and increasing risk of making things worse."

### Evidence

1. **Cost Analysis:** Each validation iteration involves LLM calls for triage and fix. 5 iterations × 3 validators = 15+ potential LLM calls per run.
2. **Convergence Risk:** Iteration loops can oscillate (fix A breaks B, fix B breaks A) without converging.
3. **Complexity Cost:** Triage system adds ~100 lines of orchestrator code, 3 models, persistence logic.
4. **Practical Reality:** "Autonomous ≠ infinite retries. It should fail fast and clearly when it can't succeed."

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| Epic 11 | **Major Redesign** | Reduce from 7 stories to 3-4, remove triage system |
| Epic 8 | None | Evidence gathering unaffected |
| Epic 5 | Minor | Pipeline flow diagram update |
| Others | None | No dependencies on triage system |

### Story Impact

**Stories to REMOVE or DEFER:**
- **11.3 (Issue Triage System):** Remove entirely. Replace with simple `can_auto_fix` boolean.
- **11.5 (Iteration Limits/Exit Conditions):** Simplify to single `max_iterations: 2` config.

**Stories to SIMPLIFY:**
- **11.4 (Fix Iteration Loop):** Merge into unified flow. One fix attempt, one re-validation.
- **11.6 (Validation State Persistence):** Simplify - only persist final result, not mid-loop state.

**Stories to KEEP (with modifications):**
- **11.1 (Unified Validation Phase):** Keep - still runs tests, linters, code review.
- **11.2 (Validation Issue Model):** Keep but simplify - remove triage fields.
- **11.7 (Validation Report):** Keep - still report what passed/failed.

### Artifact Conflicts

| Artifact | Conflict | Required Update |
|----------|----------|-----------------|
| PRD | None | No changes needed |
| Architecture | Minor | Update pipeline flow diagram |
| Epic 11 | Major | Rewrite stories |
| Configuration | Minor | Remove triage_mode, stall_threshold configs |

### Technical Impact

- **Reduced Code:** ~100 fewer lines of orchestration logic
- **Simpler State:** No mid-validation state persistence needed
- **Lower Cost:** Maximum 4 LLM calls (validate, fix, re-validate, report) vs unbounded
- **Predictable Runtime:** Deterministic 2-iteration max

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment

Modify Epic 11 stories within existing epic structure. No rollback needed (no implementation exists).

### Rationale

| Factor | Assessment |
|--------|------------|
| Implementation Effort | **Reduced** - Less code to write |
| Technical Risk | **Reduced** - Simpler state machine |
| Timeline Impact | **Positive** - Faster to implement |
| Team Morale | **Positive** - Less complex system to maintain |
| Stakeholder Value | **Maintained** - Still delivers validated code |
| Long-term Maintainability | **Improved** - Less surface area for bugs |

### New Validation Flow

```
validate/prompt.md
       │
       ▼
   [passed?] ───yes───► done
       │
       no
       │
       ▼
 [can_auto_fix?] ───no───► fail with report
       │
      yes
       │
       ▼
   fix/prompt.md
       │
       ▼
   re-validate
       │
       ▼
   [passed?] ───yes───► done
       │
       no
       │
       ▼
   fail with report
```

### Configuration (Simplified)

```yaml
# .adw/project.yaml
validation:
  enable_tests: true
  enable_review: true
  max_iterations: 2  # Hard cap, no negotiation
  test_command: "pytest"
  test_timeout_seconds: 300
```

**Removed configurations:**
- `triage_mode` (auto/manual/hybrid)
- `auto_dismiss_info`
- `stall_threshold`
- `max_fix_attempts_per_issue`

---

## Section 4: Detailed Change Proposals

### Approach: New Epic 16 (Rework)

Instead of modifying Epic 11 (which is already implemented), we create **Epic 16: Validation Phase Simplification** to rework the existing implementation.

See: `_bmad-output/epics/epic-16-validation-simplification.md`

### Epic 16 Stories

| Story | Description |
|-------|-------------|
| 16-1 | Remove Triage System |
| 16-2 | Limit to 2 Iterations |
| 16-3 | Simplify State Persistence |
| 16-4 | Update Validation Prompts |
| 16-5 | Update Validation Report |

---

### Key Changes (Reference)

#### Story 16.1: Remove Triage System

**OLD:**
```
Given any validator finds issues
When iteration completes
Then issues are collected for triage
```

**NEW:**
```
Given any validator finds issues
When iteration completes
Then issues are collected with auto-fix assessment
```

**Rationale:** Remove triage reference, add `can_auto_fix` assessment.

---

#### Story 11.2: Validation Issue Model (SIMPLIFY)

**OLD Acceptance Criteria:**
```
Given issue tracking
When fix is attempted
Then issue records: fix_attempted, fix_attempt_count, last_fix_result
```

**NEW Acceptance Criteria:**
```
Given issue tracking
When captured
Then issue includes: id, source, severity, description, location, fix_hint
```

**Rationale:** Remove multi-attempt tracking. Single fix attempt makes these fields unnecessary.

---

#### Story 11.3: Issue Triage System (REMOVE)

**Status:** REMOVED

**Replacement:** Simple `can_auto_fix` boolean returned by validator prompt.

```python
{
  "passed": false,
  "issues": [...],
  "can_auto_fix": true,  # Replaces entire triage system
  "summary": "3 test failures, all have clear fixes"
}
```

**Rationale:** Triage is an LLM call to filter garbage. If validator returns garbage, fix the validator prompt instead of adding another LLM call.

---

#### Story 11.4: Fix Iteration Loop (MERGE INTO 11.1)

**OLD Flow:**
```
Issues marked FIX → LLM fixes → Re-run validators →
Issue resolved? Mark resolved : increment fix_attempt_count, re-triage →
Max attempts? Auto-defer : loop
```

**NEW Flow:**
```
Issues found + can_auto_fix → ONE fix attempt →
Re-validate ONCE → Passed? Done : Fail with report
```

**Rationale:** Single fix attempt. No re-triage loop. Fail fast.

---

#### Story 11.5: Iteration Limits (SIMPLIFY)

**OLD Acceptance Criteria:**
```yaml
validation:
  max_iterations: 5
  max_fix_attempts_per_issue: 2
  stall_threshold: 2
```

**NEW Acceptance Criteria:**
```yaml
validation:
  max_iterations: 2  # Fixed. No config complexity.
```

**Rationale:** 2 is the magic number. More iterations have diminishing returns.

---

#### Story 11.6: Validation State Persistence (SIMPLIFY)

**OLD:**
- Persist after every iteration
- Store: current_iteration, issues_list, triage_decisions, fix_history
- Resume from mid-loop

**NEW:**
- Persist final result only
- Store: passed, issues (if failed), fix_attempted
- No mid-loop resume (max 2 iterations, fast enough to re-run)

**Rationale:** Resume granularity at phase level is sufficient. No one needs to resume mid-validation.

---

#### Story 11.7: Validation Report (KEEP - Minor Updates)

**OLD:**
```
iterations_run, issues_found, issues_fixed, issues_dismissed, issues_deferred
```

**NEW:**
```
passed, issues_found, issues_fixed, fix_attempted, final_issues
```

**Rationale:** Simpler report without triage categories.

---

### Architecture Document Updates

**Section: Pipeline Flow Change**

**OLD:**
```
Plan → Build → Validation Loop → Document
                    │
            ┌───────┴───────┐
            ▼               │
    [Run Validators]        │
            │               │
            ▼               │
    [Collect Issues]        │
            │               │
            ▼               │
    [Triage Issues]         │
            │               │
    ┌───────┼───────┐       │
    ▼       ▼       ▼       │
  DISMISS  DEFER   FIX      │
    │       │       │       │
    │       │       ▼       │
    │       │   [Apply Fix] │
    │       │       │       │
    │       │       └───────┘
    │       │
    ▼       ▼
  [Log]  [Add to PR]
            │
            ▼
    [Exit Loop]
```

**NEW:**
```
Plan → Build → Validation → Document
                    │
                    ▼
            [Run Validators]
                    │
                    ▼
              [Passed?]────yes────► Document
                    │
                    no
                    │
                    ▼
            [Can Auto-Fix?]───no───► Fail with Report
                    │
                   yes
                    │
                    ▼
              [Apply Fix]
                    │
                    ▼
            [Re-Validate Once]
                    │
                    ▼
              [Passed?]────yes────► Document
                    │
                    no
                    │
                    ▼
            Fail with Report
```

---

### Epic 11 Dependency Flowchart (Updated)

**OLD:** 5 waves, 7 stories

**NEW:** 2 waves, 4 stories

```
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately                                        ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [11-1] Unified Validation Phase                                  ║
║  [11-2] Validation Issue Model (simplified)                       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 11-1, 11-2                                         ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [11-3] Fix and Re-Validate (merged from 11.4, 11.5, 11.6)       ║
║  [11-4] Validation Report Generation (was 11.7)                   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## Section 5: Implementation Handoff

### Change Scope Classification: Moderate

This change requires:
- Epic 11 story rewrites (4 stories instead of 7)
- Minor architecture document update
- No PRD changes
- No code rollback

### Handoff Recipients

| Role | Responsibility |
|------|----------------|
| **Development Team** | Implement simplified validation flow |
| **Product Owner** | Approve story changes, update backlog |

### Success Criteria

1. Epic 11 reduced to 4 stories
2. Validation phase completes in max 2 iterations
3. No triage system in implementation
4. Configuration simplified (remove 4 config keys)
5. Architecture diagram updated

### Next Steps

1. **Immediate:** Update Epic 11 markdown file with new stories
2. **Immediate:** Update architecture.md pipeline flow diagram
3. **Sprint Planning:** Add updated stories to sprint backlog
4. **Implementation:** Build simplified validation phase

---

## Approval

**Change Proposal Status:** APPROVED (YOLO mode)

**Proposed Changes:**
- [x] New Epic 16 created (5 stories to rework Epic 11 implementation)
- [x] Remove triage system
- [x] Limit to 2 iterations
- [x] Simplify configuration
- [x] Simplify state persistence

**Deliverables:**
- `_bmad-output/epics/epic-16-validation-simplification.md` - New epic created
- `_bmad-output/sprint-change-proposal-2026-01-08.md` - This document

**Epic 11 Status:** Unchanged (existing implementation preserved)

---

*Generated by Correct Course workflow on 2026-01-08*
