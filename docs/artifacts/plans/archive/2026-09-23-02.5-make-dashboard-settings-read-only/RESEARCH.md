# Research: Make dashboard settings read-only

Curated findings only — no raw conversation transcripts.

## Key Files & Directories

- `src/adw/dashboard/routes.py`
  - L1697–2164: the settings page. `GET /settings` (`settings()`), `_SETTINGS_TABS`, `build_settings_context` (three near-identical loops for the base, `retry` and `ports` settings), `compute_changed_counts`, `_build_phase_settings`, `build_complex_settings_context`, and the display helpers.
  - `_build_page_context` (L77) supplies `csrf_token` to every page, for the New Run and Abort modals.
- `src/adw/dashboard/partials.py`
  - L1139–1392: three settings routes, `GET /partials/settings-section/task-manager` (`task_manager_fields`), `GET /partials/settings-content` (`settings_content`) and `GET /partials/settings-phase/{phase}` (`phase_config_partial`), plus `PHASE_DEFAULTS` and `_VALID_PHASES`.
  - The module imports `DEFAULT_STATE_MAPPING` only for `task_manager_fields`.
- `src/adw/dashboard/mutations.py`
  - L1–317: `_build_rerun_context`, `POST /runs/start` and `POST /runs/{run_id}/abort`. They stay.
  - L320–1084: the settings save code (`POST /settings/save` and `POST /settings/phase/{phase}/save` and their helpers). It goes.
  - `html`, `os`, `yaml`, `PydanticValidationError`, `ProjectConfig` and `resolve_project_filter` are imported only for it.
- `src/adw/dashboard/templates/partials/`
  - `settings.html` (73 lines): project selector, banner, tabs with changed-count badges, empty states. It stays.
  - `settings_content.html` (572 lines): the forms, list editors, validation JS and indicator JS. Rewritten.
  - `settings_phase_editor.html` (199) and `settings_task_manager_fields.html` (110): deleted.
- `src/adw/dashboard/dependencies.py`: `generate_csrf_token`, `validate_csrf` and `resolve_project_filter`. Unchanged.
- `src/adw/config/loader.py`: `ConfigLoader.load()` reads `.adw/project.yaml`. Without the file, it returns the detected defaults. It raises `ConfigError` on invalid YAML or a failed validation, but not on `OSError`.
- `src/adw/models/command.py`: `get_config_class(phase)` gives `ValidateCommandConfig`, `DocumentCommandConfig`, `ShipCommandConfig` or the base `CommandConfig`. All of them set `extra="forbid"`.
- `src/adw/core/phase_runner.py`
  - L632–793: `_load_command_config` and `_load_project_config` read a phase's `config.yaml`, and `_get_merged_config` merges them. Merging covers `input_files` and `llm` only.
  - A project file that fails validation raises `ConfigError(INVALID_PROJECT_CONFIG)`.
- `src/adw/executors/claude_code.py` L157–159: `--model` is passed only when a model is set.
- `tests/dashboard/`: 156 tests in 2,567 lines.
  - `test_settings_save.py`: 75 tests, 1,100 lines
  - `test_settings_route.py`: 40 tests, 505 lines
  - `test_settings_phase.py`: 22 tests, 478 lines
  - `test_settings_indicators.py`: 19 tests, 484 lines
- `tests/unit/dashboard/conftest.py`: an autouse `isolated_cwd` fixture chdirs each test into `tmp_path`, which the moved tests need.
- `tests/unit/dashboard/test_mutations.py` covers `/runs/start` and CSRF, and `test_abort.py` covers abort. Neither touches settings.

## Architecture Facts

- `ProjectConfig` sets no `extra="forbid"`, so this repo's `project.yaml` loads. Its sections are `llm`, `hooks`, `logging`, `security` (`SecurityConfig | None`, `None` here), `git`, `worktree`, `task_manager` and `webhook`. Nested models: `llm.retry`, `logging.redaction`, `worktree.port_range` and `task_manager.labels`.
- A GET settings route writes nothing today. Only the two POST routes call `_atomic_write_config`. The byte-identity criterion guards against a regression, not a known bug.
- `PHASE_SEQUENCE` in `core/constants.py` gives the five phases in order.
- `resolve_project_filter(registry, name)` returns `(None, name)` for an unregistered name, and `(None, None)` for an empty one.
- `ProjectRegistryManager.get_all()` returns entries whose `.path` and `.name` the settings routes read.
- In `base.html`, the `g s` shortcut, the nav link and `pageMap` point at `/settings` and are unaffected. `#toast-container` (L109) receives only OOB swaps from the settings saves.

## Constraints

- `mypy --strict` and ruff gate CI (`scripts/preflight.sh`).
- The full suite must keep coverage ≥ 80%. Baseline: 3,730 passed, 5 skipped, 85.56%.
- Tests follow ADR-001: behaviour, errors, I/O. No new markup-substring tests. Assert on the data the page shows.
- Dashboard tests run from `tmp_path` (`isolated_cwd`). Fixture projects are real files under `tmp_path`, registered through `app.dependency_overrides[get_project_registry]`.
- `feature/adw-19` (2.3) is open in parallel and edits `dashboard/server.py`, `config/registry.py` and `models/config.py`. Avoid those files.

## Useful Commands

```bash
uv run pytest tests/unit/dashboard -o addopts=""        # dashboard tests, no coverage gate
scripts/preflight.sh                                    # ruff check, ruff format --check, mypy
uv run python -c "from adw.dashboard.server import create_dashboard_app as c; print(sorted((r.path, sorted(r.methods)) for r in c().routes if 'POST' in getattr(r, 'methods', set())))"
shasum .adw/project.yaml .adw/commands/*/config.yaml    # from the main checkout, before and after browsing
```

## Uncertainty

- **Should the phase view merge the resolved tier's config like a run does?** Yes; validation round 1 #1 reversed the first draft. A run's rules:
  - `enabled`: the resolved tier's (`CommandResolver`: project → user `~/.adw/commands/<phase>/` → bundled; a tier counts only if its dir has `prompt.md`), unless the project file sets `enabled` explicitly (`is_phase_enabled`, L795–841)
  - `input_files` and `llm`: the tier's, overlaid key by key by the project file's (`_merge_configs_with_project`, L569–630)
  - phase-specific fields: the project file's only (`_load_project_config`, L436–470: `ship_config`, `lint_command`, `doc_mappings`)

  The view mirrors these rules until 2.8's `load_command_config` replaces both copies.
- **Should `security` (unset) be its own tab?** No: the model-driven split puts it under Basics as `security: —`. It is accurate, and phase 2.1 deletes the field.
- **How to show the evidence screenshots in the PR?** Save them under this plan's `evidence/` folder and link them from the PR body by commit-pinned URLs, since the repo is public. Headless Chrome (`--headless --screenshot`) takes them against a scratch-`HOME` dashboard with this repo registered.

## References

- Epic 02, phase 2.5: `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`
- `docs/features/settings-page-config-viewing.md` and the three editing docs it replaces
- ADR-001: `docs/architecture/adrs/ADR-001-test-reduction-strategy.md`
