# Decisions: Hook config and phase-hook scripts

Date: 2026-09-23

## 1. A non-worktree run outside a git repo

### Options Considered

1. **Warn and skip.** Log a warning, and leave `branch_name` unset.
2. **Fail the run.** `ensure_on_branch` raises `HookError`, whose suggestion is to run inside a git repository.

### Dependencies

- Worktree mode already fails outside git: `_fetch_base_branch` raises `WorktreeError`.
- Auto-commit, diff capture and PR creation all need git.
- A prototype showed that failing breaks 85 tests in 4 files.

### Selected Option

2 — fail the run (user's choice).

### Rationale

ADW's pipeline is git-based end to end, and the phase goal is "nothing fails silently". A warning would let a run proceed to phases that then fail best-effort, or quietly do nothing.

### Rejected Options

- Warn and skip: it keeps the silent-degradation pattern this phase removes. The only thing it saves is test churn, and that churn is bounded and known.

## 2. Which runs switch branches

### Options Considered

1. **Every non-worktree run start**, whatever the starting phase.
2. **Only runs that start at `plan`**, `pre.sh`'s exact trigger.

### Dependencies

`create_run_context` creates the worktree and its branch for every starting phase, `run_single_phase` included.

### Selected Option

1 — every run start (user's choice).

### Rationale

Worktree and non-worktree runs then behave the same. A single-phase `build --from-run X` commits on the run's feature branch, not on whatever branch is checked out.

### Rejected Options

- Plan-only: single-phase runs could commit onto `main`, or onto an unrelated branch.

## 3. Where the ship hooks use `ADW_PR_URL`

### Options Considered

1. **`post.sh` and `pre.sh`.** `post.sh` derives the PR number from the URL. `pre.sh` looks the PR up by URL, and falls back to the current branch.
2. **`post.sh` only.**

### Selected Option

1 (user's choice).

### Rationale

The run's own PR, recorded on the context by phase 1.7, is the exact reference. A branch lookup can miss when the run is resumed on a different checkout state.

### Rejected Options

- `post.sh` only: it leaves `pre.sh` guessing when the exact reference is already in the environment.

## 4. Resume and `--from-run` continue

### Options Considered

1. **Out of scope.** A mismatch fails at auto-commit with `GIT_BRANCH_MISMATCH` and a fix-it suggestion.
2. **Switch on resume and continue too.**

### Selected Option

2 (user's choice).

### Rationale

A resumed non-worktree run should land its commits on its own branch without the user having to intervene.

The switch runs before any context mutation or save, so a failed switch leaves the run's on-disk state untouched. A context written before this phase has `branch_name: None`. For those, the name is derived the same way run start derives it, and backfilled.

### Rejected Options

- Out of scope: the run would fail late, after the LLM work of the resumed phase, instead of at resume time.

## 5. Where the ported git logic lives

### Options Considered

1. **`hooks/git_branch.ensure_on_branch(branch, *, working_dir)`.** The lifecycle calls it.
2. **Inline in `RunLifecycle`**, calling the three existing helpers.

### Selected Option

1.

### Rationale

The logic becomes one git function, tested against real repos in `tests/integration/test_git_hooks.py`, which the epic's acceptance names. The lifecycle keeps only the when and which, and the lifecycle's unit tests can mock one name.

`get_current_branch` is reused from `git_commit.py`; there is no import cycle, since neither module imports the other.

### Rejected Options

- Inline: git calls spread across the lifecycle, and the unit tests would have to mock three helpers.

## 6. Fixing the 85 broken tests

### Options Considered

1. **Mock `adw.core.run_lifecycle.ensure_on_branch`** in the unit files. Move the two integration files to `git_repo`.
2. **Move all four files to `git_repo`.**
3. **Mock everywhere.**

### Selected Option

1.

### Rationale

- The unit files already mock every collaborator. A module-level autouse patch keeps them fast, and lets new unit tests assert the call.
- The integration files should exercise real git. `git_repo` plus a committed `.gitignore` (`home/`, `.adw/runs/`) is the pattern `test_phase_failure.py` already uses.

### Rejected Options

- All `git_repo`: about 70 extra `git init` calls, for tests that aren't about git.
- Mock everywhere: nothing would cover the real switch through the orchestrator.

## 7. Timeout acceptance test values

### Options Considered

1. **1 s timeout and 10 s sleep in the suite**, plus a manual 5 s/10 s transcript.
2. **5 s/10 s in the suite.**

### Selected Option

1.

### Rationale

The behaviour is identical. Option 1 keeps about 4 s off a suite that phase 1.1 worked to speed up, and the manual transcript reproduces the epic's exact numbers.
