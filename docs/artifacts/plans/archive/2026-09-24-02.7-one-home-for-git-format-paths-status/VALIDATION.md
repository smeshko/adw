# Validation Summary — 02.7-one-home-for-git-format-paths-status

**Rounds:** 3
**Plan status at validation:** draft
**Run on:** 2026-09-24

The plan's risk is `large`, so round 1 paired a Codex-focus reviewer with an independent lens. Codex hit its usage limit on the first call and stayed limited for the whole validation. Every round therefore ran with a clean `general-purpose` subagent given the verbatim focus text; each round file records its reviewer.

Mid-round 1, `staging` gained #212 (phase 2.3, webhook removal). The branch fast-forwarded to `7b61e72a`, and the plan's line references and baseline were refreshed (round-1 M1).

Round 3 still produced `apply` rows. The shared protocol says to ask the user at that point. The user had asked for a fully autonomous run, so round 3 took **act-and-stop**: its findings were precision fixes inside tasks, not structural defects, so they were applied and no fourth round ran.

## Rounds

| Round | Findings | Applied | Deferred | Rejected |
|-------|----------|---------|----------|----------|
| 1     | 26       | 22      | 2        | 2        |
| 2     | 13       | 12      | 0        | 1        |
| 3     | 9        | 9       | 0        | 0        |

## Applied

### Round 1
- TASK-002, TASK-006, PLAN.md:Decisions: aliases and local renames fix the name clashes (`delete_branch` / `pr_exists` / `status_style` against existing parameters and locals) (round-1 #1).
- TASK-004, PLAN.md:
  - The `-W` gate now filters by message; the module filter never fired.
  - A positive control proves the gate works.
  - `IndexManager.update_run` validates its updates.
  - Test-side string writes are converted.

  (round-1 #2)
- TASK-004, PLAN.md:Acceptance, TASK-009: two status greps replace the old one. They are satisfiable, and cover writes, `==`/`!=` and tuples. The phase-pipeline `phase_status` and the docstrings are handled (round-1 #3).
- TASK-001, TASK-003, PLAN.md:Risks: a timeout stops git with SIGTERM before SIGKILL, and `worktree prune` runs after a killed `worktree add`. The Risk now says plainly that auto-commit swallows a timeout. Applying this also moved every test patch from `subprocess.run` to the `git` / `gh` seam, because `_run` uses `Popen` (round-1 #4).
- PLAN.md:Decisions, TASK-001/002/003: timeout tiers for network, checkout and hook commands (round-1 #5).
- TASK-007, PLAN.md: `atomic_write` keeps a replaced file's mode and gives new files the umask default, instead of mkstemp's 0600 (round-1 #7).
- TASK-007: the wizard rollback tests delegate their first write, so they can't pass vacuously (round-1 #8).
- TASK-008: the resume/status/list integration fixtures `chdir` instead of patching a helper that no longer exists (round-1 #9).
- TASK-002: a new `tests/unit/cli/test_cleanup.py` covers `cleanup --delete-branch` when the worktree is already gone (round-1 #10).
- PLAN.md, TASK-005, TASK-009: one cost grep, and a fix for the `stats_aggregator.py:73` docstring (round-1 #13).
- TASK-002/003/004/005/006, PLAN.md:Scope: wrong paths and names fixed, `list(PHASE_SEQUENCE)`, and 4 more feature docs plus epic 04 and two docstrings added (round-1 #14).
- TASK-003, TASK-007: patch and injection sites the tasks had missed (round-1 #15).
- TASK-001: the timeout label names the tool and up to two leading non-flag arguments (round-1 #17).
- TASK-008 / PLAN.md:Tasks: dependencies declared for the AGENTS.md bullet (round-1 #18).
- TASK-006: `status_style` looks up with `RunStatus(status)`, which passes mypy strict (round-1 #20).
- TASK-004: the round-trip test asserts on parsed JSON (round-1 #21).
- TASK-003: a `worktree remove` timeout maps to `WORKTREE_REMOVE_FAILED`, and both fetch failures are recoverable (round-1 #22).
- PLAN.md:Risks: the full list of visible output changes (round-1 #23).
- TASK-002, TASK-007: tightened acceptance greps (round-1 #24).
- TASK-008, RESEARCH.md: the resume question is settled, and the RED wording for `logs` is corrected (round-1 #25).
- PLAN.md, RESEARCH.md, TASK-004/005/007/008/009: line references and the baseline refreshed after #212 merged, and the #212 conflict risk resolved (round-1 #16, M1).

### Round 2
- TASK-001, PLAN.md: git stays in the terminal's process group; there is no new session or group kill. Ctrl+C then reaches git, which removes its own locks, and credential/SSH prompts keep working. `_run` stops git on any exception, SIGTERM first. This reverses round 1's group-kill design (round-2 #1, #2).
- TASK-001, PLAN.md, RESEARCH.md: after SIGKILL, `_run` only `wait()`s, never reading pipes that a descendant may hold. Two stale statements corrected (round-2 #3).
- TASK-002, TASK-003: `except ADWError` wraps only the `git()` call, so `BRANCH_NOT_CREATED` and other `WorktreeError`s keep their codes, with a new test (round-2 #4).
- TASK-004: the positive-control target that works, and the 4 multi-line test `model_copy` sites (round-2 #5).
- TASK-008: `test_status_no_runs_exist` expects exit 0 and "No runs found", and the patch counts are corrected (round-2 #6).
- TASK-001, TASK-003: a SIGKILL-escalation test, `cwd=tmp_path` in every fake test, and the label rule defined as "up to the first flag" (round-2 #7).
- PLAN.md, TASK-001, TASK-003: `push` and `worktree add` move to `HOOK_TIMEOUT` (round-2 #8).
- TASK-009, PLAN.md:Tasks, TASK-002, TASK-007, PLAN.md:Out of Scope: coverage for `update_run`, a fourth shadowing site, the wrapper's third call, `fchmod` after `fdopen`, and the rename limits (round-2 #9a–d).

### Round 3
- TASK-002, TASK-003: `branch_exists` lets `GIT_TIMEOUT` through, so "unknown" never reads as "absent". `delete_branch` catches the timeout and reports failure. The pre-check timeout creates nothing and deletes nothing (round-3 #1).
- TASK-003: the fetch and push timeout mappings keep `adw.git`'s credentials/ssh-agent suggestion (round-3 #2).
- TASK-001, TASK-009, PLAN.md: the escalation test asserts `elapsed ≥ timeout + grace` for both triggers, and `KILL_GRACE` is read at call time (round-3 #3).
- TASK-001: every SIGALRM test cancels its timer in `finally`, with wider timing margins (round-3 #4).
- TASK-001: `_stop`'s `finally` still sends SIGKILL if a second interrupt arrives (round-3 #5).
- TASK-002, RESEARCH.md, PLAN.md:Acceptance, TASK-009, TASK-004, TASK-008: `git.py`'s grep, the stale tier line, new ACs for the runs path, the `atomic_write` callers and the phase lists, and nits (round-3 #6a–d).

## Deferred

- (round-1 #6) Disable git's terminal prompts (`GIT_TERMINAL_PROMPT=0`) on non-interactive paths. git keeps its terminal, so a user can still answer a prompt, and the timeout suggestion names credentials and ssh-agent. **ADW-65**
- (round-1 #19) `IndexManager.update_run` can lose updates between concurrent runs. This predates the phase: `atomic_write` prevents torn files but not lost updates. **ADW-66**
- (round-1 #19) Every command treats the cwd as the project root, so from a subdirectory the error says "run adw init". This predates the phase. **ADW-67**
- (round-2 #1, note) Ctrl+C during a phase hook leaves the hook's process group running, because `HookRunner` handles only `TimeoutError`. This predates the phase, which doesn't touch the hook runner. **ADW-71**

## Rejected

- (round-1 #11) Limit TASK-004 to writes and sets and skip the plain comparisons. Rejected because members catch typos that string literals can't, and one grep then checks the whole rule. Round 2 agreed.
- (round-1 #12) Split the phase into two PRs. Rejected because the user asked for phase 2.7 end to end as one PR, and the epic sizes it as one phase. The 8 task commits keep it reviewable piece by piece. Rounds 2 and 3 agreed.
- (round-2 #9e) Make `update_run` reject unknown keys. Rejected as optional hardening outside this phase's goal: the behaviour predates it, and callers may pass extra keys today. Round 3 agreed.
