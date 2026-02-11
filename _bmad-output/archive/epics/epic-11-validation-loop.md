# Epic 11: Validation Loop

**Goal:** Replace single-pass Verify/Validate phases with an iterative review→fix→review cycle that continues until all issues are resolved or max iterations reached.

**Priority:** P2 (MVP)
**Dependencies:** Epic 3 (Hook & Phase Execution), Epic 5 (Pipeline Orchestration), Epic 8 (Evidence Gathering)

---

## Story 11.1: Unified Validation Phase

As a developer,
I want a single "Validation" phase that combines evidence, code review, and tests,
So that all quality checks happen in one coordinated loop.

**Acceptance Criteria:**

**Given** pipeline reaches validation
**When** the phase starts
**Then** it runs: Evidence Gathering → Code Review → Test Suite

**Given** all validators pass
**When** iteration completes
**Then** phase completes successfully, moves to Document

**Given** any validator finds issues
**When** iteration completes
**Then** issues are collected for triage

**Given** the unified validation phase
**When** configured in project.yaml
**Then** individual validators can be enabled/disabled:
```yaml
validation:
  enable_evidence: true
  enable_review: true
  enable_tests: true
```

---

## Story 11.2: Validation Issue Model

As a developer,
I want validation issues tracked with structured metadata,
So that triage and fix tracking work reliably.

**Acceptance Criteria:**

**Given** a validation issue
**When** captured
**Then** it includes: id, source, severity, description, location, context

**Given** issue sources
**When** categorized
**Then** options are: TEST, REVIEW, EVIDENCE

**Given** issue severity
**When** categorized
**Then** options are: ERROR (must fix), WARNING (should fix), INFO (optional)

**Given** issue tracking
**When** fix is attempted
**Then** issue records: fix_attempted, fix_attempt_count, last_fix_result

---

## Story 11.3: Issue Triage System

As a developer,
I want to triage validation issues into FIX, DISMISS, or DEFER,
So that I control which issues block the pipeline.

**Acceptance Criteria:**

**Given** issues are found
**When** triage runs
**Then** each issue is categorized: FIX, DISMISS, or DEFER

**Given** `triage_mode: auto` in config
**When** triage runs
**Then** LLM decides based on issue severity and context

**Given** `triage_mode: manual` in config
**When** triage runs
**Then** user is prompted for each issue (or batch)

**Given** a DISMISSED issue
**When** recorded
**Then** it's logged with reasoning and doesn't block pipeline

**Given** a DEFERRED issue
**When** recorded
**Then** it's added to PR description as "Known Issues"

**Given** a FIX issue
**When** recorded
**Then** it enters the fix queue for the next iteration

---

## Story 11.4: Fix Iteration Loop

As a developer,
I want the system to attempt fixes and re-validate,
So that issues are resolved automatically when possible.

**Acceptance Criteria:**

**Given** issues marked FIX
**When** fix iteration starts
**Then** LLM is prompted to fix all FIX issues

**Given** fix attempt
**When** LLM completes
**Then** affected validators are re-run

**Given** fix resolves the issue
**When** re-validation passes
**Then** issue is marked resolved

**Given** fix doesn't resolve the issue
**When** re-validation fails
**Then** fix_attempt_count increments, issue re-enters triage

**Given** max fix attempts reached (default: 2)
**When** issue still unresolved
**Then** issue is auto-triaged to DEFER with explanation

---

## Story 11.5: Iteration Limits and Exit Conditions

As a developer,
I want configurable limits on validation iterations,
So that runs don't loop forever.

**Acceptance Criteria:**

**Given** validation loop
**When** max_iterations reached (default: 5)
**Then** loop exits with remaining issues as DEFERRED

**Given** validation loop
**When** all issues are resolved, dismissed, or deferred
**Then** loop exits successfully

**Given** validation loop
**When** no progress made (same issues after fix attempt)
**Then** remaining FIX issues auto-defer after 2 stalls

**Given** configuration
**When** limits are set
**Then** these are configurable:
```yaml
validation:
  max_iterations: 5
  max_fix_attempts_per_issue: 2
  stall_threshold: 2
```

---

## Story 11.6: Validation State Persistence

As a developer,
I want validation state persisted,
So that I can resume validation after interruption.

**Acceptance Criteria:**

**Given** validation iteration completes
**When** state is saved
**Then** includes: current_iteration, issues_list, triage_decisions, fix_history

**Given** run is resumed
**When** validation was in progress
**Then** loop continues from last iteration

**Given** issues list
**When** persisted
**Then** stored at `.adw/runs/<id>/validation/issues.json`

**Given** triage decisions
**When** persisted
**Then** stored at `.adw/runs/<id>/validation/triage.json`

---

## Story 11.7: Validation Report Generation

As a developer,
I want a validation report summarizing the loop results,
So that I understand what was checked and decided.

**Acceptance Criteria:**

**Given** validation loop completes
**When** report is generated
**Then** it includes: iterations_run, issues_found, issues_fixed, issues_dismissed, issues_deferred

**Given** the report
**When** stored
**Then** it's at `.adw/runs/<id>/artifacts/validation/report.md`

**Given** deferred issues
**When** report is generated
**Then** they're formatted for inclusion in PR description

**Given** validation confidence
**When** calculated
**Then** it's: HIGH (all resolved), MEDIUM (some deferred), LOW (many deferred or dismissed)

---

## Validators

### Test Validator
- Runs configured test command (default: `pytest` or `npm test`)
- Parses output for failures
- Each failing test becomes a ValidationIssue

### Review Validator
- Runs code review prompt against changes
- Extracts issues from LLM response
- Checks: code quality, security, patterns, edge cases

### Evidence Validator
- Runs evidence gathering (Epic 8)
- Checks evidence completeness against plan
- Missing evidence becomes a ValidationIssue

---

## Pipeline Flow Change

**OLD:**
```
Plan → Build → Verify → Validate → Document
```

**NEW:**
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
            │
            ▼
       Document
```

---

## Configuration

```yaml
# .adw/project.yaml
validation:
  # Validators to run
  enable_evidence: true
  enable_review: true
  enable_tests: true

  # Iteration limits
  max_iterations: 5
  max_fix_attempts_per_issue: 2
  stall_threshold: 2

  # Triage mode
  triage_mode: auto           # auto | manual | hybrid
  auto_dismiss_info: true     # Auto-dismiss INFO severity

  # Test configuration
  test_command: "pytest"
  test_timeout_seconds: 300

  # Review configuration
  review_prompt: null         # Custom review prompt path
  review_focus:               # Focus areas for review
    - security
    - error_handling
    - edge_cases
```

---

## Epic 11: Dependency Flowchart

```
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately                                        ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [11-1] Unified Validation Phase                                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 11-1                                               ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [11-2] Validation Issue Model                                    ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 3: After 11-2 (PARALLEL x3)                                 ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [11-3] Issue Triage    [11-4] Fix Iteration   [11-6] State       ║
║         System                  Loop                Persistence   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 4: After 11-3, 11-4, 11-6                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [11-5] Iteration Limits and Exit Conditions                      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 5: After 11-5                                               ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [11-7] Validation Report Generation                              ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---
