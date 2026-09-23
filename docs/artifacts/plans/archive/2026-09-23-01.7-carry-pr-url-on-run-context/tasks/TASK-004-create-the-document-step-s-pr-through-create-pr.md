# TASK-004: Create the document step's PR through create_pr

Depends on: TASK-001, TASK-002, TASK-003
Suggested commit: `fix(document): carry the PR URL on the run context`

## Goal

The document step opens its PR through `core.pr.create_pr` and sets `context.pr_url`. The completion comment and the pipeline summary read the context, and the `pr_result` plumbing is gone.

## Files

- `src/adw/core/extensions/document.py`:
  - `on_complete` sets `pr_creation_attempted`, then calls `load_pr_description(self._runs_dir / context.run_id)` and `create_pr(context, body, base=self._git_config.base_branch)`.
  - On success it sets `pr_url`. On `ADWError` it sets `pr_creation_failed=True` and `pr_failure_reason=str(error)`, and logs a warning.
  - Delete `_create_pr` and the `TYPE_CHECKING` import of `AutoPRResult`.
- `src/adw/core/orchestrator.py`:
  - `_execute_phases` (690–760) returns `RunContext`; update its docstring.
  - `run()` (339–342) and `resume()` (534–540) unpack a single value and call `finalize_success(context)`.
  - Drop the `AutoPRResult` import (38).
- `src/adw/core/run_lifecycle.py`:
  - Delete `_PRResultFromContext` (48–60) and the `AutoPRResult` import (38).
  - `finalize_success(context)` loses `pr_result`.
  - `_post_completion_comment(context)` passes `pr_url=context.pr_url`.
  - `_show_pipeline_summary(context, status)`: for completed runs it passes `pr_url=context.pr_url` and `pr_error=context.pr_failure_reason if context.pr_creation_failed else None`, and nothing otherwise. Update the calls at 328, 398 and 457.
- `src/adw/cli/progress.py`:
  - `show_pipeline_summary(..., pr_url: str | None = None, pr_error: str | None = None)` replaces `pr_result`.
    - With `pr_url`: print `PR Created: <url>`.
    - With `pr_error`: print the description path, the error text dimmed, and `Run 'adw pr <run_id>' to retry`.
    - With neither: print the description path, as today.
  - Delete the substring hints (341–352), `try_auto_create_pr` (371–412) and the `AutoPRResult` import (33).
- `src/adw/cli/pr.py`: delete `AutoPRResult`, `auto_create_pr`, `can_auto_create_pr` and `check_git_remote`. `create_pr_via_gh`, `push_branch_to_remote`, `check_gh_available`, `check_gh_authenticated` and `_store_pr_url` stay for `adw pr` until TASK-005.
- Docs: update the PR-creation flow and remove `auto_create_pr` / `pr_result` in:
  - `docs/architecture/deep-dive/document-phase.md` (70, 163–179, 240)
  - `docs/architecture/deep-dive/extensions-system.md` (162, 304)
- Tests:
  - `tests/unit/core/test_orchestrator.py` (`TestPRCreationAfterDocumentPhase`)
  - `tests/unit/core/test_run_lifecycle.py` (`TestFinalizeSuccess`)
  - `tests/unit/cli/test_progress.py`
  - `tests/unit/cli/test_pr.py`

## Acceptance

- [ ] **`test_pr_url_stored_in_context`** (rewritten). This is the epic criterion.
  - Setup:
    - An `Orchestrator` with mocked phase runner, a real `ContextManager(runs_dir)` and the real `DocumentExtension(GitConfig(), runs_dir)`.
    - `fake_gh` on `PATH`, and a `StatusSyncService` over a `MagicMock` task manager with a `task_info`.
    - The phase-runner side effect writes a valid `artifacts/document/pr_description.md` when `phase == "document"`, and creates the run dir.
  - After `run()`:
    - `json.loads((runs_dir / run_id / "context.json").read_text())["pr_url"]` equals the fake URL.
    - The text passed to the task manager's `post_comment` contains that URL.
- [ ] `test_pr_created_after_document_phase` (rewritten): `fake_gh.calls()` is empty while build and validate run, has one call when ship starts, and that call's `--base` is `main`.
- [ ] `test_ship_phase_skipped_when_pr_creation_fails` (rewritten): with `fake_gh.reply(stderr="boom", exit_code=1)`, ship is skipped, and `context.pr_failure_reason` starts with `[GH_PR_FAILED]`.
- [ ] `TestFinalizeSuccess::test_posts_completion_comment` asserts `post_completion_comment` was called with `pr_url=context.pr_url` for a context that has `pr_url` set.
- [ ] Pipeline summary tests:
  - A `pr_url` renders `PR Created: <url>`.
  - A `pr_error` renders the error text and `adw pr <run_id>`.
  - With neither, it renders the description path.
- [ ] `grep -rn "pr_result\|AutoPRResult\|_PRResultFromContext\|auto_create_pr\|can_auto_create_pr\|check_git_remote" src` returns nothing, and `grep -rn "adw.cli.pr" src/adw/core` returns nothing.
- [ ] `uv run pytest tests/unit/core tests/unit/cli tests/integration/test_document_phase.py tests/integration/cli/test_progress_integration.py -o addopts=""` passes.

Evidence:
- the RED run: `test_pr_url_stored_in_context` fails on today's code, because the comment gets `pr_url=None` (the extension still goes through `auto_create_pr`)
- the GREEN run
- the grep output

## Steps

### RED
- [ ] Rewrite `TestPRCreationAfterDocumentPhase` in `tests/unit/core/test_orchestrator.py` to use `fake_gh` and the real `DocumentExtension`, and drop every `patch("adw.cli.pr.auto_create_pr")` and `AutoPRResult`.
  - Enter `tmp_path` with `monkeypatch.chdir`.
  - With worktrees disabled and no `branch_name`, `create_pr` doesn't push, so no git remote is needed.
- [ ] Assert the comment text through the `MagicMock` task manager's `post_comment` call args.
- [ ] Update `TestFinalizeSuccess::test_posts_completion_comment` to check the `pr_url` kwarg.
- [ ] Rewrite `TestPipelineSummaryWithPRResult` (rename it `TestPipelineSummaryPR`) for `pr_url`/`pr_error`, and delete `TestTryAutoCreatePr`.
- [ ] Run and confirm `test_pr_url_stored_in_context` fails on the comment assertion.

### GREEN
- [ ] Switch `DocumentExtension.on_complete` to `load_pr_description` + `create_pr`.
- [ ] Remove the tuple return and `pr_result` from the orchestrator and the lifecycle, and pass `context.pr_url` to the comment.
- [ ] Change `show_pipeline_summary` to `pr_url`/`pr_error`, and delete `try_auto_create_pr`.
- [ ] Delete `AutoPRResult`, `auto_create_pr`, `can_auto_create_pr` and `check_git_remote` from `cli/pr.py`, with `TestAutoPRResult`, `TestCanAutoCreatePr`, `TestCheckGitRemote` and `TestAutoCreatePr`.
- [ ] Run the partial suite until it's green.

### REFACTOR
- [ ] Update the two deep-dive docs.
- [ ] Update the `DocumentExtension` class docstring: it calls `core.pr.create_pr`, and `git_config` supplies the base branch.
- [ ] Run the greps, then `scripts/preflight.sh`.

## Notes

- **Catch only `ADWError` in `on_complete`.** `create_pr` and `load_pr_description` raise nothing else by contract. `ExtensionRegistry.call_on_complete` still logs anything unexpected.
- **`pr_failure_reason` is `str(error)`,** i.e. `"[CODE] message\nSuggestion: …"`. `ShipExtension.should_skip` only reads `pr_creation_failed`, so its behaviour is unchanged.
- **The integration test `tests/integration/test_document_phase.py` never reaches `on_complete`** (it drives `PhaseRunner`). It should pass unchanged, and is in the run list only as a guard.
