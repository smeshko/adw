# TASK-003: Add a core create_pr with mapped gh errors

Depends on: None
Suggested commit: `feat(core): add create_pr with mapped gh errors`

## Goal

`adw.core.pr.create_pr(context, body, *, base, draft=False) -> str` pushes the run's branch, opens the PR with `gh`, and returns its URL, or raises `ADWError` with a mapped code. It is proved against a fake `gh` on `PATH`.

## Files

- `src/adw/core/pr.py` (new), with the contents below.
  - Moved here from `cli/pr.py`, unchanged in behaviour except for the exception class:
    - `generate_pr_title(context) -> str` (from `_generate_pr_title`, 613–662)
    - `load_pr_description(run_dir) -> str` (from `_load_pr_description` and `_get_pr_description_path`, 524–580). It returns `PRDescription.from_markdown(text).to_markdown()`, and raises `ADWError` with `PR_DESCRIPTION_NOT_FOUND` or `PR_DESCRIPTION_INVALID`.
  - `create_pr(context, body, *, base, draft=False) -> str`. In order:
    1. If `context.branch_name` is set, run `git push -u origin <branch>` in `context.worktree_path` (timeout 120 s). A non-zero exit, timeout or `OSError` raises `GIT_PUSH_FAILED`, with stderr in the message.
    2. If `context.task_id and context.task_info` are set, append `\n\n---\nLinear: https://linear.app/<team>/issue/<ID>` to the body, using the logic from `cli/pr.py:418–423`.
    3. Run `gh pr create --title <generate_pr_title(context)> --body <body> --base <base> [--head <branch>] [--draft]` with `capture_output=True, text=True, timeout=60`.
    4. Map the result, in this order:
       - `FileNotFoundError` → `GH_NOT_INSTALLED`, suggestion "Install the GitHub CLI (https://cli.github.com) or open the PR manually"
       - `TimeoutExpired` → `GH_TIMEOUT`, recoverable
       - non-zero exit, output contains `already exists` and a URL matching `https://\S+/pull/\d+` → return that URL
       - `auth` or `login` → `GH_AUTH_ERROR`, recoverable
       - `no commits` → `GH_NO_COMMITS`
       - anything else → `GH_PR_FAILED`, carrying the stderr
       - exit 0 with empty stdout → `GH_NO_URL`
  - Every error is a bare `ADWError(code, message, suggestion=…, recoverable=…)`.
- `src/adw/cli/pr.py`:
  - Delete `_generate_pr_title`, `_load_pr_description` and `_get_pr_description_path`, and import `generate_pr_title` and `load_pr_description` from `adw.core.pr`.
  - `auto_create_pr` and `pr()` catch `ADWError` where they caught `ConfigError` around the description load.
  - `create_pr_via_gh` and `push_branch_to_remote` stay until TASK-004 and TASK-005 remove their callers.
- `tests/conftest.py`: the new `fake_gh` fixture (see Steps).
- `tests/unit/core/test_pr.py` (new): the `create_pr` tests, plus `TestGeneratePrTitle`, `TestLoadPrDescription` and `TestGetPrDescriptionPath`, moved from `tests/unit/cli/test_pr.py` and retargeted at `adw.core.pr`.

## Acceptance

- [ ] **Success** (a `git_repo` with a local bare `origin`, `context.branch_name="feature/x"`, `worktree_path` set to the repo):
  - `create_pr` returns the fake URL.
  - `git ls-remote origin feature/x` shows the pushed commit.
  - The recorded argv is exactly `pr create --title <title> --body <body> --base main --head feature/x`, with no `--draft`.
- [ ] With `draft=True`, the argv ends with `--draft`.
- [ ] With `task_id` and `task_info` set, the `--body` value ends with `Linear: https://linear.app/<team>/issue/<ID>`.
- [ ] With no `branch_name`, `git push` doesn't run and `--head` is absent.
- [ ] Errors, parametrized over the fake `gh`'s stderr and exit code, each raise `ADWError` with the listed code:
  - auth → `GH_AUTH_ERROR`
  - no commits → `GH_NO_COMMITS`
  - other → `GH_PR_FAILED`, with the stderr in the message
  - exit 0 with empty stdout → `GH_NO_URL`
- [ ] With "already exists" plus a URL in stderr, `create_pr` returns that URL. "Already exists" with no URL raises `GH_PR_FAILED`.
- [ ] With `PATH` pointing at an empty dir, `create_pr` raises `GH_NOT_INSTALLED`.
- [ ] With `branch_name` set and no `origin`, it raises `GIT_PUSH_FAILED`, and the fake `gh` records no call.
- [ ] `uv run pytest tests/unit/core/test_pr.py tests/unit/cli/test_pr.py -o addopts=""` passes.

Evidence: the test output of `tests/unit/core/test_pr.py`, first RED on a missing module, then GREEN.

## Steps

### RED
- [ ] Add a `fake_gh` fixture to `tests/conftest.py`. It returns a small `FakeGh` dataclass:
  - `bin_dir/gh` is a `#!/bin/sh` script that runs `"{sys.executable}" -c '…'`. The Python snippet:
    - appends `json.dumps(sys.argv[1:])` plus a newline to `FAKE_GH_DIR/calls.jsonl`
    - writes `FAKE_GH_DIR/stdout` to stdout and `FAKE_GH_DIR/stderr` to stderr
    - exits with the int in `FAKE_GH_DIR/exit_code`

    `chmod` the script with `stat.S_IEXEC`.
  - Fixture setup: `monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")` and `monkeypatch.setenv("FAKE_GH_DIR", …)`. Never clear the environment.
  - Methods: `reply(stdout="https://github.com/o/r/pull/1\n", stderr="", exit_code=0)` rewrites the three files; `calls() -> list[list[str]]` reads the JSON lines.
  - Default reply: success with `https://github.com/o/r/pull/1`.
- [ ] Add a helper fixture in `tests/unit/core/test_pr.py`:
  - It builds on `git_repo` plus `monkeypatch.chdir`.
  - It runs `git init --bare` into `tmp_path / "origin.git"`, adds it as `origin`, and commits one file on `feature/x`.
- [ ] Write the `create_pr` tests from Acceptance. The timeout case patches `adw.core.pr.subprocess.run` to raise `TimeoutExpired`; it's the only mock.
- [ ] Move the three helper test classes into `tests/unit/core/test_pr.py`, importing from `adw.core.pr` and expecting `ADWError`.
- [ ] Run and confirm the tests fail on the missing module.

### GREEN
- [ ] Create `src/adw/core/pr.py` with the moved helpers, the private `_push_branch(context)`, and `create_pr`.
- [ ] Point `cli/pr.py` at the moved helpers, and delete its copies and their old tests in `tests/unit/cli/test_pr.py`.
- [ ] Run the partial suite until it's green.

### REFACTOR
- [ ] Keep `create_pr`'s error mapping in one small `_map_gh_failure(output) -> str | ADWError` helper. It returns the existing URL or the error, so `create_pr` reads top to bottom.
- [ ] Add a module docstring stating that `core.pr` owns PR creation, and that `cli/pr.py` and the document extension call it.
- [ ] `scripts/preflight.sh`.

## Notes

- **`core/pr.py` must not import anything from `adw.cli`.**
- **Why `create_pr` takes `body`:** phase 4.4's draft PR has no document output. Keep the signature exactly `create_pr(context, body, *, base, draft=False)`.
- **The URL parse matches only `https://…/pull/<n>`,** so a stray URL in an unrelated error isn't mistaken for the PR.
- **`gh` runs with no `cwd`, as today.** `--head` names the branch explicitly, and the push already ran in the worktree.
