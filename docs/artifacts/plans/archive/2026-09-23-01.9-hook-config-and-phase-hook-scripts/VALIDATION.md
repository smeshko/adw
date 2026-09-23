# Validation: Hook config and phase-hook scripts

Validated: 2026-09-23 at `f0842cd4`. CI is green on every task commit of PR #209.

| Criterion | Result |
|---|---|
| With `hooks: {timeout_seconds: 5}`, a post-hook that sleeps 10 s fails after about 5 s | Met: `test_project_hook_timeout_stops_post_hook` (1 s/10 s, RED 10.61 s → GREEN 1.43 s), and the 5 s/10 s scratch-repo transcript below |
| `grep -rn "python3 -c" src/adw/defaults` returns nothing | Met |
| A non-worktree `adw run` creates and switches to the feature branch before the plan phase | Met: `test_non_worktree_run_switches_branch_before_plan`, and the scratch-repo transcript below |
| Resume and continue switch back to the run's branch; a dirty tree or non-git dir raises and leaves the on-disk status unchanged | Met: `test_resume_switches_back_to_run_branch`, `test_resume_on_dirty_tree_leaves_status_unchanged`, `test_continue_from_run_switches_to_run_branch`, `test_resume_backfills_branch_name`, `test_non_worktree_run_outside_git_fails` |
| `test_ship_post_hook.py` and `test_git_hooks.py` pass against the trimmed scripts; the dead-names grep returns nothing | Met for `src`. In `tests`, the grep hits only `test_no_status_or_task_files_written`, the regression test TASK-005 requires, which sets `ADW_TASK_ID` and asserts both dead files are absent |
| The three D6 files and `plan/pre.sh` are gone | Met |
| `scripts/preflight.sh` passes; `uv run pytest` green, coverage ≥ 80% | Met: 3841 passed, 5 skipped, 85.25% |
| A full `uv run pytest` leaves the checkout's branches, status and worktrees unchanged | Met: see the no-touch snapshot |

## Preflight and full suite

```
$ scripts/preflight.sh
==> ruff check
All checks passed!
==> ruff format --check
154 files already formatted
==> mypy
Success: no issues found in 154 source files
preflight: ok

$ uv run pytest
Required test coverage of 80% reached. Total coverage: 85.25%
================= 3841 passed, 5 skipped in 209.31s (0:03:29) ==================
```

## No-touch snapshot

`git status --short`, `git branch`, `git worktree list` and `ls .adw/runs | wc -l`, taken before and after the full run:

```
$ diff snap-before.txt snap-after.txt
11c11
< /Users/…/.worktrees/adw-11  86768f65 [feature/adw-11]
---
> /Users/…/.worktrees/adw-11  19a4c12e [feature/adw-11]
```

The one line that changed is the sibling worktree `adw-11`, where a concurrent session committed its own plan during the run (`9a525ebe`, `19a4c12e`, authored by Ivo Tsonev; test repos commit as `Test`). This checkout's status, branches, HEAD and run count are unchanged.

## Greps

```
$ grep -rn "python3 -c" src/adw/defaults
(no output)

$ grep -rn "ADW_PR_NUMBER\|ADW_TASK_ID\|ship_status\|task_update_request" src
(no output)

$ grep -rn "ADW_PR_NUMBER\|ADW_TASK_ID\|ship_status\|task_update_request" tests
tests/integration/test_ship_post_hook.py:725:            "ADW_TASK_ID": "TASK-123",
tests/integration/test_ship_post_hook.py:740:        assert not (artifacts_dir / "ship_status.json").exists()
tests/integration/test_ship_post_hook.py:741:        assert not (artifacts_dir / "task_update_request.json").exists()

$ grep -rn "{{include:[^}]*\(checklist\|template\|validation-prompt\)\.md" src/adw/defaults
(no output)

$ grep -rn "checklist.md\|template.md\|validation-prompt" src tests
src/adw/defaults/commands/plan/create-story/workflow.yaml:18:template: "{installed_path}/template.md"
src/adw/defaults/commands/build/dev-story/workflow.yaml:13:validation: "{installed_path}/checklist.md"
```

## Import boundaries

```
$ grep -n "^import\|^from" src/adw/hooks/git_branch.py
14:import re
15:import subprocess
16:from pathlib import Path
18:from adw.exceptions import HookError
19:from adw.hooks.git_commit import get_current_branch

$ git diff --stat staging -- src/adw/hooks/__init__.py
(no output)
```

## Regression tests for the epic's bugs

Each test was run against the code before its fix, then after.

**B10: project.yaml `hooks:` ignored** (TASK-001, before `028b84a9`)

```
RED   test_runner_uses_project_hook_config
E  assert HookConfig(sh...ut_seconds=60) == HookConfig(sh...out_seconds=5)
RED   test_project_hook_timeout_stops_post_hook
E  Failed: DID NOT RAISE <class 'adw.exceptions.HookError'>
10.61s call  tests/integration/core/test_hook_config.py::test_project_hook_timeout_stops_post_hook

GREEN 10 passed in 2.09s
1.43s call  tests/integration/core/test_hook_config.py::test_project_hook_timeout_stops_post_hook
```

**B16: `python3 -c "from adw…"` hooks did nothing outside the venv** (TASK-002 before `52eaa756`, TASK-003 before `a7313ec0`)

```
RED   test_build_post_hook_extracts_story_and_leaves_changes_uncommitted
E  AssertionError: assert 'src.py' in ''          # the old step 2 auto-committed it

RED   test_non_worktree_run_switches_branch_before_plan
  with the bundled plan/pre.sh (pytest's venv python3 has adw):
E  AssertionError: assert None == 'feature/add-login'     # context.json branch_name
  without it (what a `uv tool install` sees):
E  AssertionError: assert 'main' == 'feature/add-login'   # branch.txt

GREEN 2 passed (test_phase_hook_scripts.py), 10 passed (TASK-003 groups)
```

## Manual: 5 s timeout on a 10 s post-hook

Scratch repo with `.adw/project.yaml`, `.adw/commands/plan/post.sh` (`exec sleep 10`) and `.gitignore` (`.adw/runs/`) committed, run with the branch's `adw` and a scratch `HOME`:

```
$ cat .adw/project.yaml
name: timeout-demo
language: python
worktree:
  enabled: false
hooks:
  timeout_seconds: 5
$ time ADW_MOCK_EXECUTOR=1 adw run "timeout check" --phase plan --no-worktree
19:19:22 [WARN] [hook] Hook execution timed out
19:19:22 [ERROR] [phase] Post-hook failed
╭──────────────────────────────── PLAN Failed ─────────────────────────────────╮
│ Error: Hook timed out after 5s                                               │
│ Suggestion: Increase timeout or optimize post-hook script                    │
╰──────────────────────────────────────────────────────────────────────────────╯
│ Status: failed                                                               │
│ Duration: 5.0s                                                               │
Error: Hook timed out after 5s
… 0.30s user 0.14s system 7% cpu 6.021 total
exit=1
```

## Manual: non-worktree branch switch

Scratch repo with `.adw/project.yaml` (`worktree: {enabled: false}`), a project plan post-hook that writes `notes.md` (so the plan phase has a change to auto-commit) and `.gitignore` (`.adw/runs/`) committed:

```
$ git branch --show-current
main
$ ADW_MOCK_EXECUTOR=1 adw run "Add login" --phase plan --no-worktree
adw exit=0
$ git branch --show-current
feature/add-login
$ git log --oneline -3
33e86e6 [adw] Plan: Add login
14a8f6f ADW config
$ git checkout main && echo change >> README.md
$ ADW_MOCK_EXECUTOR=1 adw run "Add logout" --phase plan --no-worktree
adw exit=1
Error: Cannot switch to branch 'feature/add-logout': the working tree has
uncommitted changes
Suggestion: Commit or stash your changes, or run with worktree isolation (drop
--no-worktree)
$ git branch --show-current
main
$ ls .adw/runs | wc -l
       1
```

The refused run created no run directory: the count stays at the first run's 1.

## Manual: `adw validate` after the D6 deletions

```
$ adw init --no-interactive && adw validate
  .adw/project.yaml ....................... OK
  plan .................................... OK
  build ................................... OK
  validate ................................ OK
  document ................................ OK
  ship .................................... OK

  Result: 0 errors, 0 warnings — configuration is valid
```

## Divergences from the plan

- **Branch.** The worktree's existing `feature/adw-15` (cut from current `origin/staging`) was used instead of running `prepare_branch.sh`, which would stash on the stash stack shared with the concurrent sessions.
- **TASK-001.** The six `MagicMock(spec=ProjectConfig)` configs in `test_bootstrap.py` needed `hooks = HookConfig()`. The task note expected them to stay green, but a Pydantic v2 defaulted field is not a class attribute, so the spec'd mock raised `AttributeError`.
- **TASK-003.** Three `TestPRCreationAfterDocumentPhase` tests in `test_orchestrator.py` failed outside the prototype's count: with `branch_name` now set on non-worktree runs, `create_pr` pushes the branch before calling `gh`. The class now stubs `adw.core.pr._push_branch`, and `test_pr_created_after_document_phase` also asserts `--head feature/test-feature`.
- **TASK-005.** The pre-hook tests use the shared `fake_gh` fixture instead of a hand-written fake `gh`; its recorded argv serves as the call log.
