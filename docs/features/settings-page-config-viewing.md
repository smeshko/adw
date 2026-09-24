# Settings Page — Read-Only Config Viewer

**Date:** 2026-09-24
**Related Files:** `src/adw/dashboard/settings.py`, `src/adw/dashboard/routes.py`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/templates/partials/settings.html`, `src/adw/dashboard/templates/partials/settings_content.html`, `src/adw/dashboard/templates/base.html`

## Overview

The Settings page shows a registered project's effective ADW configuration. It never writes: to change a setting, edit `.adw/project.yaml` or `.adw/commands/<phase>/config.yaml`. The change takes effect on the next run.

Pick a project from the dropdown. The page then shows:

- **Basics**: the top-level `ProjectConfig` scalars (`name`, `language`, `test_command`, …)
- **one tab per nested config section**, such as Git, Worktree, Task Manager or LLM
- **Phases**: one card per phase with its effective values

## Technical Implementation

### Key Files

- `src/adw/dashboard/settings.py`: `settings_context(project_root, tab)` builds the whole template context. It returns `settings_tabs`, `active_tab`, `sections`, `phases`, `config_error` and `has_project_file`.
- `src/adw/dashboard/routes.py`: `GET /settings`. Returns the full page, or the `#settings` partial when the request has an `HX-Request` header.
- `src/adw/dashboard/partials.py`: `GET /partials/settings-content`. Returns the tab-content fragment that tab clicks swap into `#settings-content`. It answers 404 for a project that isn't registered.
- `src/adw/dashboard/templates/partials/settings.html`: the project selector, the read-only banner, the config error or "no `project.yaml`" note, the tabs and the empty states.
- `src/adw/dashboard/templates/partials/settings_content.html`: a `setting_rows` macro (name, values, description) and the Phases cards.

### How sections are built

`settings_context` loads the project with `ConfigLoader`. Without `.adw/project.yaml`, that gives the defaults detected for the project. It then flattens the model with `_rows()`:

- Top-level scalars go under Basics.
- Each nested model becomes its own tab.
- Deeper models get dotted names, such as `retry.max_retries` under LLM or `labels.prefix` under Task Manager.
- Dict and list values render one entry per line, and `None` renders as `—`.

The tabs come from the model, so a new `ProjectConfig` section shows up on the page with no dashboard change, and a deleted one disappears.

If `project.yaml` fails to load, the `ConfigError` text shows above the tabs, and only the Phases tab remains.

### How phase values are read

Each phase card shows the values a run would use. They are merged by `PhaseRunner`'s rules:

1. The phase is resolved with `CommandResolver`: project `.adw/commands/<phase>/`, then user `~/.adw/commands/<phase>/`, then bundled. A tier counts only if its directory holds `prompt.md`.
2. The resolved tier's `config.yaml` supplies `enabled`, `input_files` and `llm`.
3. The project's `.adw/commands/<phase>/config.yaml` overlays them:
   - `enabled` changes only when the project file sets it explicitly.
   - `input_files` and `llm` merge key by key, and the project wins.
4. The phase-specific fields come from the project file alone: validate's `lint_command`, document's `doc_mappings`, and ship's `commands`, `bypass_ci` and `wait_for_merge`.

Every file is validated with `get_config_class(phase)`, the model a run uses, and the card lists the files it merged. A file that fails to parse or validate shows its error in place of the values, because a run on that file fails the same way. An unset `llm.model` shows `—`: runs then pass no `--model`, and Claude Code uses its default.

## How to Use

1. Navigate to `/settings` or press `g s` from any page.
2. Select a project from the dropdown.
3. Click a tab to switch sections. `?tab=<key>` URLs are bookmarkable.
4. To change a value, edit the YAML file named in the banner or on the phase card.

## Notes

- The dashboard's only write routes are `POST /runs/start` and `POST /runs/{run_id}/abort`. `tests/unit/dashboard/test_settings.py` pins that set, and checks that browsing every settings tab leaves the `.adw` files byte-identical.
- `settings.py` copies `PhaseRunner`'s merge rules. Epic 02 phase 2.8 replaces both copies with one `load_command_config`.
