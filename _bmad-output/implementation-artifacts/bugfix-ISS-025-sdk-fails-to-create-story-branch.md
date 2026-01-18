# Story: Bugfix ISS-025 - SDK fails to create story branch

Status: ready-for-dev
Linear Issue: pending
Epic: 13 - Webhook Infrastructure (Tech Debt)
Created: 2026-01-18

---

## Story

As a developer using ADW,
I want the SDK to properly create, track, and validate story branches during worktree creation,
so that commits go to the correct branch and PRs are created with the right source/target.

## Acceptance Criteria

```gherkin
Feature: Story branch creation and validation

  Scenario: Successful branch creation during worktree setup
    Given a new ADW run is started with worktree enabled
    When the orchestrator creates a worktree
    Then a branch named "story/<story-key>" or "adw/<run-id>" MUST be created
    And the branch_name MUST be stored in RunContext
    And the branch_name MUST be persisted in context.json
    And the run MUST NOT proceed if branch creation fails

  Scenario: Branch creation failure handling
    Given a new ADW run is started with worktree enabled
    When branch creation fails (e.g., branch already exists, git error)
    Then the entire run MUST fail immediately
    And a clear error message MUST be propagated to the user
    And the error MUST include the branch name that failed
    And no commits should be made to any branch

  Scenario: PR creation uses correct branch
    Given an ADW run has completed successfully
    And context.json contains a valid branch_name
    When auto_create_pr is called
    Then the PR MUST be created from branch_name to staging
    And the gh pr create command MUST use --head parameter with branch_name
    And the base branch MUST ALWAYS be "staging" - NEVER "main" or any other branch
    And the base branch parameter MUST be hardcoded, not configurable

  Scenario: Branch validation before commits
    Given an ADW run is in progress
    When the SDK is about to make commits via hooks
    Then the SDK MUST validate the current branch matches context.branch_name
    And if branches don't match, the operation MUST fail with a clear error
```

## Tasks / Subtasks

### Task 1: Modify WorktreeManager to return branch name
- [x] Update `create_worktree()` to return `tuple[Path, str]` (path, branch_name)
- [x] Update `_create_worktree_for_run()` to capture and return branch name
- [x] Add `get_branch_name()` call after worktree creation to verify branch exists

### Task 2: Populate branch_name in RunContext
- [x] Modify `Orchestrator.run()` to capture branch_name from worktree creation
- [x] Set `context.branch_name` when creating `RunContext`
- [x] Ensure `branch_name` is persisted in `context.json`

### Task 3: Add branch validation
- [ ] Create validation function to verify branch exists after creation
- [ ] Add validation that current git branch matches `context.branch_name` before commits
- [ ] Fail fast if branch validation fails with clear error message

### Task 4: Fix PR creation to use branch_name
- [ ] Modify `create_pr_via_gh()` to accept `head_branch` parameter
- [ ] Update `auto_create_pr()` to pass `context.branch_name` as head branch
- [ ] Add `--head` parameter to `gh pr create` command
- [ ] CRITICAL: Hardcode base branch to "staging" - remove ALL configurability:
  - [ ] Remove `base_branch` parameter from `auto_create_pr()` function signature
  - [ ] Remove `--base` CLI option from `adw pr` command
  - [ ] Remove/simplify `_get_base_branch()` function to just return "staging"
  - [ ] Remove `git.default_branch` config support from `.adw/adw.yaml` parsing

### Task 5: Add ADW_BRANCH_NAME to hook environment
- [ ] Update `build_hook_environment()` in `hooks/environment.py`
- [ ] Add `ADW_BRANCH_NAME` environment variable
- [ ] Document the new environment variable

### Task 6: Add comprehensive tests
- [ ] Test branch creation returns correct name
- [ ] Test context.json contains branch_name after run
- [ ] Test PR creation uses correct head/base branches
- [ ] Test failure scenarios propagate errors correctly
- [ ] Test branch validation catches mismatches

---

## Developer Context

### Technical Requirements

**Critical: This is a high-severity bugfix affecting the entire git workflow.**

The fix must ensure:
1. Branch creation is atomic with worktree creation
2. Branch name is always captured and persisted
3. PR creation explicitly specifies source branch
4. Failures are detected and propagated immediately
5. **PRs MUST ALWAYS target `staging` branch - NEVER `main` or any other branch**

**NON-NEGOTIABLE RULE:** The base branch for all ADW-created PRs is `staging`. This is not configurable. Remove ALL configurability:
- Remove `base_branch` parameter from function signatures
- Remove `--base` CLI option from `adw pr` command
- Remove `git.default_branch` config file support
- Hardcode `"staging"` as the only valid base branch
- Any code path that could create a PR against `main` or any other branch is a bug

### Architecture Compliance

**Key Files to Modify:**

| File | Current Issue | Required Change |
|------|---------------|-----------------|
| `src/adw/worktree/manager.py:395-486` | `create_worktree()` computes branch_name but doesn't return it | Return `tuple[Path, str]` or add branch_name to return object |
| `src/adw/core/orchestrator.py:1674-1726` | `_create_worktree_for_run()` discards branch info | Capture branch_name and return it |
| `src/adw/core/orchestrator.py:304-312` | `RunContext` created with `branch_name=None` | Populate from worktree creation result |
| `src/adw/cli/pr.py:145-155` | `create_pr_via_gh()` has no `--head` param | Add head_branch param, hardcode base="staging" |
| `src/adw/cli/pr.py:289-388` | `auto_create_pr()` has `base_branch` param defaulting to "main" | Remove base_branch param, pass branch_name as head |
| `src/adw/cli/pr.py:506-535` | `_get_base_branch()` reads from config, defaults to "main" | Simplify to always return "staging" |
| `src/adw/cli/pr.py` (CLI) | `--base` CLI option allows override | Remove `--base` option entirely |
| `src/adw/hooks/environment.py:91-134` | Missing `ADW_BRANCH_NAME` | Add to hook environment |

**Exception Handling:**
- Use `WorktreeError` for branch creation failures
- Include branch name, git error, and recovery suggestion in error
- Set `recoverable=False` for branch creation failures

### Library & Framework Requirements

- Use existing `subprocess.run()` pattern for git commands
- Use `WorktreeBranchManager.get_branch_name()` for consistent naming
- Use `WorktreeBranchManager.branch_exists()` for validation

### File Structure Requirements

No new files required. All changes are to existing files:
- `src/adw/worktree/manager.py`
- `src/adw/worktree/branch.py` (if needed)
- `src/adw/core/orchestrator.py`
- `src/adw/cli/pr.py`
- `src/adw/hooks/environment.py`
- `tests/unit/worktree/test_manager.py`
- `tests/unit/core/test_orchestrator.py`
- `tests/unit/cli/test_pr.py`

### Testing Requirements

**Unit Tests:**
- Test `create_worktree()` returns both path and branch_name
- Test `branch_exists()` validation after creation
- Test `RunContext.branch_name` is populated
- Test `context.json` serialization includes branch_name
- Test `create_pr_via_gh()` with explicit head branch
- Test `create_pr_via_gh()` ALWAYS uses "staging" as base (hardcoded)
- Test error propagation on branch creation failure

**Integration Tests:**
- Full run with worktree → verify branch_name in context.json
- PR creation → verify correct `--head` parameter in gh command
- PR creation → verify `--base staging` is ALWAYS used
- Failed branch creation → verify run fails cleanly

---

## Root Cause Analysis

**Primary Issue:** `RunContext.branch_name` field exists but is NEVER populated.

**Code Flow:**
1. `WorktreeManager.create_worktree()` computes `branch_name = f"adw/{run_id}"` at line 418
2. Branch is created via `git worktree add ... -b {branch_name}`
3. Function returns ONLY `worktree_path`, discarding branch_name
4. `Orchestrator._create_worktree_for_run()` at line 1699 receives only path
5. `RunContext` at line 304-312 is created with `branch_name=None` (default)
6. `context.json` persisted with `branch_name: null`
7. PR creation at `auto_create_pr()` ignores null branch_name
8. `gh pr create --base main` uses current git branch implicitly

**Evidence from ISS-025:**
- Run `01KF636397JZC18V4K8MGS59G7` shows `branch_name: null` in context.json
- `commit_shas: []` empty array
- Commits went to staging branch
- PR #111 created staging → main instead of story branch → staging

---

## Git Intelligence

**Recent relevant commits:**
- `912a4d7` - Story 13.4 Event-to-Workflow Mapping (affected by this bug)
- Previous worktree stories: 10-1 through 10-6 established the worktree framework

**Pattern observation:** The worktree infrastructure works for creating isolated directories but branch tracking was incomplete from the start.

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:
- Use exception hierarchy (`WorktreeError`) with code, message, suggestion, recoverable fields
- Full type annotations required
- Structured logging for branch operations
- Rich for CLI output on errors
- Tests mirror source structure: `tests/unit/worktree/test_manager.py`

---

## Dev Notes

### Critical Implementation Points

1. **Return type change for `create_worktree()`:**
   ```python
   # Before
   def create_worktree(self, run_id: str, ...) -> Path:

   # After
   def create_worktree(self, run_id: str, ...) -> tuple[Path, str]:
       """Returns (worktree_path, branch_name)"""
   ```

2. **Context population in Orchestrator:**
   ```python
   # In Orchestrator.run() after worktree creation
   worktree_path, branch_name = self._create_worktree_for_run(run_id)
   context = RunContext(
       ...
       branch_name=branch_name,  # NOW POPULATED
       ...
   )
   ```

3. **PR creation with explicit head and hardcoded staging base:**
   ```python
   # In create_pr_via_gh() - base is ALWAYS "staging", not configurable
   BASE_BRANCH = "staging"  # HARDCODED - PRs ALWAYS target staging

   cmd = [
       "gh", "pr", "create",
       "--title", title,
       "--body", body,
       "--base", BASE_BRANCH,  # ALWAYS staging, never main
       "--head", head_branch,  # Explicit source branch from context
   ]
   ```

   ```python
   # In auto_create_pr() - remove base_branch parameter entirely
   def auto_create_pr(
       run_id: str,
       context: "RunContext",
       runs_dir: Path,
       # NO base_branch parameter - it's always staging
   ) -> AutoPRResult:
   ```

4. **Branch validation before commits:**
   ```python
   def validate_current_branch(expected: str) -> None:
       actual = subprocess.run(["git", "branch", "--show-current"], ...)
       if actual != expected:
           raise WorktreeError(
               code="BRANCH_MISMATCH",
               message=f"Expected branch '{expected}', but current is '{actual}'",
               suggestion="Ensure you're running in the correct worktree directory",
               recoverable=False,
           )
   ```

### Backward Compatibility

- Existing runs with `branch_name: null` in context.json should still work
- PR creation should fall back to current branch if `branch_name` is None
- Add migration note: old runs may need manual branch cleanup

### References

- [Source: src/adw/worktree/manager.py:395-486] - Worktree creation
- [Source: src/adw/core/orchestrator.py:239-312] - Run initialization
- [Source: src/adw/core/orchestrator.py:1674-1726] - _create_worktree_for_run
- [Source: src/adw/cli/pr.py:145-155] - create_pr_via_gh
- [Source: src/adw/cli/pr.py:289-388] - auto_create_pr
- [Source: src/adw/hooks/environment.py:91-134] - Hook environment
- [Source: ISS-025] - Issue documentation with evidence

---

## Dev Agent Record

### Context Reference

This story was created from ISS-025 (Critical Bug) via the report-issue → create-story workflow.

### Agent Model Used

Claude Opus 4.5

### Completion Notes List

- Story created with exhaustive codebase analysis
- Root cause identified: branch_name never populated in RunContext
- All affected files and line numbers documented
- Test requirements specified
- Backward compatibility considerations noted

### File List

Files to modify:
1. `src/adw/worktree/manager.py`
2. `src/adw/core/orchestrator.py`
3. `src/adw/cli/pr.py`
4. `src/adw/hooks/environment.py`
5. `tests/unit/worktree/test_manager.py`
6. `tests/unit/core/test_orchestrator.py`
7. `tests/unit/cli/test_pr.py`
