# Epic 17: Validation Phase Simplification

**Goal:** Rework the validation phase so the SDK simply orchestrates a single prompt execution, and the LLM handles the entire validate→fix→re-validate cycle internally.

**Priority:** P1 (Technical Debt / Simplification)
**Dependencies:** Epic 11 (existing implementation to be replaced)
**Triggered By:** Course correction 2026-01-08

---

## Design Philosophy

**Maximum simplicity:**
- SDK calls validation phase ONCE
- `validate/prompt.md` instructs LLM to handle everything:
  - Run tests/linters
  - Review code
  - If fixable issues found → fix them → re-validate
  - Return final result
- No loop logic in SDK code
- No separate fix prompt
- No iteration tracking in Python

**SDK orchestration = minimal:**
```python
def validation_phase(context: RunContext) -> PhaseResult:
    result = executor.execute("validate/prompt.md", context)
    return PhaseResult(
        passed=result.passed,
        issues=result.final_issues,
        artifacts=result.artifacts
    )
```

That's it. ~5 lines.

---

## Target Flow

```
SDK                          LLM (validate/prompt.md)
 │                                    │
 │──── execute prompt ───────────────►│
 │                                    │
 │                              Run tests
 │                              Run linters
 │                              Code review
 │                                    │
 │                              Issues found?
 │                               ├─ no → return passed
 │                               └─ yes ↓
 │                                    │
 │                              Can auto-fix?
 │                               ├─ no → return failed + issues
 │                               └─ yes ↓
 │                                    │
 │                              Apply fixes
 │                              Re-run tests
 │                              Re-run linters
 │                                    │
 │                              Passed?
 │                               ├─ yes → return passed
 │                               └─ no → return failed + issues
 │                                    │
 │◄─────── return result ─────────────│
 │
Done
```

---

## Story 17.1: Remove SDK Validation Loop

As a developer,
I want all validation loop logic removed from the SDK,
So that the codebase is simpler and the LLM handles iteration.

**Acceptance Criteria:**

**Given** the existing validation loop in SDK
**When** this story is complete
**Then** all loop/iteration logic is removed from Python code

**Given** validation phase execution
**When** called by orchestrator
**Then** SDK makes exactly ONE executor call

**Given** validation result
**When** returned from executor
**Then** SDK passes it through without processing

**Tasks:**
- [ ] Remove `ValidationLoop` class/logic
- [ ] Remove iteration counting
- [ ] Remove triage system entirely
- [ ] Remove fix prompt invocation
- [ ] Simplify phase runner to single execute call
- [ ] Remove validation-specific state persistence

---

## Story 17.2: Create Unified Validation Prompt

As a developer,
I want a single validation prompt that handles everything,
So that the LLM manages the validate→fix→re-validate cycle.

**Acceptance Criteria:**

**Given** `validate/prompt.md`
**When** executed
**Then** it instructs the LLM to:
1. Run the test suite (determine correct command)
2. Run linters/type checkers if configured
3. Review the diff for bugs, security issues, bad patterns
4. If issues found and fixable → fix them → re-validate ONCE
5. Return structured result

**Given** the prompt output
**When** returned
**Then** schema is:
```json
{
  "passed": true,
  "tests_passed": true,
  "code_review_passed": true,
  "issues_fixed": [
    "Fixed missing null check in auth handler",
    "Added error handling for API timeout"
  ],
  "issues_remaining": [],
  "summary": "All tests pass, code review clean"
}
```

**Given** issues that cannot be auto-fixed
**When** detected
**Then** LLM returns immediately without attempting fixes

**Given** fix attempt
**When** re-validation still fails
**Then** LLM returns failed with remaining issues (no more attempts)

**Tasks:**
- [ ] Write `validate/prompt.md` with full instructions
- [ ] Define output schema
- [ ] Include rules for `can_auto_fix` determination
- [ ] Test prompt with various scenarios

---

## Story 17.3: Simplify Configuration

As a developer,
I want validation configuration simplified,
So that there are fewer options to manage.

**Acceptance Criteria:**

**Given** validation configuration
**When** defined in project.yaml
**Then** only these options exist:
```yaml
validation:
  enabled: true
  test_command: "pytest"  # or auto-detect
  timeout_seconds: 600    # generous for LLM to do full cycle
```

**Given** removed options
**When** configuration is loaded
**Then** these are gone:
- `max_iterations`
- `max_fix_attempts_per_issue`
- `stall_threshold`
- `triage_mode`
- `auto_dismiss_info`
- `enable_evidence`
- `enable_review`
- `review_focus`

**Tasks:**
- [ ] Update configuration schema
- [ ] Remove unused config handling
- [ ] Update documentation

---

## Story 17.4: Update Phase Result Model

As a developer,
I want the validation phase result model simplified,
So that it matches the new single-call approach.

**Acceptance Criteria:**

**Given** validation phase completes
**When** result is captured
**Then** it includes only:
```python
class ValidationResult(BaseModel):
    passed: bool
    tests_passed: bool
    code_review_passed: bool
    issues_fixed: list[str]       # one-line summaries
    issues_remaining: list[str]   # one-line summaries
    summary: str
```

**Tasks:**
- [ ] Simplify `ValidationResult` model to new schema
- [ ] Remove `ValidationIssue` model (replaced by string summaries)
- [ ] Remove iteration/triage tracking fields
- [ ] Update serialization

---

## The Prompt

```markdown
# Validation Phase

## Context
Feature: {{feature_description}}
Diff: {{git_diff}}

## Your Task

You are validating code changes. Do the following:

1. **Run Tests**
   - Determine the appropriate test command for this project
   - Execute it and capture results

2. **Run Linters** (if configured)
   - Run any configured linters/type checkers
   - Capture violations

3. **Code Review**
   - Review the diff for:
     - Bugs and logic errors
     - Security vulnerabilities
     - Bad patterns or anti-patterns
     - Missing error handling

4. **If Issues Found**
   - Assess: Can ALL issues be fixed with clear, mechanical changes?
   - If YES: Fix them, then re-run tests/linters ONCE
   - If NO: Return immediately with issues listed

5. **Return Result**

## Output Format

Return ONLY this JSON:

```json
{
  "passed": true,
  "tests_passed": true,
  "code_review_passed": true,
  "issues_fixed": [
    "Fixed missing null check in auth handler",
    "Added error handling for API timeout"
  ],
  "issues_remaining": [],
  "summary": "All tests pass, code review clean"
}
```

## Rules

- `passed` = true ONLY if `tests_passed` AND `code_review_passed` are both true
- `issues_fixed` = one-line summaries of issues you fixed (empty if none)
- `issues_remaining` = one-line summaries of issues that couldn't be fixed
- If you fix issues, re-validate ONCE only - do not loop
- If issues require design decisions or clarification → do NOT fix, add to `issues_remaining`
- Maximum one fix attempt, then return whatever state you're in

---

## What Gets Deleted

From the SDK codebase:
- `ValidationLoop` class
- `TriageDecision` enum
- `TriageResult` model
- Iteration counting logic
- Stall detection
- Fix prompt (`fix/prompt.md`)
- Mid-validation state persistence
- Triage prompt/logic
- `max_iterations` config handling
- `max_fix_attempts_per_issue` config handling

**Estimated lines removed:** 200-400

---

## Dependency Flowchart

```
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 1: Start Immediately (PARALLEL)                             ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [17-1] Remove SDK Validation Loop                                ║
║  [17-2] Create Unified Validation Prompt                          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════╗
║  WAVE 2: After 17-1, 17-2                                         ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  [17-3] Simplify Configuration                                    ║
║  [17-4] Update Phase Result Model                                 ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## Success Criteria

- [ ] SDK validation phase = single executor call (~5 lines)
- [ ] No loop logic in Python code
- [ ] No triage system
- [ ] No separate fix prompt
- [ ] Configuration reduced to 3 options
- [ ] 200+ lines of code deleted
- [ ] All existing tests updated/passing

---

## Estimated Effort

| Story | Estimate |
|-------|----------|
| 17-1 Remove SDK Loop | 0.5 day |
| 17-2 Create Unified Prompt | 0.5 day |
| 17-3 Simplify Config | 0.25 day |
| 17-4 Update Result Model | 0.25 day |
| **Total** | **~1.5 days** |

---
