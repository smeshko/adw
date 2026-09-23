# Epic 01 — Cleanup: test safety, dead code and bug fixes

Status: planned
Created: 2026-09-23
Depends on: none
Project: none
Linear: ADW-4 (https://linear.app/ivo-tsonev/issue/ADW-4)
Milestone: none

## Overview

First third of the codebase simplification from the 2026-09-23 audit. It does three things:

- Makes the test suite safe to cut against: it stops writing into the checkout and `~/.adw`, and stops sleeping in real time.
- Deletes code that no production path reaches, together with the tests that only exercise it.
- Fixes the behaviour bugs the audit found in duplicated or dead paths, mostly by deleting the duplicate.

No user-facing feature is removed here; that is Epic 02. Each phase is sized to land as one small-to-medium pull request, driven by a single plan under `../plans/`.

## Architecture references

- [AGENTS.md](../../../AGENTS.md): commands, test rules, and the `git_repo`/`chdir` convention that phase 1.1 extends to the whole suite.
- [ADR-001 test reduction strategy](../../architecture/adrs/ADR-001-test-reduction-strategy.md): the test policy that phase 1.4 extends.
- [Orchestrator deep dive](../../architecture/deep-dive/orchestrator.md): run loop and retry, touched by 1.6 and 1.7. Parts of it are stale; trust the code.
- [PhaseRunner deep dive](../../architecture/deep-dive/phase-runner.md): prompt rendering and hooks, touched by 1.9 and 1.10.
- [Template reference](../../templates.md): template variables and includes (1.10).
- [Simplification audit report](https://claude.ai/artifact/P59fUpiUcp7rATwMUSjjmp) (private): findings, evidence and LOC estimates behind every phase. Bug IDs `B1`–`B21` below refer to it.

## Dependencies

- none. This epic builds on the test-isolation start in `9ab939bd` and `cdb2003f`.

## Out of scope

- Removing user-facing features (security, port allocation, webhook server, terminal dashboard, settings editing, wizard steps): Epic 02.
- Consolidating duplicated helpers (git calls, formatting, config loading, logging, task managers): Epic 02.
- Restructuring the run loop (orchestrator, lifecycle, resume, interrupts, extensions): Epic 03. Phases here touch it only to fix a bug.
- Rewriting the BMAD-derived workflow prompts in `src/adw/defaults/commands/`.

## Phase 1.1 — Isolate the test suite from the checkout

**Plan**: [01.1-isolate-test-suite](../plans/archive/2026-09-23-01.1-isolate-test-suite/PLAN.md) · status: done

**Linear**: ADW-7 (https://linear.app/ivo-tsonev/issue/ADW-7)

**Goal**: Tests never touch the checkout, ~/.adw or real wall-clock time, and hook timeouts actually stop child processes.

### What to build

- Root autouse fixture in `tests/conftest.py`:
  - Point `HOME` at `tmp_path`.
  - Set `GIT_AUTHOR_*`/`GIT_COMMITTER_*` so git still works under the new home.
  - Isolate the stats cache and project registry as well as the index. Either set all three `ADW_TEST_*` variables, or rely on `HOME` and delete the env hooks from `core/index_manager.py`, `core/project_registry.py` and `core/stats_aggregator.py`.
- Autouse `monkeypatch.chdir(tmp_path)` for `tests/unit/cli/` and `tests/unit/dashboard/`, extending the per-module chdir added in `9ab939bd`. This covers `test_resume.py::TestFromPhaseValidation`, which runs `adw resume` from the checkout.
- `hooks/runner.py`: start hooks with `start_new_session=True` and `os.killpg` the group on timeout, as `executors/claude_code.py` already does. Fixes B9.
- `tests/fixtures/hooks/slow.sh`: use `exec sleep`.
- `tests/unit/core/test_orchestrator.py`: patch `time.sleep` in `TestRetryLogic`, and delete the wall-clock assertions in `TestTransitionPerformance`.

### Acceptance criteria

- [x] A full `uv run pytest` leaves the following unchanged: `git status`, `git branch`, `git worktree list`, the contents of `.adw/runs/`, and every file under `~/.adw/`.
- [x] A hook with a 1 s timeout whose script starts `sleep 30` raises `HookError` within 3 s.
- [x] Full-suite wall-clock time drops by at least 50 s against the baseline measured at the start of the phase.
- [x] Lint and tests pass.

### Validation

Before and after a full run, record:
- `git status --short | wc -l`
- `git branch`
- `git worktree list`
- `ls .adw/runs | wc -l`
- `shasum ~/.adw/*`

Diff the two snapshots and paste the result, plus both runs' `--durations=15` output, into the PR.

---

## Phase 1.2 — Delete dead modules and symbols

**Plan**: [01.2-delete-dead-code](../plans/01.2-delete-dead-code/PLAN.md) · status: done

**Linear**: ADW-8 (https://linear.app/ivo-tsonev/issue/ADW-8)

**Goal**: Remove code that no production path reaches, together with the tests that only exercise it.

### What to build

- Delete these modules:
  - `src/adw/validation/`, and the `ValidationResult` re-export in `models/__init__.py`.
  - `src/adw/utils/`.
  - `commands/validator.py`, plus `jsonschema` and `types-jsonschema` in `pyproject.toml`.
  - `CommandLoader` and `LoadedCommand`. Move `get_config_class` into `models/command.py` and delete `commands/loader.py`.
- Delete symbols with no production caller. Re-verify each one first by grepping `src/adw`, including templates, YAML and `.sh`:
  - **core:** `Orchestrator.get_next_phase`, `Orchestrator.abort`, `Orchestrator._cleanup_worktree`, `PhaseRunner._merge_configs`, `ProgressCallback`, `ArtifactManager.store_text`, `get_auto`, `get_json` and `get_artifact_paths`, `RunDirectoryManager.acquire_lock`, `RunDirectoryManager.list_runs`, `RunInfo`, `StatsAggregator.get_token_usage`, `PR_DESCRIPTION_ARTIFACT`, `DocumentExtension._git_config`.
  - **models:** `SessionContext`, `ProjectContext`, `RunContext.resolve_artifact_path`, `RunContext.get_runs_dir`, `phase.Artifact`, `ArtifactType`, `ProjectConfig.from_yaml`, `ProjectConfig.from_yaml_file`, `HookResult.is_success`, and the `json_schema_extra` example blocks.
  - **executors, hooks, logging, worktree:** the unused helpers on `MockExecutor` (`all_prompts`, `last_prompt`, `reset`, `assert_called_once`, `assert_called_with`), `ClaudeCodeExecutor.console`, `hooks.runner.find_hook`, `LiveStreamTransport.write_phase`, `LiveStreamTransport.write_raw`, `ConsoleTransport.is_tty`, `WorktreeBranchManager.create_branch`, `ConcurrentRunManager.can_start_run`, `ConcurrentRunManager.get_run_info`.
  - **cli:** `escape_feature_description`, together with its discarded call at `cli/app.py:343`.
- Delete the tests that only cover the above:
  - `tests/unit/validation/*`
  - `tests/unit/utils/test_ulid.py`
  - `tests/unit/commands/test_validator.py`
  - `tests/unit/commands/test_escape.py`
  - the `CommandLoader` tests in `tests/unit/commands/test_loader.py` and `tests/integration/test_document_phase.py`
  - the per-method tests elsewhere
- Update the `ValidationConfig`/`adw.validation` note in `AGENTS.md`.

### Acceptance criteria

- [x] `grep -rn "adw.validation\|adw.utils\|jsonschema\|CommandLoader" src tests pyproject.toml` returns nothing.
- [x] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage at or above 80%. 4039 passed, 5 skipped, 84.09%.
- [x] `adw run --dry-run "noop"` in a scratch repo still lists and renders all five phases. Evidence: the dry-run transcript, plus `adw validate` reporting `OK` for all five phases, because dry-run renders no prompt. See [VALIDATION.md](../plans/01.2-delete-dead-code/VALIDATION.md).
- [x] Lint and tests pass.

### Validation

Paste the grep output (empty), the pytest summary line with the coverage total, and the dry-run output into the PR.

---

## Phase 1.3 — Trim exceptions and re-export surfaces

**Plan**: _not yet created_

**Linear**: ADW-9 (https://linear.app/ivo-tsonev/issue/ADW-9)

**Goal**: Keep only the exception classes that are raised and the package exports that something imports.

### What to build

- Rewrite `src/adw/exceptions.py` down to these classes:
  - `ADWError`, keeping `code`, `suggestion` and `recoverable`.
  - `ConfigError`, `StateError`, `LLMError`, `TaskError`.
  - `HookError`, keeping `phase`, `exit_code`, `stdout`, `stderr` and `duration_ms`.
  - `WorktreeError`, which absorbs `PortAllocationError` and `MaxConcurrentRunsError` as error codes.
- Delete from `exceptions.py`:
  - the never-raised `CommandError` and `PhaseError`
  - `ValidationError`, whose name clashes with pydantic's. Already deleted by phase 1.2 (TASK-002).
  - all `to_dict()` methods, which have no callers
  - the long docstring examples
- Leave `SecurityError` and `LLMRateLimitError` for phases 2.1 and 1.6.
- Trim the `__init__.py` re-export lists that nothing in `src` imports through the package path: `hooks` (20 names, 0 importers), `executors`, `commands`, `logging` and `cli/__init__.py`. Keep the names that shell hooks import: `adw.config.ConfigLoader`.
- Update the `pytest.raises` targets in the affected tests.

### Acceptance criteria

- [ ] `exceptions.py` defines exactly the 7 classes listed under What to build, plus `SecurityError` and `LLMRateLimitError` until their phases land.
- [ ] Every CLI error path still prints its code and suggestion. Confirm with `adw status nonexistent-id` and `adw resume` in an empty directory.
- [ ] `scripts/preflight.sh` and `uv run pytest` pass.
- [ ] Lint and tests pass.

### Validation

Show the CLI output of both error commands before and after in the PR; the text should be unchanged.

---

## Phase 1.4 — Cut test waste outside the dashboard

**Plan**: [01.4-cut-test-waste](../plans/01.4-cut-test-waste/PLAN.md) · status: in-progress

**Linear**: ADW-10 (https://linear.app/ivo-tsonev/issue/ADW-10)

**Goal**: Delete placeholder, prompt-wording and duplicate-fixture tests, and write the rule into ADR-001.

### What to build

- Delete these files; they are docstring-plus-`pass` placeholders or assert prompt wording:
  - `tests/unit/ship/test_failure_diagnosis.py`
  - `tests/unit/ship/test_command_execution.py`
  - `tests/unit/ship/test_release_notes.py`
  - `tests/unit/ship/test_report_generation.py`
  - `tests/unit/commands/test_validate_prompt.py`
  - `tests/unit/commands/test_bundled_commands.py::TestShipPhaseInstructionsXml`
- Move `tests/unit/ship/test_ship_phase_fixes.py` to `tests/unit/core/`.
- Replace the deleted prompt tests with one parametrized test over every bundled phase that checks three things:
  - `config.yaml` validates through `get_config_class`
  - `prompt.md` exists
  - each `instructions.xml` is well-formed
- Remove unused fixtures from `tests/conftest.py`: `tmp_adw_dir`, `mock_executor`, `sample_run_context`, `sample_project_config`, `fixtures_path`, `sample_config_yaml`.
- Delete `tests/fixtures/{llm,configs,runs}/` and `tests/unit/core/test_constants.py`.
- Deduplicate the local `git_repo` redefinitions (4 files) onto the root fixture. Hoist `sample_context` (21 copies) and `executor` (13 copies) into package conftests where the definitions match.
- Delete the trivial and misplaced classes in `tests/unit/executors/test_claude_code.py`:
  - `TestClaudeCodeExecutorClass`
  - `TestHookRunnerTimeoutResolution`, which moves to `hooks/test_runner.py` if it's still relevant
  - the parts of `TestAdditionalParsingCoverage` already covered by `integration/test_token_tracking.py`
- Add three categories to ADR-001's "eliminate" table: HTML markup substrings, prompt/instruction prose, `pass` placeholders.

### Acceptance criteria

- [ ] `grep -rn "^\s*pass$" tests/unit` finds no test body that consists only of `pass`.
- [ ] The collected test count drops by at least 150, and coverage stays at or above 80%.
- [ ] ADR-001 lists the three new categories.
- [ ] Lint and tests pass.

### Validation

Include `uv run pytest --collect-only -q | tail -1` before and after, and the final coverage line, in the PR.

---

## Phase 1.5 — Dependencies, tooling and repo hygiene

**Plan**: _not yet created_

**Linear**: ADW-11 (https://linear.app/ivo-tsonev/issue/ADW-11)

**Goal**: Drop unused dependencies and stale tool config, and make install, release and lint match the uv workflow.

### What to build

- `pyproject.toml`:
  - Change `typer[all]` to `typer`; typer 0.21 has no `all` extra.
  - Evaluate `uvicorn[standard]` → `uvicorn`, since only `run(reload=True)` is used.
  - Remove the mypy overrides for `playwright` (unused) and `httpx` (ships type information), the ruff ignore for the nonexistent `src/adw/models/evidence.py`, the pytest `python_*` settings that equal the defaults, and the unused `slow`/`integration` markers.
- Replace `update.sh`, which runs `pip install -e .` into whatever pip comes first on PATH and pushes directly, with `uv version --bump <part>` plus a documented `uv tool install --editable .`. Or delete it and document both commands in `AGENTS.md`.
- CI and `scripts/preflight.sh`: also run `ruff check` and `ruff format --check` on `tests/`. Drop the `--cov` flags in CI that `addopts` already sets.
- Remove the Story/ISS/Epic references from code comments and docstrings. The audit counted 228 lines, 101 in `core` and 65 in `cli`. This includes the user-visible "(Story 10.1)" in `adw run --help`.
- Delete the untracked directories that hold only `__pycache__`: `tests/unit/evidence`, `tests/unit/validation/validators`, `src/adw/evidence`.

### Acceptance criteria

- [ ] `uv sync --locked` and `scripts/preflight.sh` pass on a clean clone.
- [ ] `grep -rnE "Story [0-9]|ISS-[0-9]|Epic [0-9]" src/adw` returns nothing.
- [ ] `adw run --help` shows no story reference.
- [ ] The documented install command yields an `adw` whose `adw --version` matches `pyproject.toml`.
- [ ] Lint and tests pass.

### Validation

Include the grep output, `adw run --help`, and `which adw && adw --version` after the documented install in the PR.

---

## Phase 1.6 — Fail phases when Claude fails

**Plan**: [01.6-fail-phases-when-claude-fails](../plans/01.6-fail-phases-when-claude-fails/PLAN.md) · status: done

**Linear**: ADW-12 (https://linear.app/ivo-tsonev/issue/ADW-12)

**Goal**: A non-zero Claude Code exit fails the phase and is retried by a single retry layer.

### What to build

- `executors/claude_code.py`: on a non-zero exit, `_build_result` raises `LLMError(recoverable=True)` carrying stderr, instead of returning `LLMResult(success=False)`, which nothing reads (B2).
- Make `Orchestrator._execute_phase_with_retry` the only retry layer, and have it read `RetryConfig` (max attempts, base delay, multiplier, max delay) instead of hard-coded values.
- Delete `executors/retry.py`, its wiring in `cli/bootstrap.py`, `LLMRateLimitError`, and the dead `isinstance` branch that checks for it.
- Remove the `timeout` parameter that is never passed from the executor Protocol and from every implementation.

### Acceptance criteria

- [x] With `MockExecutor` configured to fail twice and then succeed, the phase succeeds on attempt 3 and waits the configured backoff between attempts (sleep patched and asserted).
- [x] With a fake `claude` binary on PATH that exits 1, the phase is recorded as `failed` (not `completed`) in `context.json` and the index after the configured attempts.
- [x] `grep -rn "RetryExecutor\|LLMRateLimitError" src` returns nothing.
- [x] Lint and tests pass.

### Validation

A test drives the fake `claude` script (a shell file that exits 1) through `PhaseRunner`. The PR also shows a real `adw run --phase plan` in a scratch repo with `PATH` pointing at that fake binary, ending in a failed run and not a completed one.

---

## Phase 1.7 — Carry the PR URL on the run context

**Plan**: _not yet created_

**Linear**: ADW-13 (https://linear.app/ivo-tsonev/issue/ADW-13)

**Goal**: Every PR path sets context.pr_url, and nothing closes a ticket before its PR merges.

### What to build

- A core `create_pr(context, base, draft) -> str` that raises `ADWError` on failure, built from the working parts of `cli/pr.py`. The document step and the `adw pr` command both call it, and both set `context.pr_url`. Today `adw pr` writes `context.artifacts["pr"]`, which nothing reads (B12).
- Delete the `pr_result` plumbing: `AutoPRResult`, `_PRResultFromContext`, the tuple return of `_execute_phases`, and the `pr_result` parameters on the lifecycle methods. The completion comment reads `context.pr_url`.
- Delete the preflight guesswork in `cli/pr.py`: `can_auto_create_pr`, `check_git_remote`, `check_gh_authenticated`, `try_auto_create_pr`, the substring-matched suggestions, and the no-op `--no-open` flag. Map `gh` errors instead.
- Auto-close:
  - Delete `task_managers/closer.py`, `task_managers/github_client.py`, and `is_pr_merged` on the `TaskManager` Protocol and both implementations.
  - Stop closing tickets at run completion (B1). Deprecate `auto_close`: it still loads, but does nothing and logs a warning. The default `state_mapping` already moves the ticket on ship.
- Pick one default base branch. Today `"staging"` is hard-coded in 4 places, while `GitConfig` documents `"main"`.

### Acceptance criteria

- [ ] After a mocked run whose document step creates a PR, `context.json` has `pr_url` set, and the completion comment text includes it.
- [ ] After `adw pr <run-id>` against a run with no PR, `context.pr_url` is set.
- [ ] With `auto_close: true` and a Linear task, a completed run leaves the ticket open, and the warning is logged once.
- [ ] `grep -rn "pr_result\|IssueCloser\|GitHubClient\|is_pr_merged" src` returns nothing.
- [ ] Lint and tests pass.

### Validation

Tests cover each criterion, with `gh` stubbed by a fake binary on PATH. The PR shows `context.json` from a real `adw run` on a scratch GitHub repo, with `pr_url` populated.

---

## Phase 1.8 — Fix path, config and default drift

**Plan**: _not yet created_

**Linear**: ADW-14 (https://linear.app/ivo-tsonev/issue/ADW-14)

**Goal**: The dashboard reads the real live.log, ship gets its build command, minimal init writes loadable config, and shared defaults have one source.

### What to build

- Add `LIVE_LOG`, `CONTEXT_FILE` and a `runs_dir(project_root)` helper to `core/constants.py`. Use them in `dashboard/routes.py` (`_load_log_entries`, `log_stream_sse`), which read `runs/<id>/logs/live.log` today (B4), and in the other `live.log` readers and writers.
- Ship build command (B3): the ship extension reads `ProjectConfig.build_command` from the already-loaded config, instead of parsing `<root>/project.yaml`. Delete `_load_project_build_command`.
- Minimal `adw init` writes `project.yaml` through `YAMLWithComments.generate_project_yaml` with the detected basics (B11). Delete `ProjectInitializer.DEFAULT_CONFIG_TEMPLATE`, which also carries a `hooks:` shape that `HookConfig` rejects. Share one `.gitignore`/`.env.template` generator between minimal init and the wizard summary.
- Default Linear state mapping: `TaskManagerConfig` becomes the only definition. Delete the copies in `cli/wizard/task_manager.py`, `task_managers/sync.py`, `config/yaml_generator.py`, `dashboard/partials.py` and `dashboard/routes.py`, all of which import it now (B17).
- Dashboard:
  - One terminal-status set, including `interrupted`, used by both SSE loops (B21).
  - Run-detail cost uses `StatsAggregator.calculate_cost` instead of `tokens * 0.000009`.

### Acceptance criteria

- [ ] With an existing run on disk, the run-detail log search returns entries, and the SSE log stream emits the file's lines.
- [ ] A run in a project with `build_command: "echo built"` exports `ADW_SHIP_BUILD_CMD=echo built` to the ship post-hook.
- [ ] `adw init --no-interactive` followed by `adw validate` passes in a scratch repo.
- [ ] A wizard-generated `project.yaml` contains a `ship` state mapping.
- [ ] Run-detail cost and analytics cost agree for the same run.
- [ ] Lint and tests pass.

### Validation

Include screenshots of run-detail log search and the live stream against a real run in `.adw/runs`, a hook-env dump from a mocked ship run, and the `adw init --no-interactive` + `adw validate` transcript in the PR.

---

## Phase 1.9 — Hook config and phase-hook scripts

**Plan**: _not yet created_

**Linear**: ADW-15 (https://linear.app/ivo-tsonev/issue/ADW-15)

**Goal**: project.yaml hook settings take effect, hook scripts do no work Python already does, and nothing in them fails silently.

### What to build

- `cli/bootstrap.py`: build `HookRunner` from `config.hooks`, not `HookConfig()`, so `timeout_seconds` and `shell` apply (B10).
- `defaults/commands/build/post.sh`: delete step 2, the auto-commit. `PhaseRunner._auto_commit_changes` runs right after it and also checks the expected branch.
- Port `defaults/commands/plan/pre.sh`'s branch switch for non-worktree runs into Python (run start, next to worktree creation) and delete the script. After this, no hook script shells out to `python3 -c "from adw…"`, which silently did nothing when that interpreter lacked adw (B16).
- `defaults/commands/ship/pre.sh` and `ship/post.sh`: delete the dead steps:
  - the subshell `export` of `ADW_PR_NUMBER`
  - the `ADW_TASK_ID` step that writes `task_update_request.json`
  - `ship_status.json`, which nothing reads
- Use `ADW_PR_URL`, which Python already sets.
- `defaults/commands/document/post.sh`: delete step 2, which rewrites the `pr_description.md` that Python already wrote.
- Delete the bundled BMAD copies that no prompt includes (D6):
  - `build/dev-story/checklist.md`
  - `plan/create-story/template.md`
  - `plan/create-story/validation-prompt.md`

### Acceptance criteria

- [ ] With `hooks: {timeout_seconds: 5}`, a post-hook that sleeps 10 s fails after about 5 s.
- [ ] `grep -rn "python3 -c" src/adw/defaults` returns nothing.
- [ ] A non-worktree `adw run` in a scratch repo creates and switches to the feature branch before the plan phase.
- [ ] `tests/integration/test_ship_post_hook.py` and `test_git_hooks.py` pass against the trimmed scripts.
- [ ] Lint and tests pass.

### Validation

Include a scratch-repo transcript of a non-worktree mocked run showing the branch switch, plus the hook-timeout test output, in the PR.

---

## Phase 1.10 — Expand includes before substitution

**Plan**: _not yet created_

**Linear**: ADW-16 (https://linear.app/ivo-tsonev/issue/ADW-16)

**Goal**: ADW variables inside included prompt files are filled in, through one include handler.

### What to build

- `commands/template.py`:
  - Expand `{{include:}}`, `{{shared:}}` and `{{file:}}` first, then substitute variables. Today the order is reversed, so `{{artifacts.build.diff}}` and `{{doc_mappings}}` in included `instructions.xml` files reach the LLM unfilled, and the `test_command`/`lint_command` injection has no effect (B5).
  - Substitute only names ADW defines (`artifacts.*`, `inputs.*`, `task.*`, and the injected command and context variables). LLM-facing placeholders in the BMAD workflow files (`{{story_key}}`, `{{analysis.*}}`, …) must pass through untouched, as lenient mode already does for unknown names.
- Replace the three near-identical include handlers with one `_read_under(root, rel, error_prefix)` that keeps the path-traversal guard.
- Delete `validate_artifact_references`, which is always called non-strict and repeats `render()`'s warning. Delete the test-only `strict` mode, and the per-instance `command_root`/`shared_root` in favour of the per-call arguments.
- Update `docs/templates.md` for the new order.

### Acceptance criteria

- [ ] Rendering the document phase for a run whose build artifacts exist produces a prompt containing the actual diff, not the literal `{{artifacts.build.diff}}`.
- [ ] Rendering the validate phase with `test_command: "uv run pytest"` produces a prompt containing `uv run pytest` wherever the included instructions reference `{{test_command}}`.
- [ ] All LLM-facing placeholders in the bundled prompts are still present verbatim in the rendered output. The test lists them.
- [ ] A traversal attempt such as `{{include:../../etc/passwd}}` still raises.
- [ ] Lint and tests pass.

### Validation

Include rendered-prompt snapshots (before/after) for the document and validate phases from a real run directory. Also run one real `adw run --phase document --from-run <id>` on a scratch repo and inspect the saved prompt.

---

<!-- PHASES -->

## Epic-level acceptance criteria

- [ ] Every phase merged and its acceptance criteria met
- [ ] Status row in [EPICS.md](./EPICS.md) updated to `Done`
- [ ] Bugs B1–B5, B9–B12, B16, B17 and B21 each have a regression test that fails on the pre-epic code
- [ ] The full suite runs without touching the checkout or `~/.adw`, and is at least 50 s faster than before the epic — phase 1.1: no-touch diff empty, 210.2 s → 157.1 s (−53.1 s), see [VALIDATION.md](../plans/archive/2026-09-23-01.1-isolate-test-suite/VALIDATION.md)
- [ ] `src/adw` is at least 3,000 lines smaller than at `cdb2003f`, measured by `find src -name '*.py' | xargs wc -l` — phase 1.2: 46,993 → 44,596 (−2,397; −2,420 against `cdb2003f`'s 47,016), see [VALIDATION.md](../plans/01.2-delete-dead-code/VALIDATION.md)
