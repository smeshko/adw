# Bugfix ISS-019: Epic 11 Phases Not Unified

Status: ready-for-dev
Linear Issue: not-configured
Epic: 11 - Validation Loop
Created: 2026-01-07

---

## Story

As a pipeline user,
I want the ADW pipeline to execute 4 phases (Plan, Build, Validation, Document) instead of 5,
so that I don't experience duplicate work, wasted tokens, and confusing UX from separate Verify and Validate phases.

## Acceptance Criteria

### AC1: Phase Sequence Updated
**Given** the ADW pipeline configuration
**When** `PHASE_SEQUENCE` is defined in `constants.py`
**Then** it contains exactly 4 phases: `("plan", "build", "validation", "document")`
**And** the old "verify" phase is completely removed

### AC2: Platform Detection Moved
**Given** the validation phase starts executing
**When** the orchestrator processes the phase
**Then** platform detection runs at validation phase start (not verify)
**And** `context.platform` is set correctly

### AC3: Evidence Gathering Consolidated
**Given** the validation phase executes
**When** evidence needs to be gathered
**Then** evidence is gathered exactly once (not twice)
**And** evidence manifest is created in correct location

### AC4: Verify Defaults Removed
**Given** the defaults directory structure
**When** examining `src/adw/defaults/commands/`
**Then** the `verify/` directory does not exist
**And** only `plan/`, `build/`, `validate/` (or `validation/`), and `document/` remain

### AC5: All Tests Pass
**Given** all code changes are complete
**When** running `pytest`
**Then** all tests pass
**And** no references to the old "verify" phase cause failures

### AC6: Type Checking Passes
**Given** all code changes are complete
**When** running `mypy src/adw`
**Then** no type errors are reported

## Tasks / Subtasks

### Task 1: Update PHASE_SEQUENCE constant
- [x] Edit `src/adw/core/constants.py`
- [x] Change from 5 phases to 4 phases
- [x] Update comment to reflect new sequence

### Task 2: Update orchestrator phase hooks
- [x] Edit `src/adw/core/orchestrator.py`
- [x] Change `if phase == "verify"` to `if phase == "validate"` at line ~1179-1181
- [x] Change evidence gathering hook at line ~1189-1191
- [x] Change evidence optimization hook at line ~1193-1195
- [x] Renamed methods: `_gather_evidence_after_verify` → `_gather_evidence`, `_optimize_evidence_after_verify` → `_optimize_evidence`

### Task 3: Update phase runner
- [x] Edit `src/adw/core/phase_runner.py`
- [x] Change `if phase == "verify"` to `if phase == "validate"` at line ~1026
- [x] Update `_capture_evidence_manifest` method phase check and artifact storage

### Task 4: Delete verify defaults
- [x] Delete directory `src/adw/defaults/commands/verify/`
- [x] Verify no imports reference this directory

### Task 5: Update evidence validator paths
- [x] Edit `src/adw/validation/validators/evidence_validator.py`
- [x] Update primary path to `artifacts/validate/`, keep `artifacts/verify/` for backwards compat

### Task 6: Update other source files with verify references
Files checked and updated:
- [x] `src/adw/core/artifact_manager.py`
- [x] `src/adw/core/index_manager.py`
- [x] `src/adw/core/interruption.py` (fixed _PHASE_ORDER)
- [x] `src/adw/core/orchestrator.py` (docstrings)
- [x] `src/adw/cli/progress.py` (PHASE_COLORS)
- [x] `src/adw/cli/status_display.py`
- [x] `src/adw/cli/app.py`
- [x] `src/adw/hooks/git_commit.py`
- [x] `src/adw/exceptions.py`
- [x] `src/adw/models/context.py`
- [x] `src/adw/models/evidence.py`
- [x] `src/adw/evidence/__init__.py`
- [x] `src/adw/evidence/cli_capture.py`
- [x] `src/adw/evidence/cli_gatherer.py`
- [x] `src/adw/evidence/api_capture.py`
- [x] `src/adw/defaults/commands/validate/config.yaml`
- [x] `src/adw/defaults/commands/document/prompt.md`

### Task 7: Update test files
Test files updated to remove verify phase references:
- [x] `tests/unit/core/test_orchestrator.py` - Fixed phase sequence and renamed test
- [x] `tests/unit/core/test_constants.py` - Removed per ADR-001 (enum existence test)
- [x] `tests/unit/core/test_interruption.py` - Fixed _PHASE_ORDER and resume tests
- [x] `tests/unit/core/test_artifact_passing.py` - Changed verify to validate
- [x] `tests/unit/core/test_artifact_manager.py` - Changed verify to validate
- [x] `tests/unit/validation/test_integration.py` - Fixed phase_history
- [x] `tests/unit/validation/validators/test_evidence_validator.py`
- [x] `tests/unit/cli/test_progress.py` - Removed verify from PHASE_COLORS
- [x] `tests/unit/cli/test_dry_run.py` - Fixed phase sequences
- [x] `tests/unit/cli/test_run.py` - Fixed --phase verify to validate
- [x] `tests/unit/commands/test_bundled_commands.py` - Removed verify test
- [x] `tests/integration/cli/test_progress_integration.py` - Fixed phase checks
- [x] `tests/integration/core/test_artifact_flow_integration.py`
- [x] `tests/integration/core/test_artifact_manager_integration.py`
- [x] `tests/integration/test_document_phase.py` - Fixed verify_dir to validate_dir
- [x] `tests/fixtures/runs/completed_run/context.json`
- [x] Many other test files with verify references (batch sed updates)

### Task 8: Run tests and fix failures
- [x] Run `pytest` and fix all failures
  - Fixed test_orchestrator.py: retry tests (7->6 and 6->5 calls, 5->4 phase completed)
  - Fixed test_progress.py: phase number assertions (3/5->3/4, 20%->25%)
  - Fixed pipeline summary test to remove verify phase references
- [ ] Run `mypy src/adw` and fix type errors
- [ ] Run `ruff check src/adw` and fix linting errors

---

## Relevant Feature Documentation

### ADR-001: Test Reduction Strategy
When updating tests, follow the guidelines:
- **DO write tests for:** Validation logic, business rules, security, I/O, edge cases
- **DON'T write tests for:** Enum existence (like phase count), simple attributes
- Consolidate redundant test variants with `@pytest.mark.parametrize`

---

## Developer Context

### Technical Requirements

| Component | Requirement |
|-----------|-------------|
| Python | 3.13+ with modern syntax |
| Type Hints | Required on all functions |
| Testing | pytest, >80% coverage maintained |
| Linting | ruff, mypy strict |
| Package Manager | uv (NOT pip) |

### Architecture Compliance

**PHASE_SEQUENCE is immutable tuple** - This is intentional to prevent accidental modification.

**Phase execution order is critical** - The orchestrator relies on phase ordering for:
- Artifact passing between phases
- State persistence and resume
- Progress display
- Context management

**Pydantic model updates must use `model_copy()`**:
```python
# CORRECT
context = context.model_copy(update={"platform": platform_value})

# WRONG
context.platform = platform_value  # Loses audit trail
```

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Pydantic | 2.12+ | Models, validation |
| Rich | 14.1.0 | CLI output, progress |
| PyYAML | 6.0+ | Config parsing |

### File Structure Requirements

**Core orchestration:**
```
src/adw/core/
├── constants.py          # PHASE_SEQUENCE definition
├── orchestrator.py       # Phase execution hooks
├── phase_runner.py       # Individual phase execution
├── artifact_manager.py   # Artifact storage
└── index_manager.py      # Run indexing
```

**Validation module:**
```
src/adw/validation/
├── phase.py              # ValidationPhase class
├── config.py             # ValidationConfig
├── validators/
│   ├── evidence_validator.py
│   ├── review_validator.py
│   └── test_validator.py
└── state_manager.py      # Validation state persistence
```

**Defaults to modify:**
```
src/adw/defaults/commands/
├── plan/                 # Keep
├── build/                # Keep
├── verify/               # DELETE this directory
├── validate/             # Keep (or rename to validation/)
└── document/             # Keep
```

### Testing Requirements

**Test naming convention:**
```
test_<unit>_<behavior>_<condition>
```

**Example test updates:**
```python
# BEFORE
def test_phase_sequence_has_five_phases():
    assert len(PHASE_SEQUENCE) == 5

# AFTER - DELETE this test (per ADR-001: Enum Existence Tests are waste)
# The definition in constants.py is the source of truth

# BEFORE
def test_verify_phase_gathers_evidence():
    ...

# AFTER
def test_validation_phase_gathers_evidence():
    ...
```

**Files mirroring source:**
- `tests/unit/core/test_constants.py` → `src/adw/core/constants.py`
- `tests/unit/core/test_orchestrator.py` → `src/adw/core/orchestrator.py`

---

## Previous Story Intelligence

### From Epic 11 Stories (11.1 - 11.7)

**What was implemented:**
- ValidationPhase class with Evidence, Review, Test validators
- ValidationIssue model with source, severity, triage
- Issue triage system (FIX, DISMISS, DEFER)
- Fix iteration loop with max attempts
- Validation state persistence for resume
- Validation report generation

**What was missed (root cause of ISS-019):**
- PHASE_SEQUENCE was NOT updated from 5 to 4 phases
- "verify" phase was NOT removed
- Story 11.1 completion notes incorrectly stated "validate already exists so no modification needed"

**Lesson learned:**
When Epic documentation explicitly states a flow change (5 phases → 4 phases), the PHASE_SEQUENCE constant MUST be updated as part of the implementation.

---

## Git Intelligence

### Recent Commits
```
314aa3a feat(ISS-018): Preserve worktree for single-phase runs (#84)
fcce15c Update build prompt with dev-story workflow
a18b62a Update default plan prompt and report issue
527174d Fixes
c5b17c0 [adw] Plan: Add user authentication
27a5818 feat(ISS-016): Per-Phase Config.yaml Loading (#83)
996e193 feat(ISS-015): Phase-Specific Input Context Injection (#82)
```

### Commit Pattern
- Use `fix(ISS-019):` prefix for this bugfix
- Example: `fix(ISS-019): Unify verify/validate phases into single validation phase`

### Files Recently Modified
- `src/adw/core/orchestrator.py` - Multiple ISS fixes
- `src/adw/core/constants.py` - Rarely touched (high risk)
- `src/adw/defaults/commands/` - Phase configs

---

## Latest Technical Information

No external API or library changes required. This is an internal refactoring of existing code.

**Note on backwards compatibility:**
- Existing runs with "verify" artifacts should still be loadable
- The EvidenceValidator already has fallback path logic
- Consider adding fallback for `artifacts/verify/` → `artifacts/validation/` during transition

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:

1. **Naming Conventions:** Classes=PascalCase, functions/variables=snake_case, constants=SCREAMING_SNAKE_CASE
2. **Models in models/:** All Pydantic models must live in `src/adw/models/`
3. **Exception Hierarchy:** Use `ADWError` subclasses, never bare `Exception`
4. **Type Annotations Required:** Full annotations on all functions
5. **Rich for CLI Output:** Use `console.print()` not `print()`
6. **Structured Logging:** `logger.info("msg", extra={"key": value})`
7. **Immutable State Updates:** Use `model_copy(update={...})`

---

## Dev Notes

### Critical Implementation Notes

1. **Phase naming decision:** The code currently uses "validate" as the phase name. Epic 11 documentation uses "Validation Loop" terminology. Choose ONE:
   - Option A: Keep `"validate"` as phase name (minimal changes)
   - Option B: Rename to `"validation"` (more aligned with epic, more changes)
   - **Recommendation:** Option A - keep `"validate"` to minimize risk

2. **Evidence gathering sequence:**
   ```
   CURRENT (broken):
   verify phase → platform detect → LLM prompt → evidence gather → evidence optimize
   validate phase → EvidenceValidator (reads manifest from verify) → ReviewValidator → TestValidator

   FIXED:
   validation phase → platform detect → evidence gather → evidence optimize → validators
   ```

3. **Method renaming (optional but recommended):**
   - `_detect_and_store_platform` - Keep name (generic)
   - `_gather_evidence_after_verify` → `_gather_evidence` or `_gather_evidence_after_build`
   - `_optimize_evidence_after_verify` → `_optimize_evidence`

### Source Tree Components to Touch

| File | Change Type | Risk |
|------|-------------|------|
| `src/adw/core/constants.py` | Edit PHASE_SEQUENCE | HIGH - affects entire pipeline |
| `src/adw/core/orchestrator.py` | Edit phase checks | MEDIUM |
| `src/adw/core/phase_runner.py` | Edit phase check | LOW |
| `src/adw/defaults/commands/verify/` | DELETE directory | LOW |
| `src/adw/validation/validators/evidence_validator.py` | Edit paths | LOW |
| 10+ source files | Edit "verify" refs | LOW |
| 30+ test files | Edit "verify" refs | MEDIUM |

### Testing Standards Summary

- Run `pytest` - all must pass
- Run `mypy src/adw` - no type errors
- Run `ruff check src/adw` - no lint errors
- Coverage must remain >80%

### References

| Document | Path |
|----------|------|
| Issue Report | `_bmad-output/implementation-artifacts/issues/ISS-019-epic-11-phases-not-unified.md` |
| Epic 11 | `_bmad-output/epics/epic-11-validation-loop.md` |
| Constants | `src/adw/core/constants.py:11-17` |
| Orchestrator Verify Hooks | `src/adw/core/orchestrator.py:1179-1195` |
| ValidationPhase | `src/adw/validation/phase.py:44-387` |
| EvidenceValidator | `src/adw/validation/validators/evidence_validator.py:49-149` |
| Project Context | `_bmad-output/project-context.md` |
| Test Reduction ADR | `docs/architecture/adrs/ADR-001-test-reduction-strategy.md` |

---

## Dev Agent Record

### Context Reference

- Issue: ISS-019-epic-11-phases-not-unified.md
- Epic: epic-11-validation-loop.md

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- All artifact analysis exhaustive (issue, epic, codebase patterns, project context, conditional docs)
- Developer guardrails extracted from architecture and project context
- Git intelligence analyzed for commit patterns
- Testing requirements aligned with ADR-001

### File List

Files to CREATE:
- None

Files to MODIFY:
- `src/adw/core/constants.py`
- `src/adw/core/orchestrator.py`
- `src/adw/core/phase_runner.py`
- `src/adw/validation/validators/evidence_validator.py`
- `src/adw/core/artifact_manager.py`
- `src/adw/core/index_manager.py`
- `src/adw/core/interruption.py`
- `src/adw/cli/progress.py`
- `src/adw/cli/dry_run.py`
- `src/adw/cli/status_display.py`
- `src/adw/hooks/git_commit.py`
- `src/adw/exceptions.py`
- 30+ test files

Files to DELETE:
- `src/adw/defaults/commands/verify/config.yaml`
- `src/adw/defaults/commands/verify/prompt.md`
- `src/adw/defaults/commands/verify/` (directory)
