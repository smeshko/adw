# TASK-001: Render the settings page from a read-only settings_context

Depends on: None
Suggested commit: `refactor(dashboard): render settings from one read-only settings_context`

## Goal

`GET /settings` and `GET /partials/settings-content` render a read-only view built by one `settings_context()`. The page no longer links to any edit route.

## Files

- `src/adw/dashboard/settings.py` (new): `settings_context(project_root: Path, tab: str) -> dict[str, Any]`, plus the private helpers `_rows`, `_lines`, `_inline`, `_project_sections`, `_phase` and `_load_phase_file`. `_phase` resolves the tier with `adw.commands.resolver.CommandResolver` and merges the tier and project configs by `PhaseRunner`'s rules (PLAN.md Decisions).
- `src/adw/dashboard/routes.py`
  - `settings()` resolves the project, then calls `settings_context`. It drops `ConfigLoader`/`ConfigRegistry`, the `has_project_config` key, `changed_counts`, `csrf_token` (already in `_build_page_context`), `settings_sections`, `phase_settings` and the complex context.
  - The old builders stay for now, because `mutations.py` still imports them.
- `src/adw/dashboard/partials.py`: `settings_content()` calls `settings_context`. An unregistered project returns a 404 fragment.
- `src/adw/dashboard/templates/partials/settings_content.html`: rewritten read-only (~60 lines). It holds a `rows` macro, one tab per section, and a Phases tab with one card per phase (the files merged, or "defaults", then the rows or the validation error).
- `src/adw/dashboard/templates/partials/settings.html`:
  - The tab loop reads `settings_tabs` from the new context.
  - Remove the changed-count badges.
  - Show `config_error` as an alert, and a note when `.adw/project.yaml` is missing.
  - The banner says the page is read-only and names the files to edit.
- `tests/unit/dashboard/test_settings.py` (new): replaces `tests/dashboard/test_settings_route.py`, which this task deletes.
- `tests/dashboard/test_settings_indicators.py`: deleted. The indicators it tests are gone from the page.

## Acceptance

- [ ] `settings_context` against a fixture project returns:
  - the project values: Basics `name`, `git` `base_branch`, `task_manager` `team_key`, and the nested `retry.max_retries` default
  - a `phases` entry per `PHASE_SEQUENCE` item, carrying the project file's values (ship's `commands.version_bump`, validate's `lint_command`, plan's `enabled: false`) or its model defaults when there is no file
- [ ] A phase file with an unknown key, like this repo's `timeout_seconds`, sets that phase's `error` and leaves the other phases' values intact.
- [ ] Effective merge, matching `PhaseRunner`. The user tier here is a `$HOME/.adw/commands/build/` holding `prompt.md` and a `config.yaml` with `enabled: false`, `llm: {model: haiku}` and `input_files: {a: x.md}`. The per-test `isolated_home` fixture makes it safe.
  - With no project file for build, the phase shows `enabled: false`, `llm.model: haiku` and `input_files` `a: x.md`, and its sources list the user file.
  - A project file with `input_files: {b: y.md}` and `llm: {model: opus}` gives both `input_files` keys and `llm.model: opus`, with `enabled` still `false`.
  - A project file that sets `enabled: true` explicitly flips it back.
  - Phase-specific fields come from the project file only (validation round 3 #2). Parametrized over validate (`lint_command`), document (`doc_mappings`) and ship (`commands.version_bump`, `bypass_ci`): a user-tier `config.yaml` (with `prompt.md`) that sets the field leaves it at the model default. A project file that sets it shows the project's value.
- [ ] A malformed `project.yaml` sets `config_error`, and phases still render. A missing `project.yaml` gives the detected defaults and `has_project_file == False`.
- [ ] Every tab returns 200 in all three renders: `/settings` as a full page, `/settings` as an HTMX partial, and `/partials/settings-content`. Each shows its section's values. The `.adw` files' SHA-256 digests and file set are unchanged afterwards.
- [ ] `/partials/settings-content` with an unregistered project returns 404. The no-projects and no-selection empty states still render.
- [ ] `uv run pytest tests/unit/dashboard tests/dashboard -o addopts=""` passes and `scripts/preflight.sh` passes.

Evidence: the pytest output for `tests/unit/dashboard/test_settings.py` and the rest of the dashboard tests, and the preflight output.

## Steps

### RED
- [ ] Write `tests/unit/dashboard/test_settings.py`:
  - A `project` fixture writes to `tmp_path / "proj"`:
    - a `.adw/project.yaml` modelled on this repo's (with comments; `git.base_branch: staging`; `task_manager` `type: linear`, `team_key: ADW`)
    - `commands/plan/config.yaml` with `enabled: false`
    - `commands/validate/config.yaml` with `lint_command: ruff check .`
    - `commands/ship/config.yaml` with `commands: {version_bump: ./update.sh}`
    - `commands/build/config.yaml` with `timeout_seconds: 1800`, which is invalid
    - no document file
  - A `client` fixture overrides `get_project_registry`, whose `get_all()` returns one entry named `proj` at that path, and `get_index_manager`, which returns no runs.
  - Context tests: values, nested dotted names, per-phase values and defaults, the invalid-phase error, the malformed and missing `project.yaml` cases, the three user-tier merge cases above, and the parametrized phase-specific-field case.
  - Route tests, parametrized over every tab key from `settings_context(...)["settings_tabs"]`: 200 in all three render modes, each tab's expected value in the body, and byte-identical `.adw` files and file set.
  - Empty states: no projects, no selection. An invalid `tab` falls back to the first tab. An unregistered project on the partial returns 404.
  - Carry over from `test_settings_route.py` only what still holds, in these tests: the full page against the HTMX partial, and the empty states. Drop its helper-function, `_SETTINGS_TABS`, nav-markup and task-manager-partial tests: their targets are deleted, or they are markup substrings (ADR-001).
- [ ] Run it and confirm it fails (`ModuleNotFoundError: adw.dashboard.settings`).

### GREEN
- [ ] Write `src/adw/dashboard/settings.py`. `settings_context(project_root, tab)` returns these keys:
  - `settings_tabs`: `[(key, label)]` for the sections, then `("phases", "Phases")`. The labels are "Basics" for `project`, "LLM" for `llm`, and a title-cased key otherwise.
  - `active_tab`: `tab` if valid, else the first tab
  - `sections`: `{key: rows}`
  - `phases`: `[{name, label, sources, error, rows}]`, where `sources` lists the files merged, each as `(tier, path)`
  - `config_error`: `str | None`, from `ConfigError`/`OSError` raised by `ConfigLoader(project_root).load()`
  - `has_project_file`: `ConfigLoader.has_project_config`

  Each row is `{name, lines, description}`. `_rows(model, prefix)` recurses into nested `BaseModel` values. `_lines` splits dicts and lists into one line per entry and shows `None` as `—`.

  `_phase` works as follows:
  - It resolves the tier. If the tier isn't `project` and has a `config.yaml`, it loads that file as the tier config.
  - It loads the project file, then starts from the project config, or from the model defaults when there is none.
  - It takes `enabled` from the tier unless the project file set it explicitly (`model_fields_set`), and merges `input_files` and `llm` key by key, project winning.
  - It catches `ConfigError`, `OSError`, `yaml.YAMLError` and `ValidationError`, and stores `str(e)` as the error.
- [ ] Point `routes.settings()` and `partials.settings_content()` at it, with a module-level `from adw.dashboard.settings import settings_context`.
- [ ] Rewrite `settings_content.html` and edit `settings.html` as listed above. Keep the bool badges (`true` → success, `false` → neutral) and the existing card and border classes, so the page keeps its look.
- [ ] Delete `tests/dashboard/test_settings_route.py` and `tests/dashboard/test_settings_indicators.py`.

### REFACTOR
- [ ] `uv run ruff format`; `scripts/preflight.sh`; `uv run pytest tests/unit/dashboard tests/dashboard -o addopts=""`.
- [ ] Check that `grep -n "settings-phase\|settings-section\|settings/save\|settings/phase" src/adw/dashboard/templates -r` returns nothing: no template links to an edit route.

## Notes

- `tests/dashboard/test_settings_save.py` and `test_settings_phase.py` still pass after this task. They exercise the save routes and `phase_config_partial`, which stay until TASK-002 and render their own templates.
- Build fixture configs with real files, not `MagicMock` configs, so the model-driven flattening runs against real Pydantic models.
