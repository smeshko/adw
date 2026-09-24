# Research: One home for git, formatting, paths and run status

Curated findings only — no raw conversation transcripts.

Line numbers refer to `d9ba2f79`. #212 (phase 2.3) merged into this branch during validation (`7b61e72a`). It deleted `src/adw/webhook/` and `src/adw/server/`, and moved these lines: `dashboard/server.py` templates to `:78` (`create_dashboard_app`, now a plain `FastAPI()`); `wizard/summary.py` `atomic_write_config` to `:289`; `cli/app.py` by −1; `live_stream.py` by −1.

## Key Files & Directories

### Git
- `src/adw/hooks/git_commit.py` (476 lines): `get_current_branch`, `validate_branch_matches`, `format_commit_message`, `stage_changes`, `has_staged_changes` (reads rc 0/1), `get_unstaged_modifications`, `create_commit` (retries up to `MAX_HOOK_RETRIES=3` when a pre-commit hook modifies files, then amends). Imported by `core/phase_runner.py:22` and `hooks/git_branch.py:19`.
- `src/adw/hooks/git_branch.py`: `sanitize_branch_name`, `check_uncommitted_changes`, `create_or_switch_branch`, `ensure_on_branch`. Imported by `core/run_lifecycle.py:31`.
- `src/adw/hooks/git_diff.py` (331 lines): `has_commits`, `capture_diff`, `capture_staged_diff`, plus the pure parsers `count_binary_files`, `truncate_diff` and `get_diff_stats`. Imported by `core/extensions/build.py:12`.
- `src/adw/worktree/branch.py`: `WorktreeBranchManager`. Its methods are `get_branch_name` (`adw/<run_id>`), `branch_exists`, `has_unpushed_commits`, `delete_branch(run_id, force, *, branch_name)` and `check_pr_exists` (`gh pr view`). `worktree/manager.py:83` wraps it, exposed as the `branch_manager` property. `cli/cleanup.py:135` uses the property.
- Other direct callers:
  - `worktree/manager.py`: 4 calls (`worktree add` / `remove`, `status`, `branch -D`)
  - `core/run_lifecycle.py:580`: `git fetch`
  - `core/pr.py`: `:170` `gh pr create`, 60 s; `:214` `git push`, 120 s
  - `core/extensions/build.py:181`: `git diff --stat`
  - `core/extensions/ship.py:192,198`: `checkout` and `pull`, `check=True`, bytes output
  - `cli/wizard/git.py:136`: `rev-parse`, 5 s
- `src/adw/core/run_trigger.py:103`: `Popen` of the `adw` CLI, not git. It keeps its own `import subprocess`.
- `hooks/runner.py` (asyncio, hook scripts) and `executors/claude_code.py` don't import `subprocess`.

### Formatting and status styles
- **Duration formatters:**
  - `cli/global_commands.py:86` (datetime pair) and `:445` (ms)
  - `cli/list.py:395` (seconds)
  - `dashboard/routes.py:485` (seconds)
  - `cli/status_display.py:167` (`RunContext`)
  - `task_managers/comments.py:23` (seconds; clamps negatives)
  - `dashboard/partials.py:101` (ms) and `:634` (timedelta)
  - `cli/progress.py:189` (ms or `None`)
  - inline in `logging/live_stream.py:236`
- **Tokens:** `cli/global_commands.py:402` (`340.0K`), `cli/progress.py:204` and `dashboard/partials.py:111` (`340K`, `2M`).
- **Relative time:**
  - `cli/global_commands.py:116` (`just now` under 60 s)
  - `cli/projects.py:139` (ISO string, has months)
  - `dashboard/partials.py:45` and its exact copy at `dashboard/routes.py:56` (`30s ago`)
- **Cost:**
  - `cli/global_commands.py:425` (the only one with `,` separators)
  - inline in `partials.py` (6 sites plus a `"$0.00"` literal) and `routes.py` (2 sites, `—` for zero)
  - templates `project_breakdown.html:26` and `analytics.html:215`
  - `stats_row.html:61-62` prepends `$` to a number from Python
- **Size:** `cli/dry_run.py:278` and `dashboard/routes.py:774` are identical. `cli/logs.py:784` is always KB.
- **CLI status→colour maps:**
  - `global_commands.py:67`
  - `list.py:249`
  - `list_display.py:30`
  - `status_display.py:40`
  - `progress.py:308` (if/elif)
  - `progress.py:68` `STATUS_ICONS`, which nothing in `src` reads
- **Dashboard badge:** `templates/components/status_badge.html` has its own 5-entry map; unknown falls back to `aborted`.
- **Jinja:** `dashboard/server.py:82` creates `Jinja2Templates` and registers no filters or globals. `tests/unit/dashboard/test_stat_cards.py:626` renders the badge macro through a bare `jinja2.Environment`.

### Run status
- `models/context.py:60` `RunContext.status` and `models/index.py:55` `IndexEntry.status` are both `Literal["running","completed","failed","interrupted","aborted"]`.
- `core/constants.py:33` `TERMINAL_STATUSES: frozenset[str]`.
- `cli/list.py:26` and `cli/global_commands.py:30` hold identical `VALID_STATUSES` copies.
- `core/run_lookup.py:98` has the incomplete set; `dashboard/routes.py:458,630,670` have `("failed","aborted")`.
- `PHASE_SEQUENCE` is at `core/constants.py:16`. The hand-written lists left are `cli/wizard/phases.py:16` `AVAILABLE_PHASES` and `dashboard/partials.py:343` `canonical_phases`. `cli/app.py:178`'s `--phase` help lists 4 phases.

### Atomic writes
- `core/context_manager.py:58-112`: `.context.json.tmp` + fsync + `Path.rename`, inside a `FileLock`.
- `core/snapshot_manager.py:188-209` and `core/artifact_manager.py:45-92`: the same pattern, without a lock.
- `cli/wizard/summary.py:304-370` `atomic_write_config`: in-place `write_text` for each file, with backup and restore on `OSError`.
- Written in place:
  - `core/run_directory.py:106` (first `context.json`; its comment says "atomically")
  - `core/index_manager.py:402` `_write_all_entries`
  - `core/project_registry.py:284` `_save_registry`

### Runs directory
- `core/constants.py:38` `project_runs_dir(root)` (from 1.8; no `mkdir`).
- `cli/bootstrap.py:64` `get_runs_dir` calls `mkdir`. Callers:
  - `create_orchestrator:205`
  - `resume:36`
  - `abort:39`
  - `status:86`
  - `pr:150`
  - `cleanup:58,226`
- `cli/logs.py:216` `_get_runs_dir` exits 1 without `.adw`. `cli/list.py:297` `_get_runs_dir` returns `None` without `.adw/runs`.
- 13 hand-built `".adw" / "runs"` paths:
  - `cli/app.py:243,350,369`
  - `cli/global_commands.py:727`
  - `core/run_directory.py:62`
  - `core/stats_aggregator.py:243,291,341,489`
  - `core/extensions/ship.py:151`
  - `config/initializer.py:116`
  - `worktree/manager.py:184,238,239`

## Architecture Facts

- **Only 3 of 31 git/gh calls set a timeout.** The network calls without one are `git fetch` (`run_lifecycle.py:580`), `git pull` (`ship.py:198`) and `gh pr view` (`worktree/branch.py:171`).
- **The epic's acceptance grep is vacuous.** `subprocess\.(run|Popen)\(\s*\[\s*"(git|gh)"` matches 0 lines today: 24 calls put `["git", …]` on the next line, and 7 pass `cmd` / `commit_cmd` / `stat_cmd`. `rg -U` (multi-line) and the `import subprocess` file list are the real checks.
- **`WorktreeBranchManager.delete_branch(force=False)` never runs.** `manager.py:643` and `cleanup.py:138` both pass `force=True`, so `has_unpushed_commits` and the `git branch -d` path are dead.
- **Patches of `subprocess.run` stop intercepting git code.** `adw.git._run` uses `Popen`, so neither a global `patch("subprocess.run")` nor a module-scoped one such as `adw.core.run_lifecycle.subprocess.run` catches its calls. Tests patch the `git` / `gh` seam instead: `adw.git.git` for the helpers, `<consumer>.git` for call sites.
- **Behaviour of a `StrEnum` field (pydantic 2.12, Python 3.13), checked in memory:**
  - `model_dump_json()` writes the value, so `context.json` and `index.jsonl` are unchanged.
  - `model_validate_json` turns strings into members.
  - `str(member)` is the value.
  - `model_copy(update={"status": "failed"})` skips validation and leaves a `str` in the field, and serialisation then warns (`PydanticSerializationUnexpectedValue`). Every write must use a member.
- **Status writes via `model_copy` or `update_run`:**
  - `interruption.py:163-277`
  - `run_lifecycle.py:314-517`
  - `orchestrator.py:404-646`
  - `resume_manager.py:296`
  - `global_commands.py:859`
  - `mutations.py:290`
- **Run detail's elapsed time changes format live.** It first renders with `routes._format_duration_from_seconds` (`1h 2m`), then the SSE stream (`routes.py:1424`) swaps in `partials._format_elapsed` (`62m 5s`).
- **`analytics.html:132` reads `bar.total_tokens`,** but the context key is `tokens` (`partials.py:318`), so the tooltip always shows 0.
- **`adw status` outside a project creates `./.adw/runs`,** prints "No runs found" and exits 0. With a run id it exits 1 with `RUN_NOT_FOUND`, still after the `mkdir`. `adw list` and `adw logs` create nothing.
- **`RunLookup._list_runs` returns `[]` when the runs directory is missing** (`run_lookup.py:114`).

## Constraints

- mypy `--strict` and ruff gate CI (`scripts/preflight.sh`).
- ADR-001: no enum-existence, import-smoke or markup-substring tests. The formatter tests are parametrized behaviour tables.
- Tests that touch git run in `git_repo` / `tmp_path`. The fake sleeping `git` goes first on `PATH` via `monkeypatch.setenv`, and never replaces PATH.
- Phase 1.8 named the path helper `project_runs_dir` so that a local `runs_dir` can't shadow it (`UnboundLocalError`).
- #212 (phase 2.3), merged, rewrote `dashboard/server.py` (`create_dashboard_app` builds a plain `FastAPI()`) and deleted the wizard's webhook step.

## Useful Commands

```bash
rg -U 'subprocess\.(run|Popen)\(\s*\[\s*"(git|gh)"' src   # multi-line argv literals
rg -l 'import subprocess' src                              # which modules still shell out
rg -n 'def _?(format_(duration|elapsed|tokens|cost|size|file_size|relative_time|duration_ms|duration_from_seconds)|relative_time)\b' src
rg -n '/ "runs"' src                                       # hand-built runs paths
uv run pytest tests/unit/git -o addopts="" --durations=5
```

## Uncertainty

- **Whether 60 s is long enough for every default-timeout call.** Resolved in validation rounds 1 and 2: no, 60 s only suits local plumbing. The other tiers:
  - network commands (fetch, `gh pr view`): 300 s
  - `worktree remove` and `add -A`: 300 s
  - hook-running commands (commit, amend, checkout, pull, push, `worktree add`): 600 s
  - `gh pr create` keeps 60 s and the wizard's `rev-parse` keeps 5 s
- **What a timeout does to git.** `subprocess.run(timeout=)` sends SIGKILL at once, which leaves `.git/index.lock` behind. Resolved:
  - Round 1 chose SIGTERM to a new session's process group.
  - Round 2 showed that a new session keeps the terminal's Ctrl+C from reaching git and takes away its `/dev/tty` prompts.
  - Final design: git stays in the terminal's group, gets SIGTERM, then SIGKILL after 5 s, and after that `_run` only calls `wait()`.
- **Mode of files written through a temp file.** `mkstemp` creates 0600, which `os.replace` keeps. Resolved: create the temp file with `os.open(..., 0o666)` (the umask applies), and `fchmod` it to the target's mode when replacing.
- **Whether moving all dashboard formatting into templates is required by "registers the formatters as Jinja filters".** Resolved: no. Filters are registered and used wherever a template formats a number itself. Context builders call `adw.format` directly. Phase 2.11 reworks those builders.
- **Whether `resume` reaches the runs-dir guard before loading config outside a project.** Resolved: yes. `resume.py:77` calls `_create_resume_manager`, which calls the helper at `:36` first.

## References

- Epic 02, phase 2.7: `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`
- Phase 1.8 plan (runs path helper): `docs/artifacts/plans/archive/2026-09-23-01.8-fix-path-config-default-drift/PLAN.md`
- ADR-001: `docs/architecture/adrs/ADR-001-test-reduction-strategy.md`
- `docs/architecture/deep-dive/build-phase.md` (names the git helper modules)
