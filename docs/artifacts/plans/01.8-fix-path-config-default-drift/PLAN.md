# Plan: Fix path, config and default drift

Status: in-progress
Branch: feature/adw-14
Risk: medium
Epic: 01 — Cleanup: test safety, dead code and bug fixes ([epic](../../epics/01-cleanup-safety-dead-code-bugs.md))
Phase: 1.8 — Fix path, config and default drift
Linear: ADW-14
Created: 2026-09-23

## Goal

After this phase:

- The dashboard reads the `live.log` that runs actually write.
- The ship post-hook receives the project's `build_command`.
- Minimal `adw init` writes a `project.yaml` that `adw validate` accepts.
- The Linear state mapping has one definition, which includes `ship`.
- Both SSE streams close on every terminal status.
- Run-detail cost matches analytics.

## Scope

- `core/constants.py` gains three names:
  - `LIVE_LOG`
  - `CONTEXT_FILE`
  - `project_runs_dir(project_root)`

  They replace hand-built paths in three places:
  - every `live.log` reader and writer: `dashboard/routes.py`, `dashboard/partials.py`, `cli/logs.py` and `cli/bootstrap.py`
  - every `.adw/runs` join inside `src/adw/dashboard/`
  - the `context.json` joins in `core/context_manager.py` and `cli/logs.py`

  This fixes B4.
- `ShipExtension` takes `build_command` from the loaded `ProjectConfig` through `create_default_registry`, and exports `ADW_SHIP_BUILD_CMD` even when the project has no ship-config override. Delete `_load_project_build_command` (B3).
- `ProjectInitializer` writes `project.yaml` through `YAMLWithComments.generate_project_yaml`, with `name` set to the directory name. Delete these three class attributes:
  - `DEFAULT_CONFIG_TEMPLATE`
  - `GITIGNORE_CONTENT`
  - `ENV_TEMPLATE_CONTENT`

  `generate_gitignore()` and `generate_env_template()` move to `config/initializer.py`, and the wizard summary imports them. The wizard's basics step records `project_name` (B11).
- `DEFAULT_STATE_MAPPING` in `models/config.py` becomes the only default mapping, and `TaskManagerConfig` uses it. These files import it instead of keeping their own copy:
  - `cli/wizard/task_manager.py`
  - `task_managers/sync.py`
  - `config/yaml_generator.py`
  - `dashboard/partials.py`
  - `dashboard/routes.py`

  The wizard now prompts for `ship` too (B17).
- `TERMINAL_STATUSES` in `core/constants.py`, including `interrupted`, used by `run_events_sse` and `log_stream_sse` (B21).
- `StatsAggregator.get_phase_token_usage(run_dir)`: `_parse_llm_response_files` becomes a sum over it. Run detail prices the run total and each phase through `calculate_cost`, replacing `tokens * 0.000009`.

## Out of Scope

- The other ~25 `.adw/runs` joins outside `src/adw/dashboard/` (in `stats_aggregator`, the worktree manager, the cli commands and `run_directory`), and `bootstrap.get_runs_dir`/`logs._get_runs_dir` beyond calling the new helper. Consolidating them belongs to Epic 02.
- Deleting `StatsAggregator.get_token_usage`. This plan neither uses nor removes it; phase 1.2 deletes it.
- Moving `get_config_class` out of `commands/loader.py` (phase 1.2), and trimming the rest of the `task_managers/__init__.py` re-exports (phase 1.3).
- `auto_close` and the default base branch (phase 1.7).
- The ship-config early return for `ADW_SHIP_BYPASS_CI`/`ADW_SHIP_WAIT_FOR_MERGE`. `post.sh` defaults (`true`/`false`) match `ShipCommandConfig`, so an absent override changes nothing.
- How the dashboard renders `interrupted` runs in the phase pipeline (`status in ("failed", "aborted")` at `routes.py` ~450/617/657). B21 covers only the SSE loops.
- `live.log`'s line format, and `worktree.manager.DEFAULT_PRESERVE_ARTIFACTS`. `live.log` is written to the main checkout's run dir, so preservation doesn't apply.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). Each bug was confirmed against real data or reproduced:

- **B4**: all 44 real runs in the main checkout keep `live.log` at `runs/<id>/live.log`, and `runs/<id>/logs/` is empty. The dashboard reads `runs/<id>/logs/live.log`. Two test files write their fixture at the wrong path, so the tests share the bug. The dashboard's line regex matches real lines (`[LLM]`, `[TOOL]`, `[INFO]`), so fixing the path is enough.
- **B3**: `_load_project_build_command` reads `<root>/project.yaml`, not `<root>/.adw/project.yaml`. `get_hook_env` also returns `{}` before the build command whenever `.adw/commands/ship/config.yaml` is absent.
- **B11**: in a scratch repo, `adw init --no-interactive` then `adw validate` gives `Value error, Missing required fields: name`. A prototype through `YAMLWithComments` with `project_name` set loads and validates: 0 errors, 0 warnings.
- **B17**: `cli/wizard/task_manager.py` and `task_managers/sync.py` lack `ship`. A wizard user who opens the mapping prompt and accepts every default gets an active `state_mapping` without `ship`, so ship never moves the ticket to Done (reproduced). `TestConstants::test_default_state_mappings_covers_all_phases` asserts that `ship` is missing.
- **B21**: both SSE loops test `("completed", "failed", "aborted")`. An `interrupted` run never closes either stream.
- **Cost**: run detail uses `tokens * 0.000009`. Analytics uses `calculate_cost(_parse_llm_response_files(run_dir))`, which prefers `actual_cost_usd`. The response files are `llm/NNN_<phase>_response.json` (`phase_runner.py:1360`), so cost per phase is recoverable.

## Decisions

- **The helper is `project_runs_dir(project_root)`, not the epic's `runs_dir`.** Every dashboard call site already has a local variable called `runs_dir`. `runs_dir = runs_dir(project_path)` would make the name local and raise `UnboundLocalError`.
- **Path scope: log readers and writers plus the dashboard package** (user's choice). The remaining `.adw/runs` joins wait for Epic 02, which owns helper consolidation.
- **`TERMINAL_STATUSES` lives in `core/constants.py`, next to the path constants.** `interrupted` emits `run-failed` on the events stream, the same as `failed`/`aborted`: every non-`completed` terminal status is shown as a failure.
- **Per-phase cost comes from the llm response files** (user's choice). `get_phase_token_usage` is the only parser, and `_parse_llm_response_files` sums its values. Analytics and run detail therefore read the same numbers by construction.
- **`build_command` goes in through the constructor.** `create_default_registry(..., build_command=None)` → `ShipExtension(project_root, build_command)`. Bootstrap already holds the loaded `ProjectConfig`, so nothing re-reads YAML.
- **Shared `.gitignore`/`.env.template` generators live in `config/initializer.py`.** It's the lower layer, and `cli/wizard/summary.py` imports from it. The wizard's `.gitignore` content wins because it is a superset (`logs/`, `state.json`), so nothing that was ignored stops being ignored.
- **The `project.yaml` header becomes `# Generated by adw init on <date>`.** Both init paths now share the generator, so "ADW Init Wizard" would be wrong for minimal init.
- **The wizard basics step records `project_name = project_root.name`** (user's choice). Both init paths then write the same `name`.
- **`DEFAULT_STATE_MAPPING` is a module constant in `models/config.py`.** `TaskManagerConfig.state_mapping` uses `default_factory=lambda: dict(DEFAULT_STATE_MAPPING)`. Consumers that mutate their copy take `dict(...)` of it. The `task_managers/__init__.py` re-export of the old sync copy is removed.

## Risks

- **A RED test for B21 hangs on today's code**, because the stream never ends. Mitigation: call the route function directly, patch `adw.dashboard.routes.asyncio.sleep`, and drain `body_iterator` under `asyncio.wait_for(..., timeout=2)`. RED fails with `TimeoutError` in 2 s.
- **Run-detail tests use a `MagicMock` stats aggregator**, so `get_phase_token_usage` would return a mock. Mitigation: the tests that render cost build a real `StatsAggregator` with mocked index and registry, and llm files under `tmp_path`.
- **Phases 1.2–1.7 are unplanned and touch neighbouring code:**
  - 1.2 moves `get_config_class`, which `ship.py` imports.
  - 1.4 moves `tests/unit/ship/test_ship_phase_fixes.py`.
  - 1.3 trims `task_managers/__init__.py`.

  Mitigation: this plan leaves those imports and files where they are, so a later rebase is a mechanical conflict.
- **Real-run evidence reads the real `~/.adw` index** through the web dashboard. Mitigation: view pages only, and click no abort/delete/settings controls. Stop the server afterwards.
- **The wizard prompt count changes from 5 to 6.** Tests that feed `Prompt.ask` side effects break. Mitigation: TASK-004 updates `test_state_mapping_accepts_defaults`.

## Acceptance Criteria

- [ ] With an existing run on disk, the run-detail log search returns entries, and the SSE log stream emits the file's lines. Evidence:
  - a writer → reader test: `create_log_manager(run_dir=…)` writes, and `_load_log_entries` reads it back
  - `test_log_stream_emits_live_log_lines`
  - a run-detail log-search screenshot against a real run from the main checkout's `.adw/runs`
  - a `curl -N` SSE transcript
- [ ] A run in a project with `build_command: "echo built"` exports `ADW_SHIP_BUILD_CMD=echo built` to the ship post-hook. Evidence: a bootstrap wiring test, plus a hook-env dump from a mocked ship run in a scratch repo.
- [ ] `adw init --no-interactive` followed by `adw validate` passes in a scratch repo. Evidence: a CLI test, plus a scratch-repo transcript.
- [ ] A wizard-generated `project.yaml` contains a `ship` state mapping. Evidence: a test that accepts every default in the mapping prompt, generates the YAML, and loads it; `state_mapping["ship"] == "Done"`.
- [ ] An `interrupted` run closes both SSE streams. Evidence: RED (a 2 s timeout) and then GREEN, for `run_events_sse` and `log_stream_sse`.
- [ ] Run-detail cost and analytics cost agree for the same run. Evidence: a test that renders both pages for a one-run project, where both show the same `$N.NN`.
- [ ] `grep -rn '"In Review"' src/adw --include='*.py'` lists only `models/config.py`, and `grep -rn "0.000009\|_load_project_build_command\|DEFAULT_CONFIG_TEMPLATE" src` returns nothing.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Read and write live.log through shared path constants
- [x] TASK-002: Pass build_command from ProjectConfig to the ship hook
- [ ] TASK-003: Write minimal-init project.yaml through YAMLWithComments
- [ ] TASK-004: Define the default state mapping once
- [ ] TASK-005: Close both SSE streams on every terminal status
- [ ] TASK-006: Price run-detail cost with calculate_cost
- [ ] TASK-007: Final Validation
