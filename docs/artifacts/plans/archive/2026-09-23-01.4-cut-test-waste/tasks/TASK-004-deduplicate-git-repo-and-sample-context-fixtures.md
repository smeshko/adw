# TASK-004: Deduplicate git_repo and sample_context fixtures

Depends on: TASK-003
Suggested commit: `test: use the root git_repo fixture and collapse duplicate sample_context copies`

## Goal

Every `git_repo` consumer uses the root fixture, and `test_snapshot_manager.py` defines `sample_context` once.

## Files

- `tests/unit/worktree/test_branch.py`: delete the three class-level `git_repo` fixtures (lines ~45, ~116, ~250).
- `tests/integration/worktree/test_single_phase_preservation.py`: delete the class-level `git_repo` (line ~24).
- `tests/integration/test_git_hooks.py`: delete the module-level `git_repo` (line ~27).
- `tests/integration/test_git_diff.py`:
  - Delete the module-level `git_repo` (line ~24).
  - `test_capture_diff_with_modified_file`: write `git_repo / "README.md"` instead of `initial.txt`. Assert `"README.md" in diff` and `"-# Test Repository" in diff`.
  - `test_capture_diff_with_deleted_file`: unlink `git_repo / "README.md"`, and assert `"README.md" in diff`.
- `tests/unit/core/test_snapshot_manager.py`: replace the seven identical class-level `sample_context` fixtures with one module-level `sample_context` above the first class. The seven classes are `TestPrePhaseSnapshot`, `TestPostPhaseSnapshot`, `TestSequentialNumbering`, `TestSnapshotListing`, `TestSnapshotLoading`, `TestPerformance` and `TestSequenceCache`.
- Drop imports left unused. `subprocess` in the files whose fixture was the only git caller, and possibly `Path`.

## Acceptance

- [ ] The duplicate-fixture scan from `RESEARCH.md` → Useful Commands shows:
  - exactly one `git_repo` definition, at `tests/conftest.py`
  - the `sample_context 2b1f6c` group down to 2 entries: `test_snapshot_manager.py` (module-level) and `integration/core/test_snapshot_integration.py:26`
- [ ] `uv run pytest tests/unit/worktree/test_branch.py tests/integration/worktree/test_single_phase_preservation.py tests/integration/test_git_hooks.py tests/integration/test_git_diff.py tests/unit/core/test_snapshot_manager.py -o addopts=""` passes with the same test count as before the change.
- [ ] After that run, `git worktree list` and `git branch` in the checkout match the values recorded before it. The root fixture's teardown must not reach outside `tmp_path`.
- [ ] `uv run ruff check tests/ && uv run ruff format --check tests/` pass.

Evidence:
- the scan output before and after
- the partial-suite summary lines before and after, with equal counts
- the unchanged `git worktree list`

## Steps

### RED
- [ ] Run the five files and record the summary line and count. Run the duplicate-fixture scan: 6 `git_repo` groups and `sample_context 2b1f6c` ×8.
- [ ] In `test_git_diff.py`, first switch the two tests to `README.md` against the *local* fixture. They should fail (no `README.md` in the local repo), which shows the edit is what ties them to the root fixture.

### GREEN
- [ ] Delete the six local `git_repo` fixtures. Re-run the five files; the two `test_git_diff.py` tests now pass.
- [ ] Collapse `sample_context` in `test_snapshot_manager.py`, and re-run it.

### REFACTOR
- [ ] Remove the unused imports, then run ruff check and format on `tests/`.
- [ ] Re-run the scan, and compare the checkout's `git worktree list` and `git branch` with the values recorded in RED.

## Notes

- The root `git_repo` yields `tmp_path` itself, not a subdir. In `test_git_diff.py`, `test_has_commits_false_for_empty_repo` and `test_capture_staged_diff_in_empty_repo` build their own repo under `tmp_path / "empty_repo"` without taking `git_repo`, so nothing collides.
- The root README content is `"# Test Repository"` with no trailing newline. Git's diff line is `-# Test Repository`, followed by a `\ No newline at end of file` marker, which the substring assertion ignores.
- The root fixture also runs `_cleanup_worktrees` on teardown. That suits `test_single_phase_preservation.py`, which creates a worktree on purpose and never removed it.
- Leave `sample_context` in `test_snapshot_integration.py` (2 differing copies), `test_resume_manager.py` and `models/test_resume.py` alone. They are cross-package or differ (see PLAN → Out of Scope).
