# TASK-005: Route adw pr through create_pr

Depends on: TASK-001, TASK-004
Suggested commit: `fix(cli): set context.pr_url from adw pr`

## Goal

`adw pr <run-id>` opens the PR through `core.pr.create_pr` and saves `context.pr_url` (B12). The preflight guesswork, `artifacts["pr"]` and `--no-open` are gone.

## Files

- `src/adw/cli/pr.py`. `pr()` becomes:
  1. Resolve the run as today and require `status == "completed"`.
  2. If `context.pr_url` is set, print it and exit 0.
  3. Load the body with `load_pr_description(run_dir)`, and the base with `_get_base_branch(run_dir)`.
  4. Call `create_pr(context, body, base=base, draft=draft)`.
  5. Save `context.model_copy(update={"pr_url": url})` with `ContextManager(runs_dir)`, and print the success panel.
  6. On `ADWError`, print the error panel (code, message, suggestion) and `display_manual_instructions`, then exit 1.

  Delete from the same file:
  - `create_pr_via_gh`, `push_branch_to_remote`, `check_gh_available`, `check_gh_authenticated` and `_store_pr_url`
  - the `--no-open` option and the `ConfigError` import, if it is now unused

  Update the module and command docstrings.
- `tests/unit/cli/test_pr.py`:
  - `TestPrCommand` drives the real command through `CliRunner` with `fake_gh`, against a completed run seeded under `tmp_path/.adw/runs/<id>/`, which holds `context.json` and `artifacts/document/pr_description.md`.
  - Delete `TestCheckGhAvailable`, `TestCheckGhAuthenticated`, `TestCreatePrViaGh` (moved in spirit to `tests/unit/core/test_pr.py`), `TestStorePrUrl` and `test_pr_with_no_open_option`.
  - Keep `TestDisplayManualInstructions` and `TestGetBaseBranch`.
- `docs/architecture/deep-dive/document-phase.md`: the `adw pr` section, if it mentions `--no-open` or the preflight.

## Acceptance

- [ ] `test_pr_sets_pr_url`: `adw pr <run-id>` on a completed run without `pr_url` exits 0, and the `context.json` on disk has `pr_url` equal to the fake URL. `"pr"` is not in `artifacts`. This is the epic criterion.
- [ ] `test_pr_uses_configured_base_and_draft`:
  - With `.adw/project.yaml` setting `git.base_branch: develop` and `--draft`, the recorded argv has `--base develop` and `--draft`.
  - With no config, it has `--base main`.
- [ ] `test_pr_body_includes_linear_link`: a run with `task_id`/`task_info` produces a `--body` ending in the Linear link, the same as the document step.
- [ ] `test_pr_existing_url_short_circuits`: a run with `pr_url` already set exits 0, prints the URL, and `fake_gh.calls()` is empty.
- [ ] `test_pr_gh_missing_shows_manual_instructions`: with `PATH` pointing at an empty dir, the command exits 1, the output contains `GH_NOT_INSTALLED` and the manual-instructions title, and `context.json` has no `pr_url`.
- [ ] `test_pr_gh_failure_exits_1`: `fake_gh.reply(stderr="boom", exit_code=1)` gives exit 1 with `GH_PR_FAILED` in the output.
- [ ] The existing not-found, not-complete and no-description cases still exit 1.
- [ ] `adw pr --no-open` is rejected as an unknown option. Checked by hand, no test (ADR-001).
- [ ] `grep -rn "can_auto_create_pr\|check_git_remote\|check_gh_authenticated\|try_auto_create_pr\|no_open\|artifacts\[\"pr\"\]\|_store_pr_url\|create_pr_via_gh" src` returns nothing.
- [ ] `uv run pytest tests/unit/cli/test_pr.py tests/unit/core/test_pr.py -o addopts=""` passes.

Evidence:
- the RED run: `test_pr_sets_pr_url` fails on the TASK-004 code, because only `artifacts["pr"]` is written
- the GREEN run
- the grep output
- the `adw pr --no-open` error line

## Steps

### RED
- [ ] Add a `completed_run` fixture in `tests/unit/cli/test_pr.py`. It writes, under `tmp_path/.adw/runs/<ULID>/`:
  - a completed `RunContext` through `ContextManager`
  - a valid `artifacts/document/pr_description.md`

  The autouse `isolated_cwd` in `tests/unit/cli/conftest.py` already puts cwd at `tmp_path`.
- [ ] Rewrite `TestPrCommand` around `fake_gh` and `completed_run` with the cases in Acceptance. Remove every `patch("adw.cli.pr.subprocess.run")`, `patch("…check_gh_available")` and `patch("…check_gh_authenticated")`.
- [ ] Run and confirm `test_pr_sets_pr_url`, `test_pr_body_includes_linear_link` and `test_pr_existing_url_short_circuits` fail.

### GREEN
- [ ] Rewrite `pr()` as described in Files, and delete the dead helpers, `--no-open`, and their tests.
- [ ] Run the partial suite until it's green.

### REFACTOR
- [ ] `_get_base_branch(run_dir)` keeps its `project.yaml` lookup, now with no fallback of its own (TASK-001). Leave it; replacing the `parent.parent.parent` hop with cwd config loading belongs to Epic 02's config-loading consolidation.
- [ ] Run the grep, then `scripts/preflight.sh`.

## Notes

- **A missing `gh` now exits 1, not 0.** It is a failure; the manual-instructions panel is still printed.
- **`find_most_recent()` returns runs of any status** despite the help text. Leave that alone; the `status == "completed"` check already guards it.
- **Don't add `ContextManager` locking of your own.** `ContextManager.save` is atomic under its file lock.
