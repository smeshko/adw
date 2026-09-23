# Validation: Carry the PR URL on the run context

Validated: 2026-09-23 at `9f6970f8`. CI is green on every task commit of PR #207.

| Criterion | Result |
|---|---|
| Mocked run whose document step opens a PR through the fake `gh`: `context.json` has `pr_url`, and the completion comment carries it | Met: `test_pr_url_stored_in_context` |
| `adw pr <run-id>` on a completed run with no PR sets `context.pr_url` | Met: `test_pr_sets_pr_url` (fake `gh`), and a real run against a private scratch repo, below |
| `auto_close: true` with a Linear task leaves the ticket open and logs one warning | Met: `test_auto_close_leaves_ticket_open_and_warns_once` |
| `grep -rn "pr_result\|IssueCloser\|GitHubClient\|is_pr_merged" src` is empty | Met |
| `grep -rn "AutoPRResult\|…\|task_uuid" src` is empty | Met |
| `grep -rn "staging" src/adw` hits only `hooks/git_commit.py` (the git index) | Met |
| `scripts/preflight.sh` passes; `uv run pytest` green, coverage ≥ 80% | Met: 4262 passed, 5 skipped, 84.82% |

## Preflight and full suite

```
$ scripts/preflight.sh
==> ruff check
All checks passed!
==> ruff format --check
165 files already formatted
==> mypy
Success: no issues found in 165 source files
preflight: ok

$ uv run pytest -p no:cacheprovider
Required test coverage of 80% reached. Total coverage: 84.82%
================= 4262 passed, 5 skipped in 212.79s (0:03:32) ==================
```

## Greps

```
$ grep -rn "from adw.cli\|import adw.cli" src/adw/core/pr.py src/adw/core/extensions/document.py
(no output)

$ grep -rn "pr_result\|IssueCloser\|GitHubClient\|is_pr_merged" src
(no output)

$ grep -rn "AutoPRResult\|_PRResultFromContext\|can_auto_create_pr\|check_git_remote\|check_gh_authenticated\|try_auto_create_pr\|no_open\|task_uuid" src
(no output)

$ grep -rn "staging" src/adw
src/adw/hooks/git_commit.py:3:This module provides utilities for staging changes and creating
src/adw/hooks/git_commit.py:270:    hooks have modified files after staging.
```

## Regression tests for the epic's bugs

Each test was run against the code before its fix (the RED run recorded in its task), then after.

**B1: a completed run closed its ticket** (TASK-002, before `3fb81833`)

```
RED   TestFinalizeSuccess::test_auto_close_leaves_ticket_open_and_warns_once
E  AssertionError: Expected 'TaskManagerFactory' to not have been called. Called 1 times.
E  Calls: [call(),
E   call().create(task_type='linear', config=TaskManagerConfig(... auto_close=True)),
E   call().create().close_task('uuid-adw-1')].
GREEN test_auto_close_leaves_ticket_open_and_warns_once PASSED
GREEN test_no_auto_close_warning_by_default PASSED
```

The RED run shows the bug: the ticket was closed with no merge check.

**B12: `adw pr` never set `pr_url`** (TASK-005, before `9f6970f8`)

```
RED   TestPrCommand::test_pr_sets_pr_url
>       assert saved["pr_url"] == PR_URL
E       AssertionError: assert None == 'https://github.com/o/r/pull/1'
GREEN test_pr_sets_pr_url PASSED
```

**Completion comment without the PR URL** (TASK-004, before `5ad2c25b`). With the real `DocumentExtension`, the old preflight guessed there was no remote and never ran `gh`:

```
RED   TestPRCreationAfterDocumentPhase::test_pr_url_stored_in_context
E       AssertionError: assert None == 'https://github.com/o/r/pull/456'
RED   test_ship_phase_skipped_when_pr_creation_fails
E       ... = 'No git remote configured'.startswith('[GH_PR_FAILED]')
GREEN all 5 TestPRCreationAfterDocumentPhase tests PASSED
```

## Real `adw pr` against a private scratch repo

The run used real `gh` (2.76.2) and no Claude, in the session scratchpad and never in the checkout. `smeshko/adw-pr-scratch-20260923` was created with `gh repo create --private --add-readme --clone`, so its default branch is `main`. Branch `feature/pr-scratch` got one commit (`scratch.txt`). A completed run was then seeded through `ContextManager` with this worktree's code:

- `branch_name="feature/pr-scratch"`, `worktree_path=<scratch repo>`, and `pr_url` unset
- a valid `artifacts/document/pr_description.md`
- no `.adw/project.yaml`, so the base branch comes from the new `main` default

**First run: opens the PR and saves `pr_url`**

```
$ adw pr 01M3727GVRP2GP25Q816APE01J
Creating PR from run: 01M3727GVRP2GP25Q816APE01J
Base branch: main

╭─────────────────────────── ✓ Pull Request Created ───────────────────────────╮
│ PR created successfully!                                                     │
│                                                                              │
│ https://github.com/smeshko/adw-pr-scratch-20260923/pull/1                    │
╰──────────────────────────────────────────────────────────────────────────────╯
exit=0

$ jq .pr_url .adw/runs/01M3727GVRP2GP25Q816APE01J/context.json
"https://github.com/smeshko/adw-pr-scratch-20260923/pull/1"
$ jq '.artifacts | has("pr")' .adw/runs/01M3727GVRP2GP25Q816APE01J/context.json
false
$ gh pr view <url> --json baseRefName,headRefName,isDraft,url
{"baseRefName":"main","headRefName":"feature/pr-scratch","isDraft":false,"url":"https://github.com/smeshko/adw-pr-scratch-20260923/pull/1"}
```

**Second run: reports the existing PR without calling `gh`**

```
$ adw pr 01M3727GVRP2GP25Q816APE01J
✓ Run already has a PR:
https://github.com/smeshko/adw-pr-scratch-20260923/pull/1
exit=0
$ gh pr list --state all --json number,url
[{"number":1,"url":"https://github.com/smeshko/adw-pr-scratch-20260923/pull/1"}]
```

**Extra: real `gh`'s "already exists" reply.** This settles the plan's open question about `gh`'s wording. With `pr_url` cleared from `context.json`, `create_pr` runs `gh pr create` again. `gh` 2.76.2 reports that the PR exists, and `create_pr` returns its URL:

```
$ adw pr 01M3727GVRP2GP25Q816APE01J   # pr_url cleared
Base branch: main
│ https://github.com/smeshko/adw-pr-scratch-20260923/pull/1                    │
exit=0
$ jq .pr_url .adw/runs/01M3727GVRP2GP25Q816APE01J/context.json
"https://github.com/smeshko/adw-pr-scratch-20260923/pull/1"
$ gh pr list --state all --json number
[{"number":1}]
```

The PR was then closed (`gh pr close`: `✓ Closed pull request smeshko/adw-pr-scratch-20260923#1`). The repo is still there: deleting it needs the `delete_repo` scope, which this token lacks, and Ivo decides that.

## Notes

- **Real-repo evidence covers `adw pr`, not `adw run`.** The epic's Validation line asks for `context.json` from a real `adw run`. The plan chose real `gh` without Claude instead (Decisions). The document-step path is proved by `TestPRCreationAfterDocumentPhase`, which runs the real `DocumentExtension` and a real `ContextManager` against the fake `gh`.
- **`adw pr --no-open` is rejected:** `No such option: --no-open`. Checked by hand, with no test (ADR-001).
- **Cosmetic, not fixed:** when `gh` returns an existing PR, the panel still says "PR created successfully!". The manual-instructions panel still opens with "GitHub CLI (gh) not found" whatever the error was. Its text is unchanged from before this plan.
