# Story 11.4: Fix Iteration Loop

Status: complete
Linear Issue: not-configured
Epic: 11 - Validation Loop
Created: 2026-01-05

---

## Story

As a developer,
I want the system to attempt fixes and re-validate,
so that issues are resolved automatically when possible.

## Acceptance Criteria

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

## Tasks / Subtasks

### Task 1: Create FixEngine Class
- [x] Create `src/adw/validation/fix_engine.py` with `FixEngine` class
- [x] Implement `attempt_fixes(issues: list[ValidationIssue]) -> FixResult`
- [x] Inject LLM executor for fix prompt generation
- [x] Track which validators need re-running per issue

### Task 2: Build Fix Prompt Generator
- [x] Create `_build_fix_prompt(issues: list[ValidationIssue]) -> str`
- [x] Include issue details, location, and context
- [x] Provide code snippets for reference
- [x] Request structured fix response from LLM

### Task 3: Implement Fix Application
- [x] Parse LLM fix response for file modifications
- [x] Apply fixes to files using existing file utilities
- [x] Create backup before applying fixes (atomic operation)
- [x] Rollback on partial failure

### Task 4: Implement Selective Re-validation
- [x] Track which validators are affected by each issue
- [x] Only re-run affected validators after fix
- [x] Map issue source to validator: TEST→TestValidator, etc.
- [x] Aggregate new issues from re-validation

### Task 5: Add Fix Attempt Tracking
- [x] Update `ValidationIssue.fix_attempted` to True
- [x] Increment `ValidationIssue.fix_attempt_count`
- [x] Create `FixAttempt` record with result
- [x] Store in `ValidationIssue.fix_history`

### Task 6: Implement Auto-Defer on Max Attempts
- [x] Check `fix_attempt_count >= max_fix_attempts_per_issue`
- [x] Auto-change triage decision to DEFER
- [x] Set reason: "Max fix attempts reached ({count})"
- [x] Log auto-defer decision for audit

### Task 7: Create Fix Result Model
- [x] Create `FixIterationResult` model with:
  - `issues_fixed: list[str]` (issue IDs)
  - `issues_remaining: list[str]`
  - `issues_deferred: list[str]`
  - `files_modified: list[str]`
  - `validation_rerun: bool`
- [x] Support serialization for state persistence

### Task 8: Write Tests
- [x] Unit tests for FixEngine (5 tests)
- [x] Unit tests for fix prompt generation (5 tests)
- [x] Unit tests for fix application (7 tests)
- [x] Unit tests for selective re-validation (6 tests)
- [x] Unit tests for auto-defer logic (3 tests)
- [x] Unit tests for FixIterationResult (4 tests)
- [x] Unit tests for fix attempt tracking (4 tests)
- [x] Integration test for fix→validate cycle (2 tests)
- **Total: 36 tests, 93% coverage on fix_engine.py**

---

## Dependencies

- **Depends On:** Story 11.2
- **Blocks:** Story 11.5
- **Can Parallel With:** Story 11.3, Story 11.6

### Dependency Rationale
- Story 11.2: Fix loop needs issue tracking metadata (fix_attempted, fix_history)
- Story 11.5: Exit conditions need fix loop behavior to enforce max_fix_attempts limits

---

## Developer Context

### Technical Requirements

1. **LLM Fix Generation**
   - Prompt includes all FIX issues for batch fixing
   - Request specific file/line changes
   - Support multiple fix attempts per issue

2. **Atomic Fix Application**
   - Create backup of files before modification
   - Apply all fixes or none (transaction)
   - Rollback on any failure
   - Preserve file permissions and encoding

3. **Selective Re-validation**
   - Only re-run validators that could verify the fix
   - TEST issues → re-run TestValidator
   - REVIEW issues → re-run ReviewValidator
   - EVIDENCE issues → re-run EvidenceValidator

### Architecture Compliance

**File Location:** `src/adw/validation/fix_engine.py`

**Class Structure:**
```python
# src/adw/validation/fix_engine.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FileChange:
    file_path: Path
    original_content: str
    new_content: str
    line_start: int | None = None
    line_end: int | None = None

@dataclass
class FixIterationResult:
    issues_fixed: list[str]  # Issue IDs
    issues_remaining: list[str]
    issues_deferred: list[str]
    files_modified: list[str]
    validation_rerun: bool
    iteration_number: int

class FixEngine:
    def __init__(
        self,
        llm_executor: LLMExecutor,
        config: ValidationConfig,
        validators: list[Validator],
    ):
        self.llm = llm_executor
        self.config = config
        self.validators = {v.name: v for v in validators}
        self._file_backups: dict[Path, str] = {}

    async def attempt_fixes(
        self,
        issues: list[ValidationIssue],
        context: RunContext,
    ) -> FixIterationResult:
        """Attempt to fix all FIX-triaged issues."""
        # Filter to FIX issues only
        fix_issues = [i for i in issues if i.triage_decision == "FIX"]

        if not fix_issues:
            return FixIterationResult(
                issues_fixed=[],
                issues_remaining=[i.id for i in issues],
                issues_deferred=[],
                files_modified=[],
                validation_rerun=False,
                iteration_number=0,
            )

        # Generate and apply fixes
        prompt = self._build_fix_prompt(fix_issues, context)
        response = await self.llm.execute(prompt)
        changes = self._parse_fix_response(response)

        # Apply fixes atomically
        try:
            self._backup_files(changes)
            self._apply_changes(changes)
        except Exception as e:
            self._rollback()
            raise FixApplicationError(f"Failed to apply fixes: {e}")

        # Re-validate affected validators
        affected_validators = self._get_affected_validators(fix_issues)
        new_issues = await self._revalidate(affected_validators, context)

        # Check which issues are resolved
        resolved, remaining = self._check_resolution(fix_issues, new_issues)

        # Update fix tracking on remaining issues
        for issue in remaining:
            issue.fix_attempt_count += 1
            issue.fix_attempted = True
            issue.last_fix_result = FixResult.FAILED
            issue.fix_history.append(FixAttempt(
                result=FixResult.FAILED,
                notes=f"Attempt {issue.fix_attempt_count} failed",
            ))

            # Auto-defer if max attempts reached
            if issue.fix_attempt_count >= self.config.max_fix_attempts_per_issue:
                issue.triage_decision = "DEFER"
                issue.triage_reason = f"Max fix attempts reached ({issue.fix_attempt_count})"

        return FixIterationResult(
            issues_fixed=[i.id for i in resolved],
            issues_remaining=[i.id for i in remaining if i.triage_decision != "DEFER"],
            issues_deferred=[i.id for i in remaining if i.triage_decision == "DEFER"],
            files_modified=[str(c.file_path) for c in changes],
            validation_rerun=True,
            iteration_number=1,
        )

    def _build_fix_prompt(
        self,
        issues: list[ValidationIssue],
        context: RunContext,
    ) -> str:
        """Build LLM prompt for fixing issues."""
        # Implementation details...

    def _backup_files(self, changes: list[FileChange]) -> None:
        """Backup files before modification."""
        for change in changes:
            if change.file_path.exists():
                self._file_backups[change.file_path] = change.file_path.read_text()

    def _rollback(self) -> None:
        """Restore files from backup."""
        for path, content in self._file_backups.items():
            path.write_text(content)
        self._file_backups.clear()
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| asyncio | stdlib | Async LLM calls |
| pathlib | stdlib | File operations |
| Pydantic | 2.12+ | Model validation |
| shutil | stdlib | File backup |

### File Structure Requirements

**New Files:**
- `src/adw/validation/fix_engine.py`

**Modified Files:**
- `src/adw/validation/__init__.py` - Export FixEngine
- `src/adw/validation/models.py` - Add FixIterationResult if not in 11.2

**Test Files:**
- `tests/unit/validation/test_fix_engine.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/validation/test_fix_engine.py
class TestFixEngine:
    async def test_attempt_fixes_calls_llm(self, mock_llm):
        """LLM called with fix prompt for FIX issues."""

    async def test_attempt_fixes_skips_non_fix(self):
        """Only FIX-triaged issues are processed."""

    async def test_apply_changes_atomic(self, tmp_path):
        """All changes applied or none (rollback on failure)."""

    async def test_rollback_on_error(self, tmp_path):
        """Files restored on fix application error."""

    async def test_revalidate_affected_only(self, mock_validators):
        """Only affected validators re-run after fix."""

    async def test_auto_defer_max_attempts(self, mock_config):
        """Issues auto-deferred after max fix attempts."""

class TestFixPromptGeneration:
    def test_includes_issue_details(self, sample_issues):
        """Prompt includes issue description and location."""

    def test_includes_code_context(self, sample_issues):
        """Prompt includes code snippets when available."""

    def test_batches_multiple_issues(self, sample_issues):
        """Multiple issues in single prompt."""

    def test_handles_no_location(self, issue_without_location):
        """Handles issues without file location."""
```

---

## Previous Story Intelligence

**Learnings from Story 11.2:**
- ValidationIssue has fix tracking fields
- FixAttempt model records each attempt
- FixResult enum tracks attempt outcomes

**Learnings from Story 11.3:**
- Issues arrive with triage_decision set
- FIX issues should be attempted
- Triage can be re-done after fix failure

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 3: LLM executor patterns
- File modification patterns from various stories

**Established Patterns:**
- Atomic file operations with backup/rollback
- LLM responses parsed as structured JSON
- Async operations for LLM calls

---

## Latest Technical Information

**LLM Code Fixing (2025):**
- Provide full file context, not just snippets
- Request specific line-by-line changes
- Use diff format for clarity
- Validate syntax before applying

**Atomic File Operations:**
- Write to temp file, then rename (atomic on most filesystems)
- Store backups in memory for small files
- Use file locks for concurrent access

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Async by default**: Fix operations should be async
- **Atomic operations**: All file changes atomic
- **Structured logging**: Log fix attempts and results
- **Error handling**: Wrap errors in typed exceptions

---

## Dev Notes

### Fix Prompt Template

```
You are fixing validation issues in code. For each issue below,
provide the fix as a file modification.

Issues to fix:
{issues_formatted}

Current file contents:
{file_contents}

Respond with JSON:
{
  "fixes": [
    {
      "issue_id": "VI-...",
      "file_path": "src/...",
      "line_start": 10,
      "line_end": 15,
      "replacement": "new code here"
    }
  ]
}

Only include fixes you are confident will resolve the issue.
If unsure, set replacement to null and explain in notes.
```

### Implementation Approach

1. Create FixIterationResult model
2. Implement FixEngine skeleton
3. Add fix prompt generation
4. Add fix application with backup/rollback
5. Add selective re-validation
6. Add fix tracking updates
7. Add auto-defer logic
8. Write comprehensive tests

### Key Design Decisions

1. **Batch Fixing**: Fix multiple issues in one LLM call for efficiency
2. **Atomic Application**: All-or-nothing file changes
3. **Selective Re-validation**: Only re-run affected validators
4. **Auto-Defer**: Prevent infinite fix loops

### References

- [Source: _bmad-output/epics/epic-11-validation-loop.md#Story 11.4]
- [Source: _bmad-output/architecture.md#LLM Integration]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 11: Validation Loop - Story 11.4

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

### Completion Notes List

### File List
