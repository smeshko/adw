# Plan: Remove port allocation

Status: in-progress
Branch: feature/adw-18
Risk: medium
Epic: 02 — Cleanup: remove inert features and consolidate ([epic](../../epics/02-cleanup-remove-and-consolidate.md))
Phase: 2.2 — Remove port allocation
Linear: ADW-18
Created: 2026-09-24

## Goal

After this phase:

- Port allocation, which nothing wires up, is gone from code, config, the init wizard, hook environments and `adw list --running`.
- A `project.yaml` that still has `worktree.port_range` loads and validates without error.
- `worktree.max_concurrent` still limits concurrent runs.

## Scope

- **Active runs.** Drop `ActiveRun.backend_port`/`frontend_port`, the matching `register_run` parameters and lock-file keys in `worktree/concurrent.py`. `adw list --running` loses its `Ports` column, and its `--json` output loses the two port keys (`cli/list.py`).
- **Hook environment.** Drop the `port_allocation` parameter from `HookRunner.run_hook`/`_execute_hook` (`hooks/runner.py`) and from `build_hook_environment` (`hooks/environment.py`). Also drop `build_hook_environment`'s `ports_file` parameter, the `.ports.env` auto-detection, `_parse_ports_env_file`, and the `ADW_BACKEND_PORT`, `ADW_FRONTEND_PORT`, `ADW_SLOT` and `ADW_PORTS_FILE` variables.
- **Allocator and model.** Delete `worktree/ports.py` (`PortAllocator`) and `models/worktree.py` (`PortAllocation`), and their re-exports in `worktree/__init__.py` and `models/__init__.py`. Remove `PORT_ALLOCATION_FAILED` and the "cannot get ports" wording from the `WorktreeError` docstring in `exceptions.py`.
- **Wizard.** Delete `cli/wizard/ports.py` and remove it from:
  - `WizardStep`, `STEP_SEQUENCE` and `STEP_TITLES` in `cli/wizard/flow.py`
  - the handler registration in `cli/init.py`
  - the docstring and re-exports in `cli/wizard/__init__.py`
  - the `Ports:` line of the summary panel in `cli/wizard/summary.py`
  - the `# === Worktree & Ports ===` block in `config/yaml_generator.py`, which becomes an always-commented `# === Worktree ===` block with `enabled`, `base_dir` and `max_concurrent`
- **Config.** Delete `PortRangeConfig`, `WorktreeConfig.port_range` and the `validate_port_ranges` validator in `models/config.py`, and the `PortRangeConfig` re-export in `models/__init__.py`. In `config/registry.py`, delete the `ports` section, the `skip_nested=["port_range"]` argument and the `PortRangeConfig` import, and replace `"ports"` with `"worktree"` in `SECTION_ORDER`.
- **Tests.** Delete `tests/unit/worktree/test_ports.py` and `tests/unit/cli/wizard/test_ports.py`, and the port cases in:
  - `test_environment.py`, `test_concurrent.py` and `test_list_running.py`
  - `test_config.py`, `test_registry.py` and `test_yaml_generator.py`
  - `test_summary.py` and `test_flow.py`

  Add tests for a missing `Ports` column, a legacy lock file, and a legacy `project.yaml` that has `worktree.port_range`.

## Out of Scope

- **An `adw validate` warning for a leftover `worktree.port_range`.** Phase 2.3's `REMOVED_PROJECT_SECTIONS` (PR #212, still a draft) handles top-level keys only. Whichever of 2.2 and 2.3 lands second can extend it to this nested key. Here the key is ignored silently, which meets the epic's "loads without error".
- **`adw list --running` ignoring `worktree.max_concurrent` and `base_dir`.** It builds `ConcurrentRunManager(Path.cwd())` with defaults, so the title always says "of 15" and a custom `base_dir` hides lock files. This was already broken and is unrelated to ports. It belongs with phase 2.12 (thin the CLI).
- **Simultaneous starts can both pass the `max_concurrent` check.** `check_can_start_or_raise` runs before worktree creation, and `register_run` only after it, with no atomic reservation in between. The race predates this phase and doesn't involve ports. It is filed as ADW-64.
- **The security (2.1) and webhook (2.3) removals**, although they touch the same wizard, generator, registry and summary files.
- **Replacing the wizard flow controller** (phase 2.6). `tests/unit/cli/wizard/test_state.py` uses `"ports"` only as an arbitrary step name and stays as it is.
- **`build_hook_environment`'s `project_root` parameter**, which no caller passes. It is not port-related.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). In short:

- **Nothing constructs a `PortAllocator`.** Nothing outside `worktree/ports.py` and its tests calls `PortAllocator`, `write_ports_env` or `allocate`. `run_lifecycle._setup_worktree` calls `register_run(run_id=…, worktree_path=…)` without ports, and neither `phase_runner` hook call passes `port_allocation`. The `.ports.env` auto-sourcing in `build_hook_environment` would only fire for a file a user wrote by hand.
- **Stale keys load silently.** `WorktreeConfig` and `ProjectConfig` set no `extra=`, so Pydantic ignores unknown keys, and a leftover `port_range:` loads once the field is gone. `ConfigChecker` validates through `ProjectConfig.model_validate`, so `adw validate` accepts it too.
- **Old lock files still parse.** `get_active_runs` reads lock keys by name (`data["run_id"]` and so on), so `backend_port`/`frontend_port` keys written by an older ADW are ignored.
- **`max_concurrent` doesn't depend on ports.** `Orchestrator` builds `ConcurrentRunManager(max_concurrent=worktree_config.max_concurrent)`, and `check_can_start_or_raise` raises `MAX_CONCURRENT_REACHED`. The removed validator only read `max_concurrent` to bound the port ranges.
- **The dashboard needs no edit.** Its settings page flattens `ProjectConfig` by reflection (`dashboard/settings.py:_rows`), so the `worktree.port_range.*` rows go away with the field.
- **Docs.** Nothing under `docs/` outside `artifacts/` mentions ports, `.ports.env` or `ADW_SLOT`.
- **Baseline.** `uv run pytest` on `ad704a17`: 3581 passed, 5 skipped, coverage 85.33% (gate 80%).

## Decisions

- **A leftover `worktree.port_range` is silently ignored, with no validate warning.** The epic asks only that it load. The warning mechanism exists only on draft PR #212, and building a second one here would conflict with it (see Out of Scope).
- **Drop `.ports.env` auto-sourcing outright, with no deprecation path.** ADW never writes the file (`PortAllocator.write_ports_env` has no caller), and the epic lists it for removal.
- **`adw list --running --json` drops `backend_port`/`frontend_port`.** The values were always `null`, since nothing passed ports to `register_run`.
- **The generator's worktree block is always commented.** Customised ports were the only thing that made it active. With them gone, every value in it is a default, like the other commented blocks.
- **The acceptance grep allows one file: the legacy-config regression test.** The gate is per file, not per hit. The test's name, its comment and its YAML all contain `port_range`, so it matches on several lines, all in `tests/unit/models/test_config.py`. The epic asks both for an empty `grep "…port_range…" src tests` and for a `project.yaml` with `worktree.port_range` to keep loading. A regression test for the second has to contain the key. The fixture uses an overlapping range that the old validator rejected, so it fails RED today and proves the key is ignored. Phase 2.3 made the same trade: its grep kept one file, `checker.py`.
- **Replace `"ports"` with `"worktree"` in `SECTION_ORDER`, not just delete it.** The worktree block sits at that position in the generated `project.yaml`, and `worktree` is a real section in the catalog.
- **Task order keeps every commit green.** TASK-002 removes the only importers of `PortAllocation` (the hooks), and TASK-004 removes the only importer of `adw.worktree.ports` outside its package (`cli/wizard/ports.py`). So TASK-003 runs after both, and the `## Tasks` list puts TASK-004 before TASK-003. TASK-004 also removes the generator's `port_range` output before TASK-005 drops the field. TASK-001 is independent.

## Risks

- **Parallel worktrees edit neighbouring lines.** Phase 2.1 (`feature/adw-17`) and draft PR #212 (phase 2.3) edit the same `flow.py`, `init.py`, `wizard/__init__.py`, `summary.py`, `yaml_generator.py`, `registry.py` and `models/__init__.py`, and the same test fixtures. Mitigation: each task removes only port lines, and none reformats the code around them. Rebase on `origin/staging` before the PR and again before merging.
- **A user hook that reads `ADW_BACKEND_PORT` or a hand-written `.ports.env` stops getting those values.** ADW never set them in a real run, so only a hand-written `.ports.env` is affected. This is intended by the epic, and the PR body calls it out.
- **The runtime evidence uses a real `adw run`.** Mitigation: a scratch git repo under the session scratchpad, a temp `HOME` and `ADW_MOCK_EXECUTOR=1`. The run is refused before any worktree is created, and this checkout is never targeted.

## Acceptance Criteria

- [ ] `grep -rn "PortAlloc\|port_range\|ports.env" src` returns nothing, and `grep -rln "PortAlloc\|port_range\|ports.env" tests` lists only `tests/unit/models/test_config.py`, which holds the legacy-config regression test (see Decisions). Evidence: both grep outputs.
- [ ] `adw list --running` shows no port column. Evidence: `test_list_running_has_no_ports_column`, RED then GREEN, plus a scratch-repo transcript with one mocked active run.
- [ ] A `project.yaml` that still has `worktree.port_range` loads without error and keeps its `max_concurrent`. Evidence: `test_legacy_port_range_is_ignored`, RED then GREEN. Its overlapping range fails validation before the change and loads after it. Plus `adw validate` against a legacy file in a scratch repo, which exits 0.
- [ ] `max_concurrent` is still enforced for a run started while the limit's worth of runs are live (sequential starts; see Out of Scope for the simultaneous-start race). Evidence: the existing `test_check_can_start_or_raise_raises_at_limit` passes, which pins the `MAX_CONCURRENT_REACHED` code. In a scratch repo with `max_concurrent: 1` and one live lock, `adw run` prints "Maximum concurrent runs reached (1)", exits non-zero and creates no worktree. The CLI prints the message, not the code.
- [ ] `adw init --wizard` has no ports step, and the generated `project.yaml` has no `port_range`. Evidence: `test_run_marks_steps_completed` asserting that the controller run never visits `ports`, and the `test_yaml_generator.py` assertions, both RED then GREEN.
- [ ] Lint and tests pass. Evidence: `scripts/preflight.sh` and the tail of `uv run pytest`, with coverage ≥ 80%.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Drop port fields from active runs and adw list --running
- [x] TASK-002: Remove port variables and .ports.env sourcing from hook environments
- [x] TASK-004: Remove the ports step from the init wizard
- [x] TASK-003: Delete PortAllocator, PortAllocation and the port error code (depends on TASK-002, TASK-004)
- [ ] TASK-005: Drop WorktreeConfig.port_range and keep old configs loading (depends on TASK-004)
- [ ] TASK-006: Final Validation
