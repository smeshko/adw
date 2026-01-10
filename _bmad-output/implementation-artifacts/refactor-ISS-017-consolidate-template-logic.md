# Story 13.ISS-017: Consolidate Template Logic

Status: ready-for-dev
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure (Tech Debt)
Created: 2026-01-10

---

## Story

As a **developer maintaining the ADW SDK**,
I want **template-related logic consolidated in the template module with clear extension points**,
so that **template logic changes only require updates in one place, improving maintainability and testability**.

## Acceptance Criteria

- [ ] `ARTIFACT_REF_PATTERN` in `phase_runner.py` is either:
  - Moved to `template.py` and imported, OR
  - Delegated to TemplateEngine via a method call
- [ ] `_validate_artifact_references()` logic is moved to TemplateEngine (or a validation hook/extension point in TemplateEngine)
- [ ] State mutation pattern for `command_root`/`shared_root` is replaced with parameters passed to `render()` method
- [ ] All existing tests pass
- [ ] No behavioral changes - this is a pure refactoring story

## Tasks / Subtasks

### Task 1: Move ARTIFACT_REF_PATTERN to TemplateEngine
- [x] Add `ARTIFACT_REF_PATTERN` constant to `template.py` (or create method `find_artifact_references()`)
- [x] Import/use the pattern from TemplateEngine in `phase_runner.py`
- [x] Remove duplicate pattern definition from `phase_runner.py:55`

### Task 2: Move Artifact Validation to TemplateEngine
- [x] Create `validate_artifact_references()` method in TemplateEngine class
- [x] Move logic from `phase_runner.py:589-661` to new method
- [x] Update PhaseRunner to call the new method instead of inline validation
- [x] Consider: Create optional `ArtifactValidator` protocol/hook for extensibility (not needed - simple function is sufficient)

### Task 3: Refactor State Mutation to Parameter Passing
- [ ] Add `command_root` and `shared_root` parameters to `TemplateEngine.render()` method
- [ ] Remove lines 389-390 in `phase_runner.py` that mutate instance state
- [ ] Pass roots as parameters in the `render()` call instead
- [ ] Update all callers of `render()` to pass the new parameters (if any other callers exist)

### Task 4: Update Tests
- [ ] Ensure unit tests in `tests/unit/commands/test_template.py` cover new methods
- [ ] Ensure unit tests in `tests/unit/core/test_phase_runner.py` still pass
- [ ] Add tests for the new `validate_artifact_references()` method

### Task 5: Verify Integration
- [ ] Run full test suite: `uv run pytest`
- [ ] Verify no regressions in template rendering behavior
- [ ] Verify artifact reference validation still works in strict mode

---

## Relevant Feature Documentation

No matching conditional docs found for this story context.

---

## Developer Context

### Technical Requirements

**Issue Classification:** Tech Debt / Minor
**Impact:** Internal maintainability only, no user-facing changes

This refactoring addresses three specific code smells:

1. **Duplicated Pattern Matching** (`phase_runner.py:55`)
   ```python
   # Currently in phase_runner.py
   ARTIFACT_REF_PATTERN = re.compile(r"\{\{artifacts\.([a-z_][a-z0-9_.]*(?:\.\*)?)\}\}")
   ```
   This pattern duplicates template-matching concepts that belong in `template.py`.

2. **Validation Logic in Wrong Place** (`phase_runner.py:589-661`)
   The `_validate_artifact_references()` method validates template syntax but lives in PhaseRunner instead of TemplateEngine.

3. **Awkward State Mutation** (`phase_runner.py:389-390`)
   ```python
   self.template_engine.command_root = command.path
   self.template_engine.shared_root = command.path.parent
   ```
   This mutates instance state before each render instead of passing parameters.

### Architecture Compliance

**From Architecture Document:**
- All template-related logic should be in `src/adw/commands/template.py`
- Template Engine is defined as a "simple regex-based parser"
- State updates should be immutable where possible (Pydantic `model_copy` pattern)

**Module Boundaries:**
- `template.py` - Generic template engine (variable substitution, file inclusion)
- `phase_runner.py` - ADW-specific orchestration (should use template engine, not reimplement)

**Decision:** The architecture doc states templates use simple patterns:
```python
VARIABLE_PATTERN = r'\{\{([a-z_][a-z0-9_.]*)\}\}'
FILE_PATTERN = r'\{\{file:([^}]+)\}\}'
```

The `ARTIFACT_REF_PATTERN` follows the same structure and should be consolidated.

### Library & Framework Requirements

No new libraries required. This is a pure refactoring using existing Python patterns.

### File Structure Requirements

**Files to Modify:**
| File | Changes |
|------|---------|
| `src/adw/commands/template.py` | Add pattern, add validation method, update render() signature |
| `src/adw/core/phase_runner.py` | Remove pattern, remove validation method, update render() call |

**No New Files Required** - consolidation into existing modules.

### Testing Requirements

**Existing Tests:**
- `tests/unit/commands/test_template.py` - TemplateEngine tests
- `tests/unit/core/test_phase_runner.py` - PhaseRunner tests

**Test Strategy:**
1. Add unit tests for new `validate_artifact_references()` method in `test_template.py`
2. Ensure existing tests pass without modification (behavioral equivalence)
3. Run integration tests to verify end-to-end behavior unchanged

**Coverage Requirement:** >80% (existing standard)

---

## Previous Story Intelligence

This is a tech debt story from ISS-017 analysis. Related refactoring stories in Epic 13:
- `refactor-ISS-012-config-driven-artifact-capture` (ready-for-dev)
- `refactor-ISS-013-remove-template-aliases` (ready-for-dev)
- `refactor-ISS-014-centralize-resume-logic` (ready-for-dev)

**Lessons from Similar Refactoring:**
- `refactor-ISS-021-remove-evidence-gathering` (done) - Successful removal of dead code subsystem
- Keep changes minimal and focused
- Ensure tests pass at each step

---

## Git Intelligence

**Recent Commits:**
```
ffca725 Update sprint status
302d1b4 refactor(epic-16): Remove evidence gathering subsystem (ISS-021) (#98)
39f6818 Sync issue
```

**Commit Message Pattern:** `type(scope): description (ISS-XXX) (#PR)`

**For This Story:** Use `refactor(template): consolidate template logic (ISS-017)`

---

## Latest Technical Information

No external web research required. This is a pure Python refactoring using:
- Python `re` module (regex patterns)
- Pydantic BaseModel (for context)
- Standard Python class design patterns

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Naming:** PEP 8 strict (snake_case functions, PascalCase classes)
- **Exceptions:** Use ADWError hierarchy, never bare Exception
- **Type Annotations:** Required on all public functions
- **Testing:** Tests mirror source structure, >80% coverage

---

## Dev Notes

### Key Code Locations

| Current Location | Line(s) | Target Location |
|-----------------|---------|-----------------|
| `phase_runner.py` | 55 | `template.py` |
| `phase_runner.py` | 389-390 | `template.py` render() params |
| `phase_runner.py` | 589-661 | `template.py` new method |

### Implementation Approach

**Option A (Recommended):** Minimal Consolidation
- Move `ARTIFACT_REF_PATTERN` to `template.py`
- Add `validate_artifact_references()` to TemplateEngine
- Add optional params to `render()` for command/shared roots

**Option B:** Extension Point Pattern
- Create `TemplateValidator` protocol
- `ArtifactValidator` implements protocol
- More extensible but potentially over-engineered for this use case

**Recommendation:** Use Option A for simplicity, matching the "don't over-engineer" principle.

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
- No conflicts with existing patterns
- Follows established module boundaries

### References

- [Source: _bmad-output/architecture.md - Template Engine section]
- [Source: _bmad-output/implementation-artifacts/issues/ISS-017-template-logic-scattered-between-modules.md]
- [Source: _bmad-output/project-context.md - Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Moved ARTIFACT_REF_PATTERN from phase_runner.py to template.py with proper import. Removed unused `re` import from phase_runner.py. Added 6 unit tests for pattern matching.
- Task 2: Created standalone `validate_artifact_references()` function in template.py. Removed `_validate_artifact_references()` method from PhaseRunner. Updated call site to use new function. Added 9 unit tests. Updated 4 existing tests in test_artifact_passing.py.

### File List

- `src/adw/commands/template.py` - Added ARTIFACT_REF_PATTERN constant, added validate_artifact_references() function
- `src/adw/core/phase_runner.py` - Removed ARTIFACT_REF_PATTERN, removed _validate_artifact_references(), now imports from template.py
- `tests/unit/commands/test_template.py` - Added TestArtifactRefPattern (6 tests), TestValidateArtifactReferences (9 tests)
- `tests/unit/core/test_artifact_passing.py` - Updated 4 tests to use standalone function

