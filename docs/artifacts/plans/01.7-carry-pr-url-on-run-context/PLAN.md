# Plan: Carry the PR URL on the run context

Status: in-progress
Branch: feature/adw-13
Risk: medium
Epic: 01 — Cleanup: test safety, dead code and bug fixes ([epic](../../epics/01-cleanup-safety-dead-code-bugs.md))
Phase: 1.7 — Carry the PR URL on the run context
Linear: ADW-13
Created: 2026-09-23

## Goal

Every PR path (the document step and `adw pr`) sets `context.pr_url` through one core `create_pr`, and nothing closes a ticket before its PR merges.

## Scope

- **One default base branch, `main`.** It lives on `GitConfig.base_branch`. The four `"staging"` fallbacks and the `ship/post.sh` fallback go.
- **Stop closing tickets at run completion (B1).**
  - Delete `task_managers/closer.py`, `task_managers/github_client.py`, and `is_pr_merged` from the `TaskManager` Protocol, `LinearTaskManager` and `NullTaskManager`.
  - Delete `RunLifecycle._maybe_close_task` and the `task_uuid` plumbing.
  - `auto_close` still loads, does nothing, and `finalize_success` logs one warning.
  - Drop the wizard's auto-close prompt and the generator's commented `auto_close` line.
- **A core `create_pr(context, body, *, base, draft=False) -> str` in `src/adw/core/pr.py`.**
  - It is built from the working parts of `cli/pr.py`: push, title, Linear link, `gh pr create`.
  - It maps `gh` failures to `ADWError` codes, and "already exists" returns the existing URL.
- **The document step calls `create_pr`.** `DocumentExtension.on_complete` sets `context.pr_url`, or `pr_creation_failed` and `pr_failure_reason`.
- **Delete the `pr_result` plumbing.**
  - `AutoPRResult`, `_PRResultFromContext`, the tuple return of `Orchestrator._execute_phases`, and the `pr_result` parameters.
  - The completion comment and the pipeline summary read `context.pr_url` and `context.pr_failure_reason`.
- **`adw pr` calls `create_pr`** and saves `context.pr_url`. Delete the preflight guesswork: `can_auto_create_pr`, `check_git_remote`, `check_gh_available`, `check_gh_authenticated`, `try_auto_create_pr`, the substring-matched suggestions and hints, `_store_pr_url`, and `--no-open`.
- A `fake_gh` test fixture: an executable `gh` on `PATH` that records its argv and replies with a canned URL or error.
- Doc touch-ups where these docs describe the removed behaviour:
  - `docs/architecture/deep-dive/document-phase.md`
  - `docs/architecture/deep-dive/extensions-system.md`
  - the `auto_close` rows in `docs/features/`

## Out of Scope

- `close_task` on the `TaskManager` Protocol and its two implementations. It has no caller after this plan, but the epic doesn't list it, and Epic 06's "ADW writes Done" may use it.
- The `ship → Done` entry in the default `state_mapping`, which moves the ticket to Done when the ship phase *starts*. Epic 06 (phase 6.2) replaces `state_mapping`-driven writes.
- The drift between the `state_mapping` copies (`sync.py`, the wizard, the dashboard): phase 1.8 (B17).
- The dashboard's `auto_close` toggle and its mutation and field-map entries. Epic 02 removes settings editing. The toggle keeps writing a key that is now a no-op.
- An `adw validate` warning for `auto_close`. The warning is logged at run time only.
- The `ship/post.sh` substring error mapping, and its `task_update_request.json` (phase 1.9).
- The byte-identical `pr_description.md` vs `document_output.md` artifacts (Epic 03).
- Draft PRs before build, and plan-based PR bodies: phase 4.4, which reuses `create_pr`.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). The headlines:

- **`pr_result` is always `None`.** `Orchestrator._execute_phases` always returns `(context, None)`. As a result:
  - The Linear completion comment never includes the PR URL.
  - `_maybe_close_task` gets `pr_url=None`, and `IssueCloser.maybe_close` then closes the ticket with no merge check. With `auto_close: true`, every successful full run closes its ticket (B1).
- **Only the document step sets `context.pr_url`** (`core/extensions/document.py:105`), via `cli.pr.auto_create_pr`. `adw pr` writes `context.artifacts["pr"]`, which nothing reads (B12). Core imports cli for this.
- **The two paths build different PR bodies.** `auto_create_pr` appends the Linear link and `adw pr` doesn't. `_get_base_branch` re-reads `project.yaml` through a `run_dir.parent.parent.parent` hop, while `DocumentExtension._git_config` goes unused.
- **`"staging"` is the runtime fallback in 5 places:**
  - `run_lifecycle.py:561`
  - `extensions/ship.py:156`
  - `cli/pr.py:174` and `cli/pr.py:610`
  - `ship/post.sh:249`

  `GitConfig`, the YAML generator and the wizard all document `main`. This repo's own `.adw/project.yaml` sets `base_branch: staging` explicitly, so ADW's own runs don't change.
- **No fake-binary-on-PATH test exists yet.** Every `gh` test patches `subprocess.run` or `shutil.which`.

## Decisions

- **The default base branch is `main`** (Ivo's choice), on the field: `GitConfig.base_branch: str = "main"`.
  - A `mode="before"` validator maps `None` and `""` to `"main"`, so existing `base_branch: null` configs and blank wizard or dashboard input still load.
  - Every consumer reads the field and has no fallback of its own.
  - `ship/post.sh` falls back to an empty string, and `ShipExtension` treats an empty or missing `base_branch` in the merge record as `git_config.base_branch`.
- **The signature is `create_pr(context, body, *, base, draft=False)`, which differs from the epic's `create_pr(context, base, draft)`.** Phase 4.4 opens a draft PR before any document output exists, so the caller owns the body. `create_pr` still owns the title, the Linear link, the push and `gh`, so both callers produce identical PRs. TASK-006 updates Epic 04's dependency line to this signature.
- **`create_pr` raises bare `ADWError`, not `ConfigError`.** A `gh` failure isn't a config error, and `ADWError` survives phase 1.3's exception trim. It reuses the existing codes `GH_AUTH_ERROR`, `GH_NO_COMMITS`, `GH_PR_FAILED`, `GH_NO_URL` and `GH_TIMEOUT`, and adds two:
  - `GH_NOT_INSTALLED`, for `FileNotFoundError`
  - `GIT_PUSH_FAILED`
- **"Already exists" returns the existing URL.** When `gh` fails with `already exists` and its output holds a `https://…/pull/<n>` URL, `create_pr` returns that URL. Re-running the document step (`resume`, `--phase document`) or `adw pr` then stops failing, and 4.4's draft-then-document flow gets the URL back.
- **Errors are mapped from `gh` output, not predicted by a preflight.**
  - No remote check, no `gh auth status`, no `which gh`.
  - `pr_failure_reason` becomes `str(error)`, which carries the code and the suggestion.
  - The pipeline summary prints that text plus `Run 'adw pr <run-id>' to retry` in place of today's substring-matched hints.
- **`adw pr` on a run that already has `pr_url` prints the URL and exits 0** without calling `gh`.
- **A missing `gh` makes `adw pr` exit 1** (it exited 0 before). It still prints the error and `display_manual_instructions`, which is kept as the fallback.
- **The `auto_close` warning is logged in `RunLifecycle.finalize_success`, not in a validator.** A single `adw run` validates `ProjectConfig` at least three times, and the first time is before the log manager exists. `finalize_success` runs once per completed run.
- **Remove the wizard prompt and the generator's `auto_close` line; leave the dashboard toggle** (Ivo's choice). New configs never advertise the option, and the dashboard settings editor goes in Epic 02.
- **The fake `gh` records its argv as JSON lines.** It is a `#!/bin/sh` script that runs `sys.executable`. PR bodies contain newlines, so one argv per line would be ambiguous. Pushes in tests go to a local bare repo (`git init --bare`) added as `origin`.
- **Real-repo evidence: real `gh`, no Claude** (Ivo's choice). The final validation drives the real `adw pr` against a private scratch GitHub repo. The document-step path is proved by the fake-`gh` orchestrator test.

## Risks

- **A project that relied on the silent `staging` fallback now targets `main`.** Mitigation: projects without `base_branch` set already assumed the documented `main`; ADW's own config sets `staging` explicitly. The change is called out in the PR description.
- **The "already exists" URL parse depends on `gh`'s message text.** Mitigation: when no URL is found, fall back to `GH_PR_FAILED` with the full stderr, so a wording change degrades to today's behaviour.
- **The fake `gh` depends on `PATH` order and the executable bit.** Mitigation: the fixture prepends its bin dir with `monkeypatch.setenv`, never clears the environment (AGENTS.md), and `chmod`s the script like `tests/integration/test_hooks.py` does.
- **The dashboard settings indicator test assumes a `None` default.** `test_git_badge_count_matches_changed` uses `base_branch="main"` as a changed value. Mitigation: switch it to `"develop"` in TASK-001.
- **Deleting `task_uuid` from `Orchestrator.run` breaks any caller that passes it.** Mitigation: grep shows the only caller is `cli/app.py:440`, and no test passes it.
- **The real-repo validation creates a GitHub repo, which is outward-facing.** Mitigation: it is private, and deleting it needs the `delete_repo` scope, so ask Ivo before deleting.

## Acceptance Criteria

- [ ] After a mocked run whose document step creates a PR through the fake `gh`, `context.json` on disk has `pr_url` set, and the completion comment text posted to the task manager contains it. Evidence: `TestPRCreationAfterDocumentPhase` output.
- [ ] After `adw pr <run-id>` against a completed run with no PR, `context.json` has `pr_url` set. Evidence:
  - the CLI test output with the fake `gh`
  - the real run's `context.json` against a private scratch GitHub repo, in `VALIDATION.md`
- [ ] With `auto_close: true` and a Linear task, a completed run leaves the ticket open (`close_task` and `update_status` to Done are never called from `finalize_success`), and the deprecation warning is logged exactly once. Evidence: the `caplog` test output.
- [ ] `grep -rn "pr_result\|IssueCloser\|GitHubClient\|is_pr_merged" src` returns nothing.
- [ ] `grep -rn "AutoPRResult\|_PRResultFromContext\|can_auto_create_pr\|check_git_remote\|check_gh_authenticated\|try_auto_create_pr\|no_open\|task_uuid" src` returns nothing.
- [ ] `grep -rn "staging" src/adw` hits only `hooks/git_commit.py`, where "staging" means the git index, not a branch.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Default the base branch to main in one place
- [x] TASK-002: Stop closing tickets at run completion
- [ ] TASK-003: Add a core create_pr with mapped gh errors
- [ ] TASK-004: Create the document step's PR through create_pr (depends on TASK-001,TASK-002,TASK-003)
- [ ] TASK-005: Route adw pr through create_pr (depends on TASK-001,TASK-004)
- [ ] TASK-006: Final Validation
