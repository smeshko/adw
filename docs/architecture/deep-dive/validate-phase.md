# Validate Phase Deep Dive

This document explains the complete execution flow of the Validate phase in ADW.

## Overview

The Validate phase is the third phase in the ADW pipeline (`plan → build → validate → document → ship`). It runs tests, performs adversarial code review, and fixes issues found in the build output.

**Command:** `adw run "Feature description"` (runs full pipeline) or `adw run "Feature" --phase validate --from-run <build_run_id>`

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Orchestrator calls PhaseRunner.run("validate", context)     │
│     - Loads artifacts from plan and build phases                │
│     - Prepares template variables                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. Load Artifacts from Previous Phases                         │
│     PhaseRunner._build_artifacts_map()                          │
│     - plan_output.md  → artifacts["plan"]["plan_output"]        │
│     - build_output.md → artifacts["build"]["build_output"]      │
│     - diff.txt        → artifacts["build"]["diff"]              │
│     - diff_stats.json → artifacts["build"]["diff_stats"]        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. Resolve Command                                             │
│     CommandResolver.resolve("validate")                         │
│     Searches: .adw/commands/validate/ → ~/.adw/commands/validate│
│               → bundled: src/adw/defaults/commands/validate/    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. Render Prompt Template                                      │
│     Variables available:                                        │
│       {{artifacts.plan.plan_output}}  → Plan document           │
│       {{artifacts.build.diff}}        → Git diff of changes     │
│       {{artifacts.build.build_output}}→ Build summary           │
│       {{artifacts.build.diff_stats}}  → Change statistics       │
│       {{context}}                     → RunContext model        │
│       {{worktree_path}}               → Worktree path           │
│                                                                 │
│     Include patterns:                                           │
│       {{include:code-review-loop/...}} → Workflow files         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. Execute LLM (Validation Loop)                               │
│     ClaudeCodeExecutor spawns Claude CLI                        │
│     Timeout: 600s (configurable)                                │
│                                                                 │
│     LLM executes three-phase workflow:                          │
│       Phase 1: Initialize state, detect test command            │
│       Phase 2: Run tests, fix failures, re-run                  │
│       Phase 3: Code review loop (max 2 cycles)                  │
│                - Run adversarial review (Codex or self)         │
│                - Validate findings, dismiss false positives     │
│                - Fix genuine issues, commit, re-test            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  6. Capture Artifacts                                           │
│     - validate_output.md  → LLM response with JSON result       │
│     - validate_tool_calls.json → Tool calls made (if any)       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  7. Auto-Commit Changes                                         │
│     Stages all changes and commits                              │
│     Commit format: adw(validate): <feature> [run_id]            │
└─────────────────────────────────────────────────────────────────┘
```

## Input: What Validate Receives

The validate phase receives artifacts from both plan and build phases:

| Source | Artifact | Template Variable |
|--------|----------|-------------------|
| plan | `plan_output.md` | `{{artifacts.plan.plan_output}}` |
| build | `build_output.md` | `{{artifacts.build.build_output}}` |
| build | `diff.txt` | `{{artifacts.build.diff}}` |
| build | `diff_stats.json` | `{{artifacts.build.diff_stats}}` |

## Validation Workflow (3 Phases)

### Phase 1: Initialization
- Parse context from prompt (files to review, diff, requirements)
- Initialize in-memory tracking state (cycle count, issues fixed/remaining)
- Auto-detect test command from project structure (pytest, jest, etc.)

### Phase 2: Test Validation
```
Run tests → Pass? ──Yes──→ Proceed to Code Review
              │
              No
              ↓
      Analyze failures
              ↓
      Fix code causing failures
              ↓
      Re-run tests → Pass? ──Yes──→ Commit fixes, proceed
                         │
                         No
                         ↓
                  Add to issues_remaining
```

### Phase 3: Code Review Loop (max 2 cycles)
```
┌──────────────────────────────────────────────────────┐
│  For each cycle (max 2):                             │
│    1. Run adversarial code review (Codex/self)       │
│    2. Parse findings as JSON                         │
│    3. For each finding:                              │
│       - Validate against actual code                 │
│       - Dismiss if false positive (with reasoning)   │
│       - Fix if genuine issue                         │
│    4. Commit fixes                                   │
│    5. Re-run tests                                   │
│    6. Exit if clean or no progress                   │
└──────────────────────────────────────────────────────┘
```

## Configuration

Defined in `src/adw/models/command.py` as `ValidateCommandConfig`:

```yaml
# Default config.yaml
enable_evidence: true        # Run evidence validator
enable_review: true          # Run code review validator
enable_tests: true           # Run test validator
test_timeout_seconds: 300    # Test execution timeout
review_focus:                # Code review focus areas
  - security
  - error_handling
  - edge_cases
max_iterations: 5            # Max validation loop iterations
max_fix_attempts_per_issue: 2
stall_threshold: 2           # Iterations without progress before exit
triage_mode: "auto"          # auto | manual | hybrid
auto_dismiss_info: true      # Auto-dismiss info-level issues
timeout_seconds: 600         # Overall phase timeout
```

## Output: Structured JSON Result

The LLM outputs a structured JSON result embedded in `validate_output.md`:

```json
{
  "passed": true,
  "tests_passed": true,
  "code_review_passed": true,
  "issues_fixed": [
    "Fixed null check in auth handler",
    "Fixed race condition in cache"
  ],
  "issues_remaining": [],
  "summary": "All tests pass, code review clean, 2 issues fixed"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `passed` | bool | Overall validation pass/fail |
| `tests_passed` | bool | All tests passing |
| `code_review_passed` | bool | Code review found no issues |
| `issues_fixed` | list | One-line summaries of fixed issues |
| `issues_remaining` | list | One-line summaries of remaining issues |
| `summary` | string | Human-readable summary |

## Artifact Directory Structure

```
.adw/runs/<run_id>/artifacts/validate/
├── validate_output.md       # LLM response with JSON result
└── validate_tool_calls.json # Tool calls made (if any)
```

## How Downstream Phases Use Validate Output

| Phase | Variable | Purpose |
|-------|----------|---------|
| document | `{{artifacts.validate.validate_output}}` | Validation evidence for docs |
| ship | `{{artifacts.validate.*}}` | Gate shipping on validation pass |

## Code Review Finding Format

Each finding from the code review has this structure:

```json
{
  "severity": "HIGH",           // HIGH | MEDIUM | LOW
  "file": "src/auth/handler.py",
  "line": 42,
  "issue": "Missing null check before accessing user.email",
  "suggested_fix": "Add `if user is None: return None` guard",
  "category": "error-handling"  // bug | security | logic | error-handling | pattern | incomplete | test
}
```

## Default Validate Command Structure

```
src/adw/defaults/commands/validate/
├── prompt.md                  # Main prompt template
├── config.yaml                # Phase configuration
└── code-review-loop/          # Workflow files
    ├── workflow.yaml          # Workflow config
    └── instructions.xml       # Detailed execution steps (~400 lines)
```

## Key Source Files

| File | Role |
|------|------|
| `src/adw/core/phase_runner.py` | Phase execution, artifact loading/saving |
| `src/adw/core/orchestrator.py` | Phase sequencing |
| `src/adw/models/command.py` | `ValidateCommandConfig` model |
| `src/adw/validation/phase.py` | `ValidationPhase` class |
| `src/adw/validation/models.py` | `ValidationResult` model |
| `src/adw/defaults/commands/validate/prompt.md` | Default validate prompt |
| `src/adw/defaults/commands/validate/code-review-loop/instructions.xml` | Workflow logic |

## Phase Connections

```
┌────────┐        ┌────────┐        ┌──────────┐        ┌──────────┐
│  plan  │───────▶│ build  │───────▶│ VALIDATE │───────▶│ document │
└────────┘        └────────┘        └──────────┘        └──────────┘
                       │                  │                   │
                       │                  │                   │
                  provides:          consumes:            consumes:
                  - diff.txt         - plan_output        - validate_output
                  - build_output     - diff.txt           (validation evidence)
                  - diff_stats       - build_output
```
