# TASK-005: Trim ship hooks to live steps and read ADW_PR_URL

Depends on: None
Suggested commit: `refactor(ship): trim dead hook steps and read ADW_PR_URL`

## Goal

The ship hooks read the run's PR from `ADW_PR_URL`, which Python sets from `context.pr_url`, and stop writing files and variables that nothing reads.

## Files

- `src/adw/defaults/commands/ship/pre.sh`:
  - STEP 4 looks up `pr_ref="${ADW_PR_URL:-$current_branch}"` with `gh pr view "$pr_ref" --json …`. The error message names whichever it used.
  - Delete STEP 8, the four `export`s, which die with the hook's own process.
  - Header:
    - Replace "Environment variables exported by this hook" with "Writes `pre_hook_vars.json` (pr_number, pr_url, pr_state, pr_mergeable) for template rendering".
    - List `ADW_PR_URL` under the inputs.
- `src/adw/defaults/commands/ship/post.sh`:
  - STEP 1: when the LLM output has no `PR_NUMBER:`, fall back to the trailing path segment of `ADW_PR_URL`, only if it is all digits:
    ```bash
    url_number="${ADW_PR_URL##*/}"
    [[ "$url_number" =~ ^[0-9]+$ ]] || url_number=""
    pr_number="${pr_number_from_output:-$url_number}"
    ```
    Use the same fallback in the no-output branch.
  - STEP 2: delete the `ship_status.json` block, including `json_escape` and `pr_merge_approved_json`. Keep `ship_report.md` and `release_notes.md`.
  - Delete STEP 6, the `ADW_TASK_ID` / `task_update_request.json` block.
  - Header:
    - Drop `ADW_PR_NUMBER`, `ADW_TASK_ID` and item 7, "Updates task manager status".
    - Add `ADW_PR_URL`, used for the PR number fallback, and `ADW_BRANCH_NAME`, used for remote branch deletion.
    - Renumber the steps.
- `tests/integration/test_ship_post_hook.py`:
  - Delete `TestShipPostHookTaskManager` and `TestShipPostHookArtifacts::test_status_json_artifact_valid`.
  - In `TestShipPostHookStatusParsing::test_parse_success_status`, replace the `ship_status.json` read with assertions on the `Parsed status:` stdout lines.
  - Replace every `"ADW_PR_NUMBER": "N"` with `"ADW_PR_URL": "https://github.com/o/r/pull/N"`, and rename `test_pr_number_from_output_overrides_env` accordingly.
  - Update the module docstring's list: drop "Task manager integration".
- `tests/integration/test_ship_pre_hook.py` (new): tests with a fake `gh` first on `PATH`.

## Acceptance

- [ ] `test_pr_number_from_adw_pr_url`: LLM output with `PR_MERGE_APPROVED: true` and no `PR_NUMBER:`, plus `ADW_PR_URL=https://github.com/o/r/pull/77`. Stdout contains `PR Number: 77` and `gh pr merge 77 --squash`.
- [ ] `test_non_numeric_pr_url_is_ignored`: `ADW_PR_URL=https://example.com/not-a-pr`, and no `PR_NUMBER:`. The hook reports "Cannot merge - no PR number available", and exits 1 when approved.
- [ ] `test_no_status_or_task_files_written`: after an approved run with `ADW_TASK_ID` set, `ADW_ARTIFACTS_DIR` contains neither `ship_status.json` nor `task_update_request.json`.
- [ ] `test_pre_hook_looks_up_pr_by_url` (new file):
  - Setup:
    - In `git_repo`, on a feature branch, with a fake `gh` that exits 0 for `auth status`, echoes fixed JSON for `pr view`, and appends its argv to `gh_calls.log`.
    - `ADW_PR_URL=https://github.com/o/r/pull/5`.
  - Assert:
    - `gh_calls.log` has `pr view https://github.com/o/r/pull/5 --json …`
    - `pre_hook_vars.json` has `"pr_number": "5"`
    - exit 0
- [ ] `test_pre_hook_falls_back_to_branch`: without `ADW_PR_URL`, `gh pr view` receives the current branch name.
- [ ] `grep -rn "ADW_PR_NUMBER\|ADW_TASK_ID\|ship_status\|task_update_request" src tests` returns nothing.
- [ ] `uv run pytest tests/integration/test_ship_post_hook.py tests/integration/test_ship_pre_hook.py tests/unit/core/test_ship_extension.py -o addopts=""` passes.

Evidence:
- the RED run: today's `post.sh` ignores `ADW_PR_URL` and writes both files, and `pre.sh` always queries the branch
- the GREEN run
- the empty grep

## Steps

### RED
- [ ] Write the three new `post.sh` tests, and the two `pre.sh` tests in the new file.
- [ ] The fake `gh` is a `#!/bin/bash` script in `tmp_path / "bin"`. It echoes `{"number":5,"url":"…","state":"OPEN","mergeable":"MERGEABLE","title":"t"}` for `pr view`, and handles `auth status` with exit 0. Prepend its directory to the real `PATH`, so `git` and `jq` still resolve.
- [ ] Skip the `pre.sh` tests with a reason when `shutil.which("jq")` is `None`.
- [ ] Run, and confirm the new tests fail.

### GREEN
- [ ] Edit `pre.sh` and `post.sh` as above.
- [ ] Update the existing `post.sh` tests: `ADW_PR_URL` instead of `ADW_PR_NUMBER`, and delete the dead-file tests.
- [ ] Run the three test files green.

### REFACTOR
- [ ] Re-read both headers against the code; they should list exactly the variables the scripts read.
- [ ] `bash -n` both scripts.
- [ ] `scripts/preflight.sh` passes.

## Notes

- Keep `pre_hook_vars.json`: `PhaseRunner._load_and_render_prompt` merges it into the ship template variables.
- Keep `merge_record.json`, including `"pr_number": $pr_number` as a JSON number: `ShipExtension.on_complete` reads it. The digits-only guard keeps it valid JSON.
- `gh pr view` accepts a URL, a number or a branch, so `pr_ref` needs no parsing.
- The existing `post.sh` tests set `PATH=/usr/bin:/bin`, and assert on the printed merge command, not on `gh` succeeding. Keep that style for the new `post.sh` tests.
