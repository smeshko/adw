# Plan: Make dashboard settings read-only

Status: in-progress
Branch: feature/adw-21
Risk: medium
Epic: 02 — Cleanup: remove inert features and consolidate ([epic](../../epics/02-cleanup-remove-and-consolidate.md))
Phase: 2.5 — Make dashboard settings read-only
Linear: ADW-21
Created: 2026-09-23

## Goal

The dashboard's Settings page shows a project's configuration and can no longer write it. `project.yaml` and the phase `config.yaml` files change only when someone edits them by hand.

## Scope

- Add `src/adw/dashboard/settings.py` with one read-only `settings_context(project_root, tab)`. It builds:
  - the tabs
  - the project config's sections, derived from the `ProjectConfig` model
  - each phase's effective config, resolved as a run resolves it (see Decisions)
- `GET /settings` and `GET /partials/settings-content` build their context with it. Today four places build settings context: those two routes, `save_settings` and `_render_settings_error`.
- Rewrite `partials/settings_content.html` as a read-only view: every section on one tab each, and all five phases on the Phases tab. Remove the tab-count badges from `partials/settings.html`, and replace its banner with one that says the page is read-only.
- Delete the editing path (D2, B15):
  - in `dashboard/mutations.py`: `save_settings`, `save_phase_settings`, `_render_settings_error`, `_render_phase_editor_error`, `_SECTION_FIELD_MAP`, the `_INT/_FLOAT/_BOOL_FIELDS` sets, `_parse_form_value`, `_collect_indexed_fields`, `_collect_mapping_fields`, `_deep_set`, `_atomic_write_config` and `_VALID_PHASES`
  - in `dashboard/partials.py`: the `task_manager_fields` and `phase_config_partial` routes, `PHASE_DEFAULTS` and `_VALID_PHASES`
  - in `dashboard/routes.py`: `_SETTINGS_TABS`, `build_settings_context`, `compute_changed_counts`, `_build_phase_settings`, `build_complex_settings_context`, `_resolve_config_value`, `_normalize_default`, `_format_display_value`, `_humanize_field_name`, and the `has_project_config` context key
  - the templates `settings_phase_editor.html` and `settings_task_manager_fields.html`
  - the changed-from-default dots, reset buttons and client-side validation in `settings_content.html`
- Keep the CSRF protection, `generate_csrf_token` and `validate_csrf`, that New Run and Abort use.
- Tests:
  - Delete the edit tests: `tests/dashboard/test_settings_save.py`, `test_settings_phase.py` and `test_settings_indicators.py`.
  - Replace `tests/dashboard/test_settings_route.py` with `tests/unit/dashboard/test_settings.py`, and delete the `tests/dashboard/` package.
- Docs:
  - Rewrite `docs/features/settings-page-config-viewing.md` for the read-only page.
  - Delete `phase-config-editor.md`, `complex-field-editors-task-manager-security.md` and `reset-defaults-changed-indicators-validation.md`, and their `docs/CONDITIONAL_DOCS.md` entries.
  - In epic 02, repoint phase 2.8's read-site bullet from `dashboard/partials.py` to `dashboard/settings.py`.

## Out of Scope

- The config models and the files they read. This repo's own `.adw/commands/{plan,build,validate,document}/config.yaml` still set `timeout_seconds`, which #159 removed. The page shows that validation error; fixing the local files is up to their owner.
- Removing the security, ports and webhook settings: phases 2.1–2.3. The model-driven view drops each section when its model field goes, with no dashboard edit.
- One loader and one merge rule for phase configs: phase 2.8's `load_command_config`. It then replaces this view's copy of the run's merge rules, along with `PhaseRunner`'s.
- `ConfigRegistry` (`config/registry.py`). The YAML generator and the wizard still use it; phase 2.8 renames and trims it.
- Dead dashboard code that 2.11 already owns: `get_config_loader`, `get_config_registry`, `partials/toast.html` and `#toast-container`. Once the settings saves are gone, nothing renders a toast into `#toast-container`.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). In short:

- **Editing code.** The editing path is about 1,480 lines:
  - `mutations.py` L320–1084, about 765 lines
  - `partials.py` L1139–1392, about 255
  - `routes.py` L1697–2164, about 470
  - three templates, 881 lines
- **Tests.** `tests/dashboard/` has 156 tests in 2,567 lines. Nothing under `tests/unit` or `tests/integration` references a settings route or helper.
- **Imports.** The save routes import the context builders from `routes.py` and `PHASE_DEFAULTS` from `partials.py`, inside function bodies. So the builders can only go in the same commit as the save routes.
- **Wrong defaults.** `PHASE_DEFAULTS` (plan/validate→opus, build/ship→sonnet, document→haiku) is not what a run uses. `ClaudeCodeExecutor` passes no `--model` when `llm.model` is unset, so the page showed models that runs never used.
- **Prototype.** A model-driven `settings_context` ran against this repo's real `.adw`:
  - The project config renders as Basics plus 8 sections: llm, hooks, logging, git, worktree, task_manager, webhook, and security (`—`, unset).
  - Ship renders.
  - Plan, build, validate and document fail validation with `timeout_seconds: Extra inputs are not permitted`. A run on those files fails the same way (`INVALID_PROJECT_CONFIG`).
- **Baseline.** 3,730 passed, 5 skipped, coverage 85.56%, at `ce4c1530`.

## Decisions

- **Model-driven sections.** `settings_context` flattens `ProjectConfig` with `_rows()`:
  - Top-level scalars form "Basics".
  - Each nested model field becomes its own tab, with dotted names for deeper models (`retry.max_retries`).
  - This replaces the hand-kept `_SETTINGS_TABS` list and the `ConfigRegistry` lookups. The page shows every section a run reads, including `hooks`, `logging` and `webhook`, which it hid before. When 2.1–2.3 delete `security`, `port_range` and `webhook`, their tabs disappear on their own.
- **Phase values are the effective values, merged the way a run merges them.** `_phase()` resolves the phase with `CommandResolver(project_root)` (project → user → bundled tier). It loads the resolved tier's `config.yaml` and the project's `.adw/commands/<phase>/config.yaml` with `get_config_class(phase)`, then applies `PhaseRunner`'s rules (validation round 1 #1):
  - `enabled` comes from the tier config. The project file overrides it only when it sets `enabled` explicitly (`is_phase_enabled`).
  - `input_files` and `llm` are the tier's, overlaid by the project file's, key by key (`_get_merged_config`).
  - The phase-specific fields (`lint_command`, `doc_mappings`, `commands`, `bypass_ci`, `wait_for_merge`) come from the project file alone (`_load_project_config`), else from the model defaults.
  - When the resolved tier is the project itself, both files are the same file.

  The card lists the files it read. A file that fails to parse or validate shows its error in place of the values, because a run on that file fails too. The bundled `config.yaml` files are all comments, so they contribute only defaults.
- **A new module, `dashboard/settings.py`.** Both routes import it at module level, so no function-level cross-import is added (phase 2.11 removes those). A name-only alternative, putting it in `routes.py`, would force `partials.py` into another in-function import from `routes`.
- **Keep the tabs and `GET /partials/settings-content`.**
  - Tab clicks still swap only the content, and `?tab=` URLs keep working.
  - The Phases tab loses its sub-tabs (the deleted `phase_config_partial`) and lists all five phases.
  - An unregistered `project` on the partial returns a 404 fragment. It used to render an empty default view.
- **Show only name, value(s) and description.** The type badges, "Default: …" hints, changed dots and tab-count badges were aids for editing. The epic removes the changed indicators, and the rest serve no reader of a read-only page.
- **Two implementation commits.** TASK-001 swaps the view: the page stops linking to any edit route, and the old builders stay only for the save code. TASK-002 then deletes the save code, the old builders, both edit partials and the remaining edit tests together. Each commit leaves the suite green.
- **Guard the write surface with a test.** A test collects every `(path, method)` pair in `app.routes` whose method is not `GET` or `HEAD`, and asserts the set is exactly `{("/runs/start", "POST"), ("/runs/{run_id}/abort", "POST")}`. That covers PUT, PATCH and DELETE too, so no write endpoint can come back unnoticed (validation round 1 #3).

## Risks

- **A deleted helper still has a caller outside the settings code.** Mitigation: TASK-002 greps `src` and `tests` for each deleted name before deleting it. mypy follows function-local imports.
- **Coverage drops below the gate.** The deleted tests cover code that is deleted with them. Mitigation: TASK-004 checks the total against the baseline's 85.56%.
- **A concurrent branch edits the same files.** `feature/adw-19` (2.3, draft #212) touches `dashboard/server.py`, `config/registry.py` and `models/config.py`. This plan edits none of them.
- **The view's merge drifts from `PhaseRunner`'s before 2.8 unifies them.** Mitigation: the rules are small and cited in `settings.py`'s docstring. TASK-001's tests pin each one: a user-tier `enabled`/`llm`/`input_files` shows through, and a project override wins. TASK-003 repoints epic phase 2.8's read-site list from `dashboard/partials.py` to `dashboard/settings.py`, so 2.8 replaces this copy (validation round 2 #1).
- **`project.yaml` fails to load.** Today the route logs a warning and silently renders defaults. Mitigation: `settings_context` catches `ConfigError`/`OSError` and returns `config_error`. The page shows it above the tabs, and a test covers a malformed `project.yaml`.

## Acceptance Criteria

- [ ] The settings page renders every section for this repo's `.adw` config. Every tab returns 200, both as a full page and as a partial, and shows its values, or, for an invalid phase file, its validation error. Evidence: the test run, a `curl` of every tab against this repo's `.adw` returning 200, and screenshots of the Basics, Task Manager and Phases tabs.
- [ ] The only POST routes left are run start and abort, and no route accepts PUT, PATCH or DELETE. Evidence: the list of non-GET/HEAD routes printed from `create_dashboard_app().routes`, and the passing guard test.
- [ ] Visiting every settings view leaves `.adw/project.yaml` and `.adw/commands/*/config.yaml` byte-identical. Evidence: the passing byte-identity test, and `shasum` of this repo's config files before and after the smoke `curl`s.
- [ ] `tests/dashboard/` no longer exists. Evidence: `ls tests/dashboard` fails, and `grep -rn "tests/dashboard" pyproject.toml tests` is empty.
- [ ] Nothing new is dead: `uvx vulture src/adw --min-confidence 60`, diffed against the merge-base, reports no new entry. Evidence: the empty `comm -13` output.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%. Evidence: the preflight output, and the pytest summary line with the coverage total.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Render the settings page from a read-only settings_context
- [ ] TASK-002: Delete the settings editing path (depends on TASK-001)
- [ ] TASK-003: Rewrite the settings docs for the read-only page (depends on TASK-002)
- [ ] TASK-004: Final Validation
