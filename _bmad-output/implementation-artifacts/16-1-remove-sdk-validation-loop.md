# Story 16.1: Remove SDK Validation Loop

<!-- TEMPLATE SECTION: story_header -->
Status: done
Linear Issue: not-configured
Epic: 16 - Validation Phase Simplification
Created: 2026-01-08

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a developer,
I want all validation loop logic removed from the SDK,
so that the codebase is simpler and the LLM handles iteration.

## Acceptance Criteria

**Given** the existing validation loop in SDK
**When** this story is complete
**Then** all loop/iteration logic is removed from Python code

**Given** validation phase execution
**When** called by orchestrator
**Then** SDK makes exactly ONE executor call

**Given** validation result
**When** returned from executor
**Then** SDK passes it through without processing

## Tasks / Subtasks

- [ ] **Task 1: Remove ValidationLoopController class**
  - Delete `src/adw/validation/loop_controller.py` entirely
  - Remove `ValidationLoopController` from `__init__.py` exports
  - Remove `ExitReason` enum (no longer needed)

- [ ] **Task 2: Remove TriageSystem class**
  - Delete `src/adw/validation/triage.py` entirely
  - Remove `TriageSystem` from `__init__.py` exports
  - Remove `TriageDecision` enum from models.py

- [ ] **Task 3: Remove FixEngine class**
  - Delete `src/adw/validation/fix_engine.py` entirely
  - Remove `FixEngine`, `FixIterationResult`, `FileChange` from exports

- [ ] **Task 4: Remove ValidationStateManager iteration logic**
  - Simplify `src/adw/validation/state_manager.py`
  - Remove `save_iteration_state()` method
  - Remove `load_iteration_state()` method
  - Remove mid-loop state persistence

- [ ] **Task 5: Simplify ValidationPhase**
  - Rewrite `src/adw/validation/phase.py` to single executor call
  - Remove all loop orchestration logic
  - Target: ~5 lines of code for phase execution:
    ```python
    def run(self, context: RunContext) -> PhaseResult:
        result = self.executor.execute("validate/prompt.md", context)
        return PhaseResult(
            passed=result.passed,
            issues=result.final_issues,
            artifacts=result.artifacts
        )
    ```

- [ ] **Task 6: Update tests**
  - Remove tests for deleted classes
  - Add tests for simplified single-call validation
  - Ensure coverage >80% for remaining validation code

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->
**Source:** Epic 11 (Validation Loop) - Being replaced by this simplification

The existing validation system includes:
- `ValidationLoopController` - Orchestrates the iterate-triage-fix cycle
- `TriageSystem` - FIX/DISMISS/DEFER decision making
- `FixEngine` - Applies fixes and re-validates
- `ValidationStateManager` - Persists mid-loop state

All of this is being replaced with a single prompt execution where the LLM handles the entire cycle.

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->
1. **Single executor call**: The validation phase must make exactly one call to the executor
2. **No Python loops**: All iteration logic moves to the prompt, not Python code
3. **Pass-through result**: SDK receives result from LLM and passes it through unchanged
4. **Backward compatibility**: The `ValidationPhase` class interface should remain compatible with orchestrator

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->
<!-- Constraints the developer MUST follow from architecture docs -->

**From project-context.md:**
- All models in `src/adw/models/` - any new result models must go there
- Use exception hierarchy - don't use bare exceptions for validation errors
- Full type annotations required on all functions
- Rich for CLI output when displaying validation results
- Structured logging for validation events

**Validation module structure to preserve:**
```
src/adw/validation/
├── __init__.py        # UPDATE: Remove deleted class exports
├── config.py          # KEEP: Still need basic config
├── models.py          # UPDATE: Simplify (Story 16.4)
├── phase.py           # REWRITE: Single executor call
├── report.py          # UPDATE: Simplify report generation
├── state_manager.py   # SIMPLIFY: Remove iteration state
└── validators/        # KEEP: Validators still used by prompt
```

**Files to DELETE entirely:**
- `loop_controller.py` (~200 lines)
- `triage.py` (~300 lines)
- `fix_engine.py` (~350 lines)

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->
<!-- Specific versions, APIs, and usage patterns -->

| Library | Version | Usage |
|---------|---------|-------|
| Pydantic | 2.12+ | Simplified ValidationResult model |
| Rich | 14.1.0 | Display validation summary |

**Executor interface** (from Epic 3):
```python
# The executor.execute() method signature
def execute(
    self,
    prompt_path: str,
    context: RunContext,
    *,
    timeout: int | None = None,
) -> LLMResult
```

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->
<!-- Where files should be created/modified, naming conventions -->

**Files to DELETE:**
- `src/adw/validation/loop_controller.py`
- `src/adw/validation/triage.py`
- `src/adw/validation/fix_engine.py`

**Files to MODIFY:**
- `src/adw/validation/__init__.py` - Remove deleted exports
- `src/adw/validation/phase.py` - Rewrite to single call
- `src/adw/validation/state_manager.py` - Remove iteration methods
- `src/adw/validation/models.py` - Remove unused models (coordinate with Story 16.4)

**Test files to DELETE/UPDATE:**
- `tests/unit/validation/test_loop_controller.py` - DELETE
- `tests/unit/validation/test_triage.py` - DELETE
- `tests/unit/validation/test_fix_engine.py` - DELETE
- `tests/unit/validation/test_phase.py` - UPDATE for single-call

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->
<!-- Testing standards, frameworks, coverage expectations -->

1. **Unit tests for simplified ValidationPhase:**
   ```python
   def test_validation_phase_single_call():
       """Verify phase makes exactly one executor call."""
       mock_executor = MockExecutor()
       phase = ValidationPhase(executor=mock_executor)

       result = phase.run(context)

       assert mock_executor.call_count == 1
       assert result.passed == mock_executor.last_result.passed
   ```

2. **Integration test with real prompt:**
   - Test that validation prompt can be loaded
   - Test that result parsing works correctly

3. **Coverage requirement:** >80% for `src/adw/validation/`

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->
<!-- Learnings from previous story implementation (if story_num > 1) -->

N/A - This is the first story in Epic 16.

**Context from Epic 11 implementation:**
- The validation loop was implemented across 7 stories
- Total code: ~1500 lines across loop_controller, triage, fix_engine
- Complexity grew significantly with each story
- The triage system alone has 4 decision modes
- State persistence handles mid-iteration resume which adds complexity

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->
<!-- Recent commit patterns, files modified, conventions observed -->

**Recent validation-related commits:**
- `feat(epic-11): Story 11.7 - Validation Report Generation`
- `feat(epic-11): Story 11.6 - Validation State Persistence`
- `feat(epic-11): Story 11.5 - Iteration Limits`

**Commit pattern to follow:**
```
refactor(epic-16): Remove validation loop infrastructure (Story 16.1)

- Delete loop_controller.py, triage.py, fix_engine.py
- Simplify ValidationPhase to single executor call
- Remove iteration state from state_manager.py
- Update exports in __init__.py

Lines removed: ~850
```

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->
<!-- Web research results for current library versions, API changes, best practices -->

**Simplification approach aligns with:**
- Claude Code's native ability to handle iterative tasks
- ADW's principle of "LLM does the work, SDK orchestrates"
- Reduced surface area for bugs and maintenance

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: _bmad-output/project-context.md

Key patterns and rules from project context:
- **Naming:** PascalCase for classes, snake_case for functions
- **Models:** All in `src/adw/models/` (ValidationResult may need to move)
- **Exceptions:** Use ADWError hierarchy, never bare exceptions
- **Types:** Full annotations required, use `X | None` not `Optional[X]`
- **Logging:** Structured logging (`logger.info("msg", key=value)`)

---

## Dev Notes

- This story is about DELETION and SIMPLIFICATION
- The goal is removing ~850 lines of code
- Coordinate with Story 16.2 (prompt creation) - the prompt handles the loop
- Coordinate with Story 16.4 (model updates) - models will be simplified

### Project Structure Notes

- Validation module will shrink from 8 files to 5 files
- No new modules needed - only deletions and simplifications

### References

- [Source: _bmad-output/epics/epic-16-validation-simplification.md#Story 16.1]
- [Source: _bmad-output/epics/epic-11-validation-loop.md] (what's being replaced)
- [Source: src/adw/validation/__init__.py] (current exports)

---

## Dev Agent Record

<!-- TEMPLATE SECTION: story_completion_status -->

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used



### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** None
- **Blocks:** Story 16.3, Story 16.4
- **Can Parallel With:** Story 16.2

### Dependency Rationale
- Story 16.3: Configuration simplification requires knowing what loop-related configs to remove
- Story 16.4: Result model update requires knowing what iteration/triage fields to remove
