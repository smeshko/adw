# Plan: One home for git, formatting, paths and run status

Status: in-progress
Branch: feature/adw-23
Risk: large
Epic: 02 — Cleanup: remove inert features and consolidate ([epic](../../epics/02-cleanup-remove-and-consolidate.md))
Phase: 2.7 — One home for git, formatting, paths and run status
Linear: ADW-23
Created: 2026-09-24

## Goal

After this phase, each shared primitive has exactly one implementation:

- **Git and gh.** Every `git` and `gh` subprocess goes through `adw.git`, and every call has a timeout. A hung `git fetch` or `git pull` raises `GIT_TIMEOUT` instead of blocking the run forever.
- **Formatting.** Durations, token counts, relative times, costs and file sizes are formatted by one function each in `adw.format`. The CLI, Linear comments, `live.log` and the dashboard print the same value the same way.
- **Status style.** Run status is a `RunStatus` StrEnum. One status→style map colours it in `adw list`, `adw status`, the end-of-run summary and the dashboard badge.
- **Atomic writes.** One `atomic_write(path, data)` writes every run-state and user-state file.
- **Runs directory.** One function builds the `.adw/runs` path, and only `adw run` creates the directory. `adw status` and the other read-only commands stop leaving `.adw/runs` behind in whatever directory they run from.

## Scope

- **`adw.git` runner (TASK-001).**
  - `git(*args, cwd=None, check=False, timeout=60)` and `gh(...)` run the tool through `Popen` and capture its output as text.
  - On a timeout they send SIGTERM to git, then SIGKILL after 5 s, and raise a recoverable `ADWError`: `GIT_TIMEOUT` or `GH_TIMEOUT`. An interrupt stops git the same way before it propagates.
  - Otherwise they behave like `subprocess.run`: `check=True` raises `CalledProcessError`, and a missing binary raises `FileNotFoundError`.
- **Helpers move into `adw.git` (TASK-002).**
  - The helpers in `hooks/git_branch.py`, `hooks/git_commit.py` and `hooks/git_diff.py` move into `adw.git` and run through `git()`. Their names and `working_dir` keyword stay the same.
  - `worktree/branch.py`'s `WorktreeBranchManager` becomes three functions: `branch_exists`, `delete_branch` and `pr_exists`. Its dead `has_unpushed_commits` / `force=False` path goes.
  - All four modules are deleted, and their tests move to `tests/unit/git/`.
- **Remaining call sites (TASK-003).**
  - These modules switch to `git()` / `gh()`: `worktree/manager.py`, `core/run_lifecycle.py`, `core/pr.py`, `core/extensions/build.py`, `core/extensions/ship.py` and `cli/wizard/git.py`.
  - Afterwards only `adw/git.py` and `core/run_trigger.py` import `subprocess`. `run_trigger.py` launches `adw` itself.
- **`RunStatus` (TASK-004).**
  - A `RunStatus(StrEnum)` in `models/context.py` types `RunContext.status` and `IndexEntry.status`.
  - Every status write, comparison and status set in `src` uses its members. That covers `TERMINAL_STATUSES`, the two `VALID_STATUSES` copies, `run_lookup`'s incomplete set and the dashboard's `("failed", "aborted")` tuples.
  - `PHASE_SEQUENCE` replaces the stale `--phase` help text and the two hand-written phase lists still left: `wizard/phases.py`'s `AVAILABLE_PHASES` and `dashboard/partials.py`'s `canonical_phases`.
- **`adw.format` (TASK-005).**
  - `format_duration`, `format_tokens`, `format_relative_time`, `format_cost` and `format_size` replace:
    - 9 duration formatters
    - 3 token formatters
    - 4 relative-time formatters
    - the cost function and 11 inline `${x:.2f}` sites
    - 2 size formatters and one inline
  - The dashboard builds its templates in one `build_templates()`, which registers the five as Jinja filters. The templates that format numbers themselves use the filters.
- **Status style map (TASK-006).**
  - `STATUS_STYLES` / `status_style()` in `adw.format` hold a Rich colour, an icon and badge classes per `RunStatus`.
  - They replace the 5 CLI maps (`global_commands`, `list`, `list_display`, `status_display`, `progress`), the unread `STATUS_ICONS` and the badge macro's own map.
  - The runs filter bar lists its options from `RunStatus`.
- **`atomic_write` (TASK-007).** `adw.fs.atomic_write(path, data)` writes a temp file in the same directory, fsyncs it and `os.replace`s it over the target. Its callers:
  - `ContextManager.save`
  - `SnapshotManager._create_snapshot`
  - `ArtifactManager.store`
  - `RunDirectoryManager.create`
  - the wizard's `atomic_write_config`
  - `IndexManager._write_all_entries`
  - `ProjectRegistry._save_registry`
- **Runs directory (TASK-008).**
  - `core.constants.project_runs_dir` replaces the 13 hand-built `".adw" / "runs"` paths.
  - A CLI guard, `bootstrap.require_runs_dir()`, replaces `bootstrap.get_runs_dir`, `logs._get_runs_dir` and `list._get_runs_dir`. When the project has no `.adw`, it exits 1 with "No .adw directory found". It never creates anything.
  - `create_orchestrator` is the one place that creates `.adw/runs`.
  - `AGENTS.md` gains one architecture note that names the shared primitives.
- **Docs.** Each is updated in the task that moves the helper it names:
  - `docs/architecture/deep-dive/build-phase.md`
  - epic 04's phase that names `hooks/git_branch.py`
  - seven feature docs that name private formatters
  - the `hooks/__init__.py` and `progress.py` docstrings

## Out of Scope

- **Phase-level status.** `PhaseStatus` stays as it is. So do the dashboard's phase-pipeline vocabulary (`completed` / `active` / `failed` / `pending`) and its classes. Phase 2.11 moves the pipeline builders and replaces the HTML built in Python.
- **Exact counts formatted with `{:,}`,** such as `15,000` in Linear comments, `live.log`, `status_display` and `phase_detail.html`. `{:,}` is Python's number format, not a duplicate formatter, and those places want exact counts (see Decisions).
- **Percentages and absolute timestamps.** The epic doesn't list them. Most of them live in `*_display.py`, which phase 2.12 folds.
- **Status strings outside run status:**
  - Linear label names (`adw:running`)
  - `state_mapping` config keys
  - template comparisons such as `run.status == 'completed'`, since a StrEnum compares equal to its value
- **The hook shell scripts' `git` / `gh` calls** (`ship/post.sh` and others). They run under the hook runner's own timeout, not through Python.
- **Other plain writes:** the stats cache (regenerable), LLM response dumps, lock files, and `.gitignore` and manifest files. Fsyncing the parent directory after a rename is also out.
- **`adw init`.** It keeps creating `.adw/runs` in minimal mode. It writes the project, so it isn't a read-only command.
- **Renaming the moved helpers** or their `working_dir` keyword. The move is only a move.
- **Disabling git's credential prompts (`GIT_TERMINAL_PROMPT=0`).** git keeps its terminal (see Decisions), so a user at a terminal can still answer a prompt. The timeout suggestion names credentials and ssh-agent, so a prompt that stalls git is diagnosable. This was deferred in validation round 1 (#6) and filed as a follow-up.
- **Lost updates between concurrent runs.** `IndexManager.update_run` does an unlocked read-modify-write. `atomic_write` prevents torn files, but two runs can still overwrite each other's update (pre-existing; round 1 #19).
- **Finding the project root from a subdirectory.** Every command uses the cwd as the project root. From a subdirectory, `require_runs_dir` says "run adw init" like the other commands do today (pre-existing; round 1 #19).
- **Symlinked, hard-linked or bind-mounted state files.** Like any rename-based write, `atomic_write` replaces a symlinked target with a regular file and breaks hard links. It doesn't keep a file owned by another user, and it fails on a single-file bind mount.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). In short:

- **Git.**
  - 31 `subprocess.run` calls in 10 files: 29 git, 2 gh.
  - Only 3 set a timeout: `gh pr create` 60 s, `git push` 120 s and the wizard's `rev-parse` 5 s.
  - `git fetch` (`run_lifecycle.py:580`), `git pull` (`ship.py:198`) and `gh pr view` (`worktree/branch.py:171`) can hang.
  - The epic's grep `subprocess\.(run|Popen)\(\s*\[\s*"(git|gh)"` matches nothing even today: every call is split across lines or builds its argv in a variable. The acceptance checks below use `rg -U` and the `import subprocess` list instead.
- **Formatting.**
  - 9 duration formatters in 3 styles (`1h 2m`, `62m 5s`, `13m44s` / `45.2s`), plus `live.log`'s `62.0s`.
  - 3 token formatters that disagree (`340.0K` vs `340K`).
  - 4 relative-time formatters (`just now` vs `30s ago`; one also has months).
  - Cost: one function and 11 inline `${x:.2f}` sites. Only the function uses thousands separators.
  - 2 identical size formatters.
  - Run detail renders `#run-elapsed` as `1h 2m`, then the SSE stream replaces it with `62m 5s`.
  - `analytics.html:132` reads a `total_tokens` key that doesn't exist, so its tooltip always shows 0.
  - The dashboard registers no Jinja filters.
- **Status maps.** 5 CLI maps disagree: `running` is blue, yellow or red, and `aborted` is magenta, bright_black, red or dark_orange. `adw list` and `adw status` differ on `aborted`. The dashboard badge macro has a sixth map.
- **Run status.**
  - `RunContext` and `IndexEntry` type it as a `Literal[...]`, and the same 5 values are hand-written in about 20 modules.
  - `model_copy(update={"status": "..."})` skips validation. After the switch, a plain string in a `RunStatus` field makes pydantic warn at serialisation, so every write has to use a member.
  - Serialised JSON stays the same: `"running"` either way.
- **Phase lists.** `PHASE_SEQUENCE` already exists in `core/constants.py`. Phase 2.5 deleted 2 of the epic's 4 hand-written lists, so 2 are left.
- **Atomic writes.**
  - There are 3 temp-then-rename copies (context, snapshot, artifact). Each uses a fixed temp name, `Path.rename` and the locale encoding.
  - The wizard writes its files in place and rolls back on failure.
  - `RunDirectoryManager.create` says it writes "atomically", but it calls `write_text`.
  - `IndexManager._write_all_entries` and `ProjectRegistry._save_registry` truncate and rewrite user-global state in place.
- **Runs directory.**
  - Phase 1.8 added `project_runs_dir(root)`. It doesn't create the directory, and its name keeps a local `runs_dir` from shadowing it.
  - `bootstrap.get_runs_dir()` calls `mkdir`. So `adw status`, `abort`, `resume`, `pr` and `cleanup` create `./.adw/runs` wherever they run.
  - Outside a project, `adw status` then prints "No runs found" and exits 0.
- **Baseline.** `uv run pytest` on `7b61e72a` (after #212 merged into this branch): 2982 passed, 5 skipped, coverage 84.79%, no warnings. On `d9ba2f79` it was 3189 passed.

## Decisions

- **`git()` raises `ADWError` on a timeout; otherwise it behaves like `subprocess.run`.**
  - Callers keep their `returncode`, `CalledProcessError` and `FileNotFoundError` handling unchanged.
  - A timeout raises a code the callers and the CLI already render: `GIT_TIMEOUT` (recoverable), or `GH_TIMEOUT`, which `core/pr.py` raises today.
  - There's no new exception class, since phase 1.3 just trimmed the hierarchy.
- **Timeouts come in tiers (revised in validation round 1, #5):**
  - `DEFAULT_TIMEOUT` = 60 s, for local plumbing.
  - `NETWORK_TIMEOUT` = 300 s, for `git fetch` and `gh pr view`.
  - `CHECKOUT_TIMEOUT` = 300 s, for `worktree remove` and `git add -A` (LFS filters, large trees).
  - `HOOK_TIMEOUT` = 600 s, for commands that run git hooks: `commit`, `commit --amend`, `checkout`, `pull`, `push` and `worktree add`. Round 2 (#8) moved `push` and `worktree add` up: they run pre-push and post-checkout hooks.
  - `gh pr create` keeps its 60 s, and the wizard's `rev-parse` keeps its 5 s. `push` moves from 120 s to the hook tier.

  A timeout only has to beat "forever". Killing a hook-running command early would fail real runs, and there is no environment override.
- **A timeout, or any exception inside `_run`, stops git with SIGTERM first and SIGKILL after 5 s.**
  - `subprocess.run(timeout=)` sends SIGKILL at once. That leaves `.git/index.lock` behind, because git removes its lockfiles on SIGTERM but not on SIGKILL (round 1, #4).
  - After SIGKILL, `_run` only `wait()`s. It never reads the pipes, so a descendant that inherited them can't block it (round 2, #3).
- **git stays in the terminal's process group. There is no new session and no group kill (round 2, #1 and #2).** Round 1 proposed both, to take hook grandchildren down with git, but they would:
  - keep the terminal's Ctrl+C from reaching git, so git would never remove its locks
  - take away git's `/dev/tty`, so every credential and SSH prompt would fail

  With git left in the group, Ctrl+C and prompts behave as they do today. The cost is that a hook grandchild can outlive a timed-out git (see Risks).
- **Tests patch the `git` / `gh` seam, not `subprocess.run`.** Because `_run` uses `Popen`, a `patch("subprocess.run")` would intercept nothing and let a test run real git. TASK-002 and TASK-003 move every such patch to `adw.git.git` or the consumer's `git` name.
- **The timeout message names the tool and up to two leading non-option arguments** (`` `git fetch origin` ``, `` `gh pr create` timed out after 60s ``). `gh pr create`'s title and body come after flags, so they never reach the message. The git suggestion names credentials, ssh-agent and a stale `index.lock`.
- **Moved helpers keep their names and `working_dir` keyword.** Consumers import them by name (`from adw.git import create_commit`). The dozens of `patch("adw.core.phase_runner.create_commit")` targets keep working, and the diff stays a move.
- **Where a new name would shadow an existing one, the import is aliased or the local is renamed (round 1, #1):**
  - `delete_branch` is a bool parameter in `remove_worktree` and `cleanup_command`, so it is imported there as `delete_local_branch`.
  - `manager.py`'s local `pr_exists` becomes `has_pr`.
  - The `status_style` locals in `list.py` and `global_commands.py` become `color`.
- **`WorktreeBranchManager` becomes functions, and the unpushed-commits branch goes.**
  - Every caller passes `force=True`, so `has_unpushed_commits` and the `-d` path never run.
  - `delete_branch(name, *, working_dir)` force-deletes. It returns `True` when the branch is gone and `False` when git refuses.
  - `WorktreeManager.get_branch_name` keeps the `adw/<run_id>` naming.
- **One `adw/git.py` module, not a package,** because that's what the epic names. The pure diff parsers (`truncate_diff`, `get_diff_stats`, `count_binary_files`) move with the diff helpers, since they only parse git output.
- **Canonical formats:**
  - **Duration:** `45s` / `5m 32s` / `1h 2m`.
    - It's the most common style, the only one with an hours tier, and what run detail renders first.
    - It takes seconds, clamps negatives to 0, and shows `—` for `None`.
  - **Tokens:** `999` / `1.2K` / `340K` / `1.2M` / `2M`.
    - This is the style the dashboard and `progress.py` use.
    - The unit is picked after rounding, so 9,999 is `10K` rather than `10.0K`, and 999,999 is `1M` rather than `1000K`.
  - **Relative time:** `—` / `just now` (future) / `30s ago` / `5m ago` / `2h ago` / `3d ago`.
    - This is the dashboard's style.
    - The CLI's `just now` for anything under a minute becomes `Ns ago`, and `projects.py`'s months unit goes.
  - **Cost:** `$1,234.56`, negative `-$1.00`. Call sites that show `—` for zero keep making that choice themselves.
  - **Size:** `512 B` / `1.5 KB` / `2.3 MB` / `1.1 GB`, base 1024.
- **`{:,}` exact counts stay.** Linear comments and `live.log` show `15,000 tokens` on purpose, and a compact `15K` would lose information there. A format spec isn't a second formatter.
- **Canonical status style:**
  - Colours are the ones `adw list` uses today: running yellow, completed green, failed red, interrupted orange1, aborted bright_black. `bright_black` for aborted matches the dashboard's muted `badge-ghost`.
  - Icons and classes come from the dashboard badge.
  - Unknown statuses get white, `?` and `badge-ghost`.
  - The CLI stays colour-only and gains no icons. The dashboard badge keeps its current look.
- **The dashboard builds its templates in `build_templates()` in `dashboard/server.py`.**
  - It registers the filters (`duration`, `tokens`, `relative_time`, `cost`, `filesize`) and the globals (`status_style`, `run_statuses`).
  - The app and the badge test both use it, so a test can't render a macro without the helpers the app has.
  - Context builders keep passing preformatted strings, calling `adw.format` directly. Templates that format numbers themselves switch to the filters.
  - Moving all formatting into templates would rewrite most context-builder tests for no change in behaviour, and phase 2.11 reworks those builders anyway.
- **`RunStatus` lives in `models/context.py`; `TERMINAL_STATUSES` stays in `core/constants.py` as a `frozenset[RunStatus]`.** No module under `adw.models` imports `adw.core`, so there is no import cycle.
- **Every run-status literal in `src` Python becomes a member, comparisons included.** A member catches typos that a string literal can't, and one grep checks the whole rule. Round 1 #11 proposed covering only writes and sets, and was rejected.
- **`IndexManager.update_run` validates its updates** with `model_validate({**entry.model_dump(), **updates})`. It is the one write path that takes `**Any`, which mypy can't check. A plain string from any caller becomes a member, and an invalid value raises instead of being written (round 1, #2).
- **`atomic_write` lives in a new `adw/fs.py`.**
  - Its callers are spread across `core`, `cli/wizard` and `core/index_manager`, so it goes in a top-level module next to `adw.git` and `adw.format`.
  - Each temp file gets a unique name (`.<name>.<random>.tmp`), created with `os.open(..., O_EXCL, 0o666)`, so two writers can't clobber each other's temp.
  - A new file gets the umask default (0644). A replaced file keeps its mode through `fchmod`. `NamedTemporaryFile` / `mkstemp` would silently turn state files into 0600 (round 1, #7).
  - `str` data is written as UTF-8.
  - Callers keep their own error codes (`CONTEXT_WRITE_FAILED` and so on).
- **The wizard keeps its multi-file rollback.** `atomic_write_config` still backs up and restores the whole set of files, but writes each one with `atomic_write`. The epic asks for the wizard summary to use the helper, and a crash then can't leave a half-written `project.yaml`.
- **`IndexManager._write_all_entries` and `ProjectRegistry._save_registry` also use `atomic_write`.** They rewrite the whole of `~/.adw/index.jsonl` and `~/.adw/projects.yaml` in place. A crash mid-write would lose every run's index entry or every registered project. The stats cache is regenerable and stays as it is.
- **`require_runs_dir()` checks for `.adw`, not `.adw/runs`.**
  - `adw init --wizard` creates `.adw` without `runs`. In an initialised project with no runs yet, `adw status` should still say "No runs found", not "run adw init".
  - The guard prints the message `adw logs` prints today and raises `typer.Exit(1)`.
  - It doesn't raise a `ConfigError`, because not every command renders one. Phase 2.12 unifies error handling.
- **The helper keeps the name `project_runs_dir`** rather than the epic's `runs_dir()`. Phase 1.8 chose that name so that a local `runs_dir` can't shadow it and raise `UnboundLocalError`.
- **No interview.** The user asked for an autonomous run and said to use best judgement, so the choices above are recorded here instead of being asked.

## Risks

- **A timeout kills a legitimately slow git command.** Mitigation:
  - The tiers give hook-running commands (push included) 600 s and network or checkout-heavy ones 300 s.
  - Only local plumbing gets the 60 s default.
- **A killed git command leaves state behind.** Mitigation:
  - git gets SIGTERM before SIGKILL, so it removes its lockfiles.
  - `_cleanup_partial_worktree` runs `git worktree prune` after a killed `worktree add`.
  - Residual: a hook's own child process can outlive a timed-out git, because signals go to git's pid, not a process group. It is rare, since it needs a timeout, and it is the price of keeping Ctrl+C and terminal prompts working.
- **Some timeouts don't stop the run.** Mitigation, partial:
  - Fetch, `worktree add`, `worktree remove` and push map a timeout onto their existing failure codes, so those runs fail with a readable panel.
  - Auto-commit and staging still swallow any error as a warning (`phase_runner.py:1190`–`:1227`), a `GIT_TIMEOUT` included. The run continues without that phase's commit, exactly as it does for any commit failure today. The warning names `GIT_TIMEOUT`.
  - Changing auto-commit's error policy is out of scope.
- **A plain status string in a `model_copy` update makes pydantic warn at serialisation.** Mitigation: TASK-004 greps `src` for status literals in writes. The full suite's summary line must stay free of warnings, as it is at baseline. JSON output is unchanged either way.
- **Many tests patch module-level names that move:** `adw.hooks.git_commit.*`, `adw.core.run_lifecycle.subprocess.run`, `adw.cli.status.get_runs_dir` and the private formatters. Some would keep passing while intercepting nothing: `patch("subprocess.run")` once `_run` uses `Popen`, and the `bootstrap.get_runs_dir` patches once `create_orchestrator` calls no helper. Mitigation:
  - Consumers import the moved names into their own namespace, so most consumer-level patch targets keep working.
  - TASK-002 and TASK-003 move every git patch to the `git` / `gh` seam, and check `rg 'patch\("subprocess\.(run|Popen)"' tests`.
  - TASK-008 turns the runs-dir fixtures into `monkeypatch.chdir(tmp_path)`.
  - Each task lists the patch targets it rewrites and runs its partial suite before committing.
- **Output visibly changes:**
  - `65m 30s` → `1h 5m`
  - the progress summary's `45.2s` → `45s`, `13m44s` → `13m 44s` and `N/A` → `—`
  - `45.7K` → `46K`
  - `adw global list`'s `just now` → `30s ago`, and the stats-cache age `5 minutes ago` → `5m ago`
  - `live.log`'s `(62.0s)` → `(1m 2s)`, and a sub-second stream `(0.4s)` → `(0s)`
  - colours change in `adw global list` and `adw list --global` (running, interrupted, aborted) and in the progress summary (interrupted, aborted)
  - the badge's unknown-status fallback `⦻` → `?`
  - `GH_TIMEOUT`'s message and suggestion text
  - `--status` "Valid values:" moves from alphabetical to definition order
  - `adw projects` shows a relative time instead of `unknown` for naive timestamps
  - read-only commands outside a project exit 1 instead of creating `.adw/runs`

  Mitigation: these changes are the point of the phase, and the PR lists them. Nothing parses these strings; the dashboard shows `live.log` lines verbatim.
- **Other phases landing on `staging` while this branch is open.** #212 (phase 2.3) merged during validation and was merged into this branch (`7b61e72a`). The plan's line references reflect it: `server.py:78`, `summary.py:289`, `app.py:177`/`:242`/`:349`/`:368` and `live_stream.py:235`. Mitigation: fetch and rebase before the PR and again before the merge.
- **Tests that use a fake `git` could leave processes behind or hang.** Mitigation:
  - The fakes use `exec sleep`, or their TERM trap kills their own background job.
  - `_run` only `wait()`s after signalling, so an inherited pipe can't hang a test.
  - Every fake-git test passes `cwd=tmp_path`.

## Acceptance Criteria

- [ ] **Every `git` and `gh` subprocess goes through `adw.git`:**
  - `rg -U 'subprocess\.(run|Popen)\(\s*\[\s*"(git|gh)"' src` prints nothing.
  - `rg -l 'import subprocess' src` lists only `src/adw/git.py` and `src/adw/core/run_trigger.py`.
  - `hooks/git_branch.py`, `hooks/git_commit.py`, `hooks/git_diff.py` and `worktree/branch.py` are gone.

  Evidence: the command output.
- [ ] **A timed-out git command raises instead of hanging, and cleans up after itself.** A `git fetch` through the helper, run against a fake `git` that sleeps 30 s, raises `GIT_TIMEOUT` in under 5 s. git gets SIGTERM first and SIGKILL only after the grace period, on a timeout and on an interrupt. Evidence: `test_git_fetch_times_out_against_a_sleeping_git` RED then GREEN with its duration, plus `test_timeout_sends_sigterm_first`, `test_escalates_to_sigkill_only_after_the_grace_period` (both triggers, elapsed ≥ timeout + grace) and `test_interrupt_stops_git_and_propagates`.
- [ ] **Each formatter and the status-style map is defined exactly once:**
  - `rg -n 'def _?(format_(duration|elapsed|tokens|cost|size|file_size|relative_time|duration_ms|duration_from_seconds)|relative_time)\b' src` lists only the five `adw.format` functions.
  - `rg -n 'STATUS_COLORS|STATUS_ICONS|_get_status_style' src` prints nothing.
  - `rg -n ':,?\.2f\}' src` prints only `format_cost` in `src/adw/format.py`.
  - The badge macro holds no status map.

  Evidence: the greps, and the list of formatters in the PR.
- [ ] **`adw list` and `adw status` colour every status identically,** and the dashboard badge takes its icon and classes from the same map. Evidence: `test_list_and_status_colour_each_status_alike`, plus ANSI transcripts of `adw list` and `adw status <id>` from a scratch project with one run per status.
- [ ] **Run status is a `RunStatus` everywhere in `src`:**
  - `RunContext.status` and `IndexEntry.status` are `RunStatus`.
  - Both greps in TASK-004's Acceptance print nothing. They cover writes, `==`/`!=` comparisons, and hand-written tuples and sets. The phase-pipeline `phase_status` strings are excluded.
  - `IndexManager.update_run` validates, so a string status given to it is stored as a member.
  - The full suite reports no warnings.
  - A `context.json` written today loads, and re-serialises with the same `"status"` string.

  Evidence: the grep, the suite tail and `test_context_json_status_round_trips`.
- [ ] **One helper writes state files atomically.** A write that fails partway leaves the old file intact and no temp file behind. A replaced file keeps its mode, and a new file gets the umask default. `rg -n 'os\.fsync|\.tmp"|\.rename\(' src` finds only `adw/fs.py`. Evidence: `tests/unit/test_fs.py`, RED then GREEN, and the grep.
- [ ] **Paths, writes and lists each have one source.**
  - `rg -n '/ "runs"' src` prints only `src/adw/core/constants.py`.
  - `rg -n 'atomic_write\(' src | rg -v 'def |atomic_write_config'` lists the seven callers named in Scope.
  - `rg -n "VALID_STATUSES|AVAILABLE_PHASES|canonical_phases" src tests` prints nothing.

  Evidence: the greps.
- [ ] **`adw status` in a directory without `.adw` exits with an error and creates nothing.** Neither do `abort`, `resume`, `pr`, `cleanup` and `logs`. Evidence: `test_read_only_commands_outside_a_project_create_nothing`, RED then GREEN, and a scratch-dir transcript with `echo $?` and `ls -a`.
- [ ] **Lint and tests pass.** Evidence: `scripts/preflight.sh`, and the tail of `uv run pytest` with coverage ≥ 80%, against the baseline of 2982 passed, 5 skipped, 84.79% on `7b61e72a`.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Add adw.git with a timed git() and gh() runner
- [x] TASK-002: Move the branch, commit and diff helpers into adw.git (depends on TASK-001)
- [x] TASK-003: Route the remaining git and gh calls through adw.git (depends on TASK-002)
- [x] TASK-004: Type run status as a RunStatus StrEnum
- [x] TASK-005: Add adw.format and use it everywhere
- [ ] TASK-006: One status style map for the CLI and the dashboard (depends on TASK-004,TASK-005)
- [ ] TASK-007: One atomic_write for state files
- [ ] TASK-008: One runs directory path, created only by adw run (depends on TASK-003,TASK-005,TASK-006,TASK-007)
- [ ] TASK-009: Final Validation
