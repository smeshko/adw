# Story ISS-037: PR Title Missing Description When Feature Description Equals Task ID

<!-- TEMPLATE SECTION: story_header -->
Status: done
Linear Issue: not-configured
Epic: N/A - Standalone UX Fix
Created: 2026-01-21

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a **developer using ADW with Linear integration**,
I want **the PR title to include a meaningful description when I provide only a task ID**,
so that **my pull requests are descriptive and useful without manual editing**.

## Acceptance Criteria

- [ ] **AC1**: When `feature_description` equals `task_id` AND `task_info.title` is available, use `task_info.title` for PR title
  - Given: `feature_description = "RULE-151"`, `task_id = "RULE-151"`, `task_info.title = "Add remote configuration module"`
  - Then: PR title should be `"RULE-151: Add remote configuration module"`

- [ ] **AC2**: When `feature_description` equals `task_id` AND `task_info` is NOT available, fallback gracefully to just the task ID
  - Given: `feature_description = "RULE-151"`, `task_id = "RULE-151"`, `task_info = None`
  - Then: PR title should be `"RULE-151"`

- [ ] **AC3**: When `feature_description` does NOT equal `task_id`, maintain existing behavior
  - Given: `feature_description = "Add user auth"`, `task_id = "RULE-151"`
  - Then: PR title should be `"RULE-151: Add user auth"` (unchanged from current behavior)

- [ ] **AC4**: PR title truncation at 72 chars still applies after the fix

- [ ] **AC5**: Both `auto_create_pr()` and `pr()` command use consistent title generation logic

## Tasks / Subtasks

### Task 1: Implement PR Title Generation Fix in auto_create_pr()
**File:** `src/adw/cli/pr.py`
**Lines:** 411-419

- [ ] Add check: `if context.task_id and context.feature_description == context.task_id`
- [ ] If true and `context.task_info and context.task_info.title`: use `f"{context.task_id}: {context.task_info.title}"`
- [ ] If true but no `task_info.title`: use just `context.task_id`
- [ ] Maintain truncation logic (max 72 chars)

### Task 2: Apply Same Fix to pr() CLI Command
**File:** `src/adw/cli/pr.py`
**Lines:** 735-738

- [ ] Ensure `pr()` CLI command uses same title generation logic
- [ ] The CLI command currently doesn't check for task_id at all - it just uses feature_description
- [ ] Consider extracting title generation to a helper function for DRY

### Task 3: Add Unit Tests
**File:** `tests/unit/cli/test_pr.py`

- [ ] Test: PR title uses task_info.title when feature_description equals task_id
- [ ] Test: PR title falls back to task_id when task_info is None
- [ ] Test: PR title uses feature_description when it differs from task_id
- [ ] Test: Title truncation still works correctly

### Task 4: Optional Enhancement - Info Logging
**File:** `src/adw/cli/pr.py` or logging in orchestrator

- [ ] (Optional) Add info log when using task_info.title as fallback
- [ ] Log should indicate: "Using task title from Linear as PR description"

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->
**From CONDITIONAL_DOCS.md:**

- `_bmad-output/data-models-root.md` - Contains TaskInfo model documentation
- `_bmad-output/development-guide.md` - CLI development patterns
- `_bmad-output/api-contracts-root.md` - Webhook/PR integration patterns

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->

**Root Cause Analysis:**

The bug occurs in `src/adw/cli/pr.py` at lines 411-419 in `auto_create_pr()`:

```python
# Current (buggy) implementation:
pr_title = context.feature_description  # "RULE-151"
if context.task_id:
    # Format: "TASK-123: description"
    pr_title = f"{context.task_id}: {context.feature_description}"  # "RULE-151: RULE-151"

if len(pr_title) > 72:
    pr_title = pr_title[:69] + "..."  # Gets truncated to just "RULE-151"
```

When user runs `adw run "RULE-151"`:
1. `feature_description = "RULE-151"` (the input)
2. `task_id = "RULE-151"` (detected from Linear)
3. `task_info.title = "Add remote configuration module"` (fetched from Linear)
4. Title becomes `"RULE-151: RULE-151"` which gets truncated to `"RULE-151"` (useless)

**The Solution:**

Check if `feature_description == task_id` and use `task_info.title` instead:

```python
# Fixed implementation:
pr_title = context.feature_description

# If feature_description is just the task ID, try to use the task title instead
if context.task_id and context.feature_description == context.task_id:
    if context.task_info and context.task_info.title:
        pr_title = f"{context.task_id}: {context.task_info.title}"
    else:
        pr_title = context.task_id  # Fallback to just the ID
elif context.task_id:
    # Normal case: prefix with task ID
    pr_title = f"{context.task_id}: {context.feature_description}"

if len(pr_title) > 72:
    pr_title = pr_title[:69] + "..."
```

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->

**Project Patterns to Follow:**

1. **Python 3.13+ Modern Syntax**: Use `|` for type unions, not `Optional[]`
2. **Pydantic Models**: `RunContext` and `TaskInfo` are Pydantic models - use their attributes directly
3. **Immutable Updates**: Don't mutate context - just read from it
4. **Structured Logging**: If adding logs, use `logger.info("msg", key=value)` format
5. **Rich for CLI Output**: Not applicable here (internal logic change)

**From project-context.md:**
- Exception hierarchy: Not raising exceptions here, just handling data
- Type annotations: Ensure any new code has full annotations
- Test location: Tests go in `tests/unit/cli/test_pr.py` (already exists)

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->

**Dependencies Used:**
- `pydantic`: `RunContext`, `TaskInfo` models from `adw.models`
- No new dependencies required

**Models Involved:**

1. **RunContext** (`src/adw/models/context.py`):
   - `feature_description: str` - User-provided feature description
   - `task_id: str | None` - Task ID from external system
   - `task_info: TaskInfo | None` - Full task information from Linear

2. **TaskInfo** (`src/adw/models/task.py`):
   - `id: str` - Internal UUID
   - `identifier: str` - Full identifier (e.g., "RULE-123")
   - `title: str` - Task title from Linear
   - `description: str | None` - Task description

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->

**Files to Modify:**

| File | Change Type | Description |
|------|-------------|-------------|
| `src/adw/cli/pr.py` | Edit | Fix PR title generation in `auto_create_pr()` and `pr()` |
| `tests/unit/cli/test_pr.py` | Edit | Add tests for new title generation logic |

**Files NOT to Touch:**
- `src/adw/models/context.py` - No model changes needed
- `src/adw/models/task.py` - No model changes needed
- `src/adw/core/orchestrator.py` - PR creation calls `auto_create_pr()`, no changes needed there

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->

**Test File:** `tests/unit/cli/test_pr.py`

**Existing Test Class to Extend:** `TestAutoCreatePr`

**Tests to Add:**

```python
def test_pr_title_uses_task_info_title_when_feature_equals_task_id(
    self,
    sample_pr_description: PRDescription,
    tmp_path: Path,
) -> None:
    """Test PR title uses task_info.title when feature_description equals task_id (ISS-037)."""
    # Context where feature_description == task_id
    context = RunContext(
        run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
        feature_description="RULE-123",  # Same as task_id
        current_phase="document",
        started_at=datetime.now(),
        task_id="RULE-123",
        task_info=TaskInfo(
            id="uuid-123",
            identifier="RULE-123",
            title="Add remote configuration module",
        ),
    )
    # ... setup and assert pr_title == "RULE-123: Add remote configuration module"

def test_pr_title_fallback_when_no_task_info(
    self,
    sample_pr_description: PRDescription,
    tmp_path: Path,
) -> None:
    """Test PR title falls back to task_id when task_info is None (ISS-037)."""
    context = RunContext(
        run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
        feature_description="RULE-123",
        current_phase="document",
        started_at=datetime.now(),
        task_id="RULE-123",
        task_info=None,  # No task info available
    )
    # ... setup and assert pr_title == "RULE-123"
```

**Testing Pattern (from existing tests):**
- Use `@patch("adw.cli.pr.can_auto_create_pr")` to bypass prerequisites
- Use `@patch("adw.cli.pr.create_pr_via_gh")` to capture the title passed
- Assert on `mock_create.call_args[0][0]` to verify the PR title

**Coverage Expectation:** Maintain >80% coverage

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->

**Relevant Previous Work:**

1. **ISS-031 (PR Creation After Document Phase)** - Most recent PR-related fix
   - Moved PR creation timing from post-run to after document phase
   - Added `pr_url` field to RunContext
   - File touched: `src/adw/cli/pr.py`
   - Commit: `589a051`

2. **Story 12.6 (PR-Task Linking)** - Original implementation of task_id in PR title
   - Added the `f"{context.task_id}: {context.feature_description}"` format
   - Added Linear task link to PR body
   - This is the code we're fixing

3. **ISS-026 (Base Branch Configuration)** - Related PR improvements
   - Made base_branch configurable via `git.base_branch` in config
   - Added `_get_base_branch()` helper function

**Learnings from Previous Stories:**
- PR-related changes require thorough testing of edge cases
- Both `auto_create_pr()` and `pr()` CLI command need to stay in sync
- The `task_info` object is reliably populated when `task_id` is detected from Linear

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->

**Recent Commits Affecting `pr.py`:**

```
589a051 fix(ISS-031): Move PR creation to after document phase, before ship (#137)
```

**Files Modified in Recent PR Work:**
- `src/adw/cli/pr.py` - Added `_store_pr_url()`, modified `auto_create_pr()`
- `src/adw/models/context.py` - Added `pr_url` field
- `tests/unit/cli/test_pr.py` - Added tests for `_store_pr_url()`

**Commit Convention:**
```
fix(ISS-037): Use task title in PR when feature_description equals task_id
```

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->

**No External APIs or Libraries:**
This fix is purely internal logic modification. No web research needed.

**Python Version:** 3.13+ (modern syntax like `X | None` instead of `Optional[X]`)

**Testing Framework:** pytest with `@patch` from `unittest.mock`

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: `_bmad-output/project-context.md`

Key patterns and rules from project context:

1. **Naming**: snake_case for functions, PascalCase for classes
2. **Type annotations**: Required on all functions
3. **Exception hierarchy**: Use `ConfigError` with `code`, `message`, `suggestion` (not applicable here)
4. **Structured logging**: `logger.info("msg", key=value)` format
5. **Rich for CLI**: Use `console.print()` (not applicable for this fix)
6. **Package manager**: uv (for running tests)

---

## Dev Notes

- The fix is straightforward: add a conditional check before constructing the PR title
- Both `auto_create_pr()` and `pr()` need the same logic - consider extracting to helper
- The `task_info` object is already fetched and available; no additional API calls needed
- This is a data flow issue, not a missing data issue

### Project Structure Notes

- All PR logic is in `src/adw/cli/pr.py`
- No model changes required
- Tests are in `tests/unit/cli/test_pr.py`

### References

- [Source: src/adw/cli/pr.py#411-419] - Current buggy title generation
- [Source: src/adw/cli/pr.py#735-738] - CLI command title generation
- [Source: src/adw/models/context.py#99-108] - task_id and task_info fields
- [Source: src/adw/models/task.py#12-52] - TaskInfo model with title field
- [Source: tests/unit/cli/test_pr.py#864-915] - Existing task_id in title tests
- [Source: _bmad-output/implementation-artifacts/issues/ISS-037-pr-title-missing-description.md] - Issue details

---

## Dev Agent Record

<!-- TEMPLATE SECTION: story_completion_status -->

### Context Reference

Created by create-story workflow from ISS-037

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- All artifact analysis completed exhaustively
- Developer guardrails and patterns extracted from project-context.md
- Testing patterns documented from existing test_pr.py
- Previous story intelligence gathered from ISS-031 and Story 12.6

### File List

- `src/adw/cli/pr.py` - Primary file to modify
- `tests/unit/cli/test_pr.py` - Test file to extend
