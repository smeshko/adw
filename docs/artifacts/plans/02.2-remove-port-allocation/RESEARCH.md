# Research: Remove port allocation

Curated findings only — no raw conversation transcripts.

## Key Files & Directories

- `src/adw/worktree/ports.py` (210 lines): `PortAllocator`, with `calculate_slot` (an MD5 of the run id mod `max_concurrent`), `allocate` (probes sockets for a free slot, then raises `PORT_ALLOCATION_FAILED`) and `write_ports_env` (writes `.ports.env` into a worktree). It has no production caller.
- `src/adw/models/worktree.py` (56 lines): holds only `PortAllocation` (`slot`, `backend_port`, `frontend_port`, `run_id`). It is imported only by `worktree/ports.py`, `models/__init__.py`, and the `TYPE_CHECKING` blocks of `hooks/environment.py` and `hooks/runner.py`.
- `src/adw/cli/wizard/ports.py` (316 lines): `PortsStepHandler`, `run_ports_step`, `validate_port`, `is_common_port` and `check_port_overlap`. Only `cli/wizard/__init__.py` imports it.
- `src/adw/models/config.py`: `PortRangeConfig` (`:190`), `WorktreeConfig.port_range` (`:258`) and `validate_port_ranges` (`:269`). The validator reads `max_concurrent` only to bound the port ranges.
- `src/adw/worktree/concurrent.py`: `ActiveRun.backend_port`/`frontend_port` and `register_run(..., backend_port, frontend_port)`. The one production `register_run` call (`core/run_lifecycle.py:659`) passes neither.
- `src/adw/hooks/environment.py`: `build_hook_environment(port_allocation=, ports_file=)` sets `ADW_BACKEND_PORT`, `ADW_FRONTEND_PORT` and `ADW_SLOT`, and auto-sources `<worktree>/.ports.env` (`ADW_PORTS_FILE` plus its variables). `hooks/runner.py` passes `port_allocation` through. Neither `run_hook` call in `core/phase_runner.py` (`:301`, `:1061`) passes it.
- `src/adw/cli/list.py`: the `Ports` column in `_display_running_runs` (`:373`) and the port keys in `_output_json_running` (`:452`).
- `src/adw/config/yaml_generator.py:178-200`: the `# === Worktree & Ports ===` block. It is active only when the wizard's ports differ from 9100/9200.
- `src/adw/config/registry.py`: a `ports` section built from `PortRangeConfig`, `skip_nested=["port_range"]` on `worktree`, and `"ports"` in `SECTION_ORDER`. Only tests call `get_section_order`.
- `src/adw/cli/wizard/summary.py:206-213`: the `Ports:` line of the summary panel.
- `src/adw/dashboard/settings.py`: flattens `ProjectConfig` by reflection (`_rows`), and nothing in it names ports. It needs no edit.

## Architecture Facts

- **Unknown keys are dropped.** `ProjectConfig` and `WorktreeConfig` set no `model_config`/`extra=`, so Pydantic's default `extra="ignore"` applies. A leftover `worktree.port_range` loads silently once the field is gone. `ConfigChecker.check_project_config` (behind `adw validate`) goes through `ProjectConfig.model_validate`, so it passes too.
- **Enforcement is independent of ports.** `Orchestrator.__init__` builds `ConcurrentRunManager(max_concurrent=self.worktree_config.max_concurrent, base_dir=…)` when worktrees are enabled. `RunLifecycle._create_worktree_for_run` calls `check_can_start_or_raise()` before fetching or creating the worktree, and it raises `WorktreeError("MAX_CONCURRENT_REACHED")`.
- **Lock files are read by key.** `get_active_runs` builds `ActiveRun(run_id=data["run_id"], …)` field by field, so extra keys in an old lock file are never read.
- **`adw list --running` uses defaults.** It builds `ConcurrentRunManager(Path.cwd())` with the default `max_concurrent=15` and `base_dir="trees"`, ignoring `project.yaml`. This is pre-existing and out of scope.

## Constraints

- **Parallel branches.** `feature/adw-17` (phase 2.1, security) and draft PR #212 (`feature/adw-19`, phase 2.3, webhook) edit the same wizard, generator, registry, summary and `models/__init__.py` lines, and the same test fixtures. Keep edits line-local.
- **PR #212 adds `REMOVED_PROJECT_SECTIONS`** to `config/checker.py`, for top-level keys only. It isn't on `staging`, so this plan can't extend it.
- **Tests follow ADR-001.** No tests that only assert an attribute is gone, and no enum-existence or count tests. `test_flow.py:test_step_sequence_defined` hard-codes `len(STEP_SEQUENCE) == 10`, which every removed step breaks. A test that runs `adw run` or touches git uses a throwaway directory.
- **The epic's grep and its back-compat criterion conflict.** An empty `grep "port_range" src tests` rules out a regression test for loading a legacy `port_range`. The plan keeps the test and allows it as the grep's one hit.
- **The CLI prints `ADWError.message` and `suggestion`, never `code`** (`cli/app.py`). Runtime transcripts show "Maximum concurrent runs reached (1)", not `MAX_CONCURRENT_REACHED`.
- **Lock files need every key `get_active_runs` reads:** `run_id`, `pid`, `start_time` (ISO) and `worktree_path`. A missing key counts as corruption, and the lock is deleted.

## Useful Commands

```bash
# Acceptance grep
grep -rn "PortAlloc\|port_range\|ports.env" src tests
# Partial runs, without the coverage gate
uv run pytest tests/unit/worktree tests/unit/cli/test_list_running.py -o addopts=""
uv run pytest tests/unit/hooks tests/unit/cli tests/unit/config tests/unit/models -o addopts=""
# Lint, format and types, as in CI
scripts/preflight.sh
```

## Uncertainty

- **Does any user hook depend on `.ports.env` or `ADW_*_PORT`?** ADW never allocated ports in a real run, so `ADW_*_PORT` was never set. `.ports.env` was sourced only if a user put one in the worktree by hand. Accepted as intended by the epic, and called out in the PR.
- **Should `adw validate` warn about the dead key?** It doesn't, for now. See PLAN.md, Decisions.

## Baseline

`uv run pytest` on `ad704a17`: 3581 passed, 5 skipped, coverage 85.33% (gate 80%), 200 s. The deleted `worktree/ports.py` is 100% covered (41 statements), so removing it and its tests leaves the gate well clear.

## References

- Epic: [02 — phase 2.2](../../epics/02-cleanup-remove-and-consolidate.md)
- Linear: ADW-18
- Sibling plan for the same pattern: phase 2.3 on `feature/adw-19` (`docs/artifacts/plans/02.3-remove-webhook-server/`)
