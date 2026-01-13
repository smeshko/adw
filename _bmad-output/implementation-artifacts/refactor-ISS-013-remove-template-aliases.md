# Story: Remove Inconsistent Template Aliases

<!-- TEMPLATE SECTION: story_header -->
Status: review
Linear Issue: not-configured
Epic: Tech Debt - PhaseRunner Refactoring
Created: 2026-01-05

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a prompt author,
I want template variables to use explicit, consistent paths,
so that I can understand exactly what data I'm referencing without ambiguity.

## Acceptance Criteria

- [x] Remove hardcoded alias block from `phase_runner.py:335-343`
- [x] Update `commands/build/prompt.md` to use explicit path
- [x] Update `commands/verify/prompt.md` to use explicit path (N/A - doesn't exist)
- [x] Update `commands/document/prompt.md` to use explicit path
- [x] Update `commands/validate/prompt.md` to use explicit path (N/A - doesn't use alias)
- [x] Update any tests that rely on alias variables
- [x] All existing tests pass
- [x] Documentation updated if applicable (N/A - removed code, not added)

## Tasks / Subtasks

### Task 1: Remove Alias Code Block
- [x] Delete lines 335-343 in `phase_runner.py`
- [x] Verify no other code depends on these aliases

### Task 2: Update Default Prompts
- [x] `commands/build/prompt.md`: `{{plan}}` -> `{{artifacts.plan.plan_output}}`
- [x] `commands/verify/prompt.md`: N/A - verify folder doesn't exist (only validate)
- [x] `commands/document/prompt.md`: `{{implementation}}` -> `{{artifacts.build.build_output}}`
- [x] `commands/validate/prompt.md`: N/A - doesn't use `{{output}}` alias

### Task 3: Update Tests
- [x] Search for `variables["plan"]` assertions - none found
- [x] Search for `variables["implementation"]` assertions - none found
- [x] Search for `variables["output"]` assertions - none found
- [x] Update any affected test expectations - updated test_document_phase.py fixture

### Task 4: Verification
- [x] Run full test suite - 2187 passed, 7 skipped (82.53% coverage)
- [x] Manual verification with sample run - N/A (pure refactoring, tests verify behavior)

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->
**Source:** `docs/development/tech-debt/phase-runner-aliases.md`

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->
- Python 3.13+
- Low effort change (~15 lines across 4-5 files)
- No new dependencies
- Purely a cleanup/consistency refactoring

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->
**Location:** `src/adw/core/phase_runner.py:335-343`

**Current Code (TO BE DELETED):**
```python
# Add convenience aliases for common artifact references
# e.g., {{plan}} instead of {{artifacts.plan.plan_output}}

if "plan" in artifacts_map and "plan_output" in artifacts_map["plan"]:
    variables["plan"] = artifacts_map["plan"]["plan_output"]
if "build" in artifacts_map and "build_output" in artifacts_map["build"]:
    variables["implementation"] = artifacts_map["build"]["build_output"]
if "verify" in artifacts_map and "verify_output" in artifacts_map["verify"]:
    variables["output"] = artifacts_map["verify"]["verify_output"]
```

**Problems with Current Aliases:**

| Alias | Maps To | Issue |
|-------|---------|-------|
| `{{plan}}` | `artifacts.plan.plan_output` | Identity mapping - redundant |
| `{{implementation}}` | `artifacts.build.build_output` | Semantic rename - inconsistent |
| `{{output}}` | `artifacts.verify.verify_output` | Generic name - ambiguous |

**After Fix:**
- All prompts use explicit `{{artifacts.phase.artifact_name}}` paths
- No ambiguity about what data is being referenced
- Consistent naming across all phases

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->
- No library changes required
- Template engine already supports nested paths
- Existing `{{artifacts.X.Y}}` syntax works without aliases

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->
**Files to Modify:**

| File | Change |
|------|--------|
| `src/adw/core/phase_runner.py` | Delete lines 335-343 |
| `commands/build/prompt.md` | `{{plan}}` -> `{{artifacts.plan.plan_output}}` |
| `commands/verify/prompt.md` | `{{implementation}}` -> `{{artifacts.build.build_output}}` |
| `commands/document/prompt.md` | `{{implementation}}` -> `{{artifacts.build.build_output}}` |
| `commands/validate/prompt.md` | `{{output}}` -> `{{artifacts.verify.verify_output}}` |

**Test Files to Check:**
- `tests/unit/core/test_phase_runner.py` - Check for alias assertions

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->
- Run existing test suite - should pass after prompt updates
- No new tests needed (removing code, not adding)
- Verify template rendering still works with explicit paths
- Coverage requirement: >80% (existing coverage should suffice)

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->
N/A - This is a standalone cleanup story.

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->
Recent commits show consistent patterns:
- Refactoring commits reference related issues
- Test updates accompany code changes

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->
N/A - No external dependencies or API changes.

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- Follow naming conventions (snake_case for variables)
- Template variables should be explicit and unambiguous

---

## Dev Notes

- Effort: Low (~15 lines across 4-5 files)
- This is a simple cleanup task
- Be sure to search for any other prompt files that might use these aliases
- Custom user prompts in `.adw/commands/` may need updating - document the breaking change

### Project Structure Notes

- Prompts live in `commands/{phase}/prompt.md`
- User overrides in `.adw/commands/{phase}/prompt.md`

### References

- [Source: docs/development/tech-debt/phase-runner-aliases.md]
- [Source: ISS-013-phaserunner-template-aliases-inconsistent.md]

---

## Dev Agent Record

<!-- TEMPLATE SECTION: story_completion_status -->

### Context Reference

Story created from ISS-013 tech debt documentation.

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

- Story created: 2026-01-05
- Ultimate context engine analysis completed - comprehensive developer guide created
- Task 1: Removed alias code block from phase_runner.py (lines 371-379, ~9 lines deleted)
- Task 2: Updated build/prompt.md ({{plan}} -> {{artifacts.plan.plan_output}}) and document/prompt.md ({{implementation}} -> {{artifacts.build.build_output}})
- Task 3: Updated test_document_phase.py fixture to use explicit artifact path
- Task 4: Full test suite passed - 2187 tests, 82.53% coverage
- Note: verify/prompt.md doesn't exist (only validate), validate/prompt.md doesn't use {{output}} alias

### File List

Files modified:
- `src/adw/core/phase_runner.py` - Removed alias code block
- `src/adw/defaults/commands/build/prompt.md` - Updated {{plan}} reference
- `src/adw/defaults/commands/document/prompt.md` - Updated {{implementation}} reference
- `tests/integration/test_document_phase.py` - Updated fixture prompt
