# Research: Carry the PR URL on the run context

Curated findings only — no raw conversation transcripts. Line numbers are at `f61f8873`.

## Key Files & Directories

- **`src/adw/cli/pr.py`** (867 lines):
  - `create_pr_via_gh` (170–282):
    - The command is `gh pr create --title --body --base [--head] [--draft]`, run with `capture_output`, `timeout=60`, and **no `cwd`**. The URL comes from stdout.
    - Error mapping: `auth`/`login` → `GH_AUTH_ERROR`, `no commits` → `GH_NO_COMMITS`, anything else → `GH_PR_FAILED`, empty stdout → `GH_NO_URL`, timeout → `GH_TIMEOUT`, all as `ConfigError`. A missing `gh` (`FileNotFoundError`) is **not** caught.
  - `push_branch_to_remote` (88–135) runs `git push -u origin <branch>` in `context.worktree_path`, with a 120 s timeout, and returns `(ok, err)`. No test covers it.
  - `auto_create_pr` (352–464), used by the document step, never raises. In order, it:
    1. runs the preflight: `can_auto_create_pr` → `check_git_remote`, `check_gh_available`, `check_gh_authenticated`
    2. maps suggestions by substring (387–392)
    3. loads the description
    4. builds the title, then appends the Linear link (418–423)
    5. pushes
    6. calls `create_pr_via_gh(draft=False)`
    7. calls `_store_pr_url`
  - The `pr()` command (692–866):
    - Preflight: if `which gh` fails it shows the manual instructions and exits **0**. If `gh auth status` fails it exits 1.
    - Then it pushes, runs `create_pr_via_gh(draft, no_open)` and `_store_pr_url`.
    - It adds no Linear link. `--no-open` is discarded (`_ = no_open`, 223–226).
  - `_store_pr_url` (665–689) appends to `context.artifacts["pr"]` and saves. It never sets `pr_url`, and nothing reads `artifacts["pr"]` (B12).
  - `_get_base_branch(run_dir)` (583–610) loads `project.yaml` from `run_dir.parent.parent.parent` and falls back to `"staging"`.
  - Also moving to core: `_load_pr_description` (546–580) with `_get_pr_description_path` (524–543), and `_generate_pr_title` (613–662).
- **`src/adw/core/extensions/document.py`**:
  - `on_complete` (70–133) sets `pr_creation_attempted`, then either `pr_url` or `pr_creation_failed`/`pr_failure_reason`. It catches every exception.
  - `_create_pr` (161–173) lazily imports `adw.cli.pr.auto_create_pr`: core depends on cli.
  - `self._git_config` is stored but never read.
- **`src/adw/core/extensions/registry.py:135–150`**: `call_on_complete` swallows extension exceptions with a warning. `DocumentExtension` must catch `ADWError` itself to still record the failure.
- **`src/adw/core/orchestrator.py`**:
  - `_execute_phases` (690–760) returns `tuple[RunContext, AutoPRResult | None]` and always ends with `return context, None`.
  - Callers: `run()` at 339–342 (passes `pr_result` and `task_uuid` to `finalize_success`) and `resume()` at 534–540.
  - `run()` takes `task_uuid` (294, docstring 313). `AutoPRResult` is imported under `TYPE_CHECKING` (38).
  - `on_complete` runs from `_execute_phase_with_transitions` (1022), so `run`, `resume`, `run_single_phase` and `continue_from_run` all create the PR.
- **`src/adw/core/run_lifecycle.py`**:
  - `_PRResultFromContext` (48–60).
  - `finalize_success(context, *, pr_result, task_uuid)` (269–344) calls, in order:
    - `_post_completion_comment(context, pr_result)` → `pr_url=pr_result.pr_url if pr_result else None` (789–812)
    - `_maybe_close_task(task_uuid, pr_url)` (815–863)
    - `_show_pipeline_summary(context, status, pr_result)` (643–690)
  - `_fetch_base_branch` (547–580): `self.git_config.base_branch or "staging"`.
  - `task_manager_config` is held at 145.
- **`src/adw/cli/progress.py`**:
  - `show_pipeline_summary(..., pr_result)` (272–369) picks its hints by substring-matching `pr_result.reason` against `remote`, `installed` and `authenticated` (341–352).
  - `try_auto_create_pr` (371–412) has no caller in src.
- **`src/adw/task_managers/`**:
  - `closer.py`: `IssueCloser.maybe_close` closes the ticket when `pr_url` is None (76–89).
  - `github_client.py`: GitHub REST merge check, using `GITHUB_TOKEN`.
  - `base.py:118`, `linear.py:409` and `null.py:91` define `is_pr_merged`.
  - `close_task` (base 104, linear 321, null 82) loses its only caller.
- **`src/adw/models/config.py`**:
  - `TaskManagerConfig.auto_close` (430). Its default `state_mapping` (411–421) maps `ship` → Done.
  - `GitConfig.base_branch: str | None = None` (475), documented as "falls back to 'main'".
- **`src/adw/core/extensions/ship.py:156`** reads `merge_record.get("base_branch", "staging")` for the post-merge checkout and pull.
  - `ShipExtension(project_root)` has no `git_config`.
  - It is registered in `core/extensions/__init__.py:66`, where `git_config` is available.
- **`src/adw/defaults/commands/ship/post.sh:249`**: `gh pr view … --jq '.baseRefName' || echo "staging"`, written into `merge_record.json` (351).
- **`src/adw/cli/app.py`**: 316–322 compute `task_uuid` from `task_info.id`, and 435–441 pass it to `orchestrator.run`. `task_info` itself stays, because `context.task_info` needs it.
- **`src/adw/cli/wizard/task_manager.py`**: `_prompt_auto_close` (254–268), called at 128–129. The `auto_close` keys are in the returned dicts (141, 159).
- **`src/adw/config/yaml_generator.py`**:
  - 298 and 329 write `# auto_close: false  # Close task when PR merged`.
  - 270 writes `# base_branch: null  # PR base branch (defaults to main)`.

## Architecture Facts

- `RunContext` (`models/context.py`) already has `pr_url` (114), `pr_creation_attempted` (119), `pr_creation_failed` (125) and `pr_failure_reason` (131).
  - `ShipExtension.should_skip` uses the failure pair to skip ship.
  - `hooks/environment.py:119` exports `ADW_PR_URL`.
  - The dashboard reads `pr_url` (`routes.py:527,544,674`).
- `ContextManager.save` (`core/context_manager.py:57`) writes `context.json` atomically under a file lock.
- The completion comment is built by `StatusSyncService.post_completion_comment(context, pr_url=…)` (`task_managers/sync.py:343`), which calls `CommentFormatter.format_run_complete`. That adds `**Pull Request:** <url>` when `pr_url` is truthy (`comments.py:274`).
  - `StatusSyncService(task_manager, config, task_info=None)`.
- `ADWError(code, message, *, suggestion=None, recoverable=False)`. `str(err)` is `"[CODE] message\nSuggestion: …"`.
- `PR_DESCRIPTION_ARTIFACT = "artifacts/document/pr_description.md"` (`core/constants.py:25`).
- `MockExecutor`'s default response is `"Mock response"`, which `PRDescription.from_markdown` rejects. A plain mocked `adw run` therefore records `pr_creation_failed`, not a PR.
- `tests/unit/core/` and `tests/unit/cli/` are packages with an `__init__.py`, so `tests/unit/core/test_pr.py` can sit beside `tests/unit/cli/test_pr.py`.

## Constraints

- Phase 1.3 cuts `exceptions.py` down to `ADWError`, `ConfigError`, `StateError`, `LLMError`, `TaskError`, `HookError` and `WorktreeError`. Don't add a new exception class.
- Phase 4.4 reuses `create_pr(draft=True)` before build, and needs the single base-branch default.
- AGENTS.md:
  - Tests that touch git run in `git_repo` or `tmp_path` via `monkeypatch.chdir`.
  - Never clear `os.environ`; the root `isolated_home` fixture owns `HOME`.
- Each task is one green commit. `scripts/preflight.sh` runs ruff and mypy `--strict`.

## Tests That Change

| File | Change |
|---|---|
| `tests/unit/models/test_config*.py` | `GitConfig` default is `"main"`, and `None`/`""` map to `"main"` |
| `tests/unit/core/test_run_lifecycle.py` | `TestFetchBaseBranch` and `TestCreateWorktreeForRunFetch`: `staging` → `main`. `TestFinalizeSuccess`: the auto-close warning test; the comment test asserts `pr_url` |
| `tests/dashboard/test_settings_indicators.py` | `test_git_badge_count_matches_changed`: `"main"` → `"develop"` |
| `tests/unit/cli/wizard/test_task_manager.py` | drop the `auto_close` prompt cases, including `test_enabled_with_auto_close` |
| `tests/unit/config/test_yaml_generator.py` | no `auto_close` line; `base_branch` comment |
| `tests/unit/task_managers/test_closer.py`, `test_github_client.py` | deleted |
| `tests/unit/task_managers/test_base.py`, `test_null.py`, `test_linear.py` | drop the `is_pr_merged` cases (`TestLinearTaskManagerIsPrMerged`, the `hasattr` check) |
| `tests/conftest.py` | new `fake_gh` fixture |
| `tests/unit/core/test_pr.py` (new) | `create_pr` behaviour and error mapping |
| `tests/unit/core/test_orchestrator.py` | `TestPRCreationAfterDocumentPhase` drives the real `DocumentExtension` with `fake_gh`; drop the `AutoPRResult` patches |
| `tests/unit/cli/test_progress.py` | `TestPipelineSummaryWithPRResult` → `pr_url`/`pr_error`; delete `TestTryAutoCreatePr` |
| `tests/unit/cli/test_pr.py` | `TestPrCommand` uses `fake_gh`; delete the preflight, `AutoPRResult`, `auto_create_pr`, `_store_pr_url` and `--no-open` tests; move the title and description tests to core |

## Useful Commands

```bash
# Partial runs (no coverage gate)
uv run pytest tests/unit/core/test_pr.py tests/unit/cli/test_pr.py -o addopts=""
uv run pytest tests/unit/core/test_orchestrator.py -k PRCreation -o addopts=""
uv run pytest tests/unit/core/test_run_lifecycle.py -k "FinalizeSuccess or FetchBaseBranch" -o addopts=""

# Phase greps
grep -rn "pr_result\|IssueCloser\|GitHubClient\|is_pr_merged" src
grep -rn "AutoPRResult\|_PRResultFromContext\|can_auto_create_pr\|check_git_remote\|check_gh_authenticated\|try_auto_create_pr\|no_open\|task_uuid" src
grep -rn "staging" src/adw        # only hooks/git_commit.py (git index)

# What gh prints when the PR already exists (stderr, exit 1)
#   a pull request for branch "feature/x" into branch "main" already exists:
#   https://github.com/<owner>/<repo>/pull/<n>
```

## Uncertainty

- **Whether a plain mocked `adw run` in a scratch repo leaves a pushable branch with a commit.** It matters for the real-repo evidence. Resolution: TASK-006 seeds a valid `pr_description.md` and adds one commit on `context.branch_name` by hand if the mocked build produced none, before running the real `adw pr`.
- **The exact wording of `gh`'s "already exists" message across `gh` versions.** Resolution: the parse needs only `already exists` plus a `/pull/<n>` URL, and falls back to `GH_PR_FAILED` otherwise.

## References

- Epic 01, phase 1.7: `docs/artifacts/epics/01-cleanup-safety-dead-code-bugs.md`
- Epic 04, phase 4.4, which consumes `create_pr` and the base default: `docs/artifacts/epics/04-plan-driven-runs.md`
- Epic 06, phase 6.2, which owns the Linear status spine: `docs/artifacts/epics/06-autonomous-landing-linear-flow.md`
- `docs/architecture/deep-dive/document-phase.md` and `extensions-system.md`: the docs this plan updates
- ADR-001, the test policy: `docs/architecture/adrs/ADR-001-test-reduction-strategy.md`
