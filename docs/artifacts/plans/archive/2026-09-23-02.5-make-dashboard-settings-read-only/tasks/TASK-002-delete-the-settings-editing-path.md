# TASK-002: Delete the settings editing path

Depends on: TASK-001
Suggested commit: `refactor(dashboard): delete settings editing routes and helpers`

## Goal

The dashboard has no code that writes a config file, and its only POST routes are run start and abort.

## Files

- `src/adw/dashboard/mutations.py`
  - Delete everything from `# ── Settings save` to the end of the file (L320–1084).
  - Drop the imports only it used: `html`, `os`, `yaml`, `PydanticValidationError`, `ProjectConfig` and `resolve_project_filter`.
  - Leave the docstring's "every route requires CSRF" line as it is; it still holds.
- `src/adw/dashboard/partials.py`
  - Delete `task_manager_fields`, `phase_config_partial`, `PHASE_DEFAULTS`, `_VALID_PHASES` and their section comments.
  - Drop `DEFAULT_STATE_MAPPING` and any import left unused.
- `src/adw/dashboard/routes.py`
  - Delete `_SETTINGS_TABS`, `_humanize_field_name`, `_resolve_config_value`, `_normalize_default`, `_format_display_value`, `build_settings_context`, `compute_changed_counts`, `_build_phase_settings` and `build_complex_settings_context`.
  - Drop `DEFAULT_STATE_MAPPING` and any import left unused.
- `src/adw/dashboard/templates/partials/settings_phase_editor.html` and `settings_task_manager_fields.html`: deleted.
- `tests/dashboard/test_settings_save.py`, `tests/dashboard/test_settings_phase.py` and `tests/dashboard/__init__.py`: deleted, which removes `tests/dashboard/`.
- `tests/unit/dashboard/test_settings.py`: add the write-surface guard test.

## Acceptance

- [ ] The set of `(path, method)` pairs in `create_dashboard_app().routes` with a method other than `GET`/`HEAD` is exactly `{("/runs/start", "POST"), ("/runs/{run_id}/abort", "POST")}`. The guard test asserts it, so PUT, PATCH and DELETE are covered too.
- [ ] `grep -rnE "save_settings|save_phase_settings|_atomic_write_config|_SECTION_FIELD_MAP|PHASE_DEFAULTS|build_settings_context|compute_changed_counts|_build_phase_settings|build_complex_settings_context|task_manager_fields|phase_config_partial|settings_phase_editor|settings_task_manager_fields|\"has_project_config\"" src/adw/dashboard tests` returns nothing. The quoted `"has_project_config"` matches only the deleted context key. `settings.py` still reads `ConfigLoader.has_project_config`, the property, for `has_project_file` (validation round 3 #1).
- [ ] `tests/dashboard/` does not exist.
- [ ] `uv run pytest tests/unit/dashboard -o addopts=""` passes and `scripts/preflight.sh` passes.

Evidence: the guard test's pass, the empty grep, `ls tests/dashboard` failing, and the preflight output.

## Steps

### RED
- [ ] Add `test_only_run_start_and_abort_accept_writes` to `tests/unit/dashboard/test_settings.py`. It collects `(route.path, method)` for every route method outside `{"GET", "HEAD"}`, skipping routes without `methods` (mounts), and compares the set. It fails while `/settings/save` exists.

### GREEN
- [ ] Before deleting each name, grep `src` and `tests` for its callers. Expect only the settings code and `tests/dashboard/`.
- [ ] Delete the code, templates and test files listed above.

### REFACTOR
- [ ] `uv run ruff check --fix src/adw/dashboard` for unused imports, then `scripts/preflight.sh`.
- [ ] `uv run pytest tests/unit/dashboard -o addopts=""`.
- [ ] Run the acceptance grep.

## Notes

- `generate_csrf_token` stays imported in `partials.py` for `new_run_modal` and `abort_modal`, and `validate_csrf` stays in `mutations.py` for both POST routes. Don't let `ruff --fix` or a hand edit drop them.
- `logger`, `Path`, `Any` and the `TYPE_CHECKING` imports in `mutations.py` are still used by `start_run`/`abort_run`. Check before removing any of them.
