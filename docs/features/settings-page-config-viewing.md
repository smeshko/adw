# Settings Page — Config Viewing & Editing

**Date:** 2026-02-12
**Related Files:** `src/adw/dashboard/routes.py`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/mutations.py`, `src/adw/dashboard/dependencies.py`, `src/adw/dashboard/templates/partials/settings.html`, `src/adw/dashboard/templates/partials/settings_content.html`, `src/adw/dashboard/templates/partials/toast.html`, `src/adw/dashboard/templates/base.html`

## Overview

The Settings page provides a config viewer and editor in the dashboard. Users select a project from a dropdown, and all configuration values from `.adw/project.yaml` are displayed in tabbed sections (Basics, Git, Worktree, LLM Retry, Task Manager, Security, Phases). Editable sections (Basics, Git, Worktree/Ports, LLM Retry) render form controls; other sections remain read-only. Changes are saved per-section with Pydantic validation and atomic file writes.

## What Was Built

### Story 7.1: Config Viewing (Scaffold)
- Settings page route at `GET /settings` with dual-response pattern (full page vs HTMX partial)
- Settings content partial at `GET /partials/settings-content` for tab switching via HTMX
- Project selector that swaps settings content when a different project is chosen
- Config field rendering with label, current value, default value, description, type hint, and modified indicator
- Phase-specific settings tab with per-phase grouping
- Empty states for no projects registered and no project selected
- `g s` keyboard shortcut for navigation
- ConfigLoader and ConfigRegistry dependency injection providers

### Story 7.2: Settings Editing & Save Infrastructure
- Editable form controls for Basics (language select, platform select, text inputs), Git (text inputs, toggle), Worktree/Ports (number inputs), and LLM Retry (number inputs) sections
- `POST /settings/save` mutation endpoint with CSRF validation
- Section-specific field mapping from flat form names to nested config paths
- Load-merge-validate-write pattern: loads existing YAML, deep-merges form values, validates via Pydantic, writes atomically
- Client-side validation on blur (range checks, pattern matching, save button disable)
- Toast notification system via HTMX OOB swap (success/error, auto-dismiss after 3s)
- Creates `.adw/` directory and `project.yaml` if they don't exist

### Story 7.3: Complex Field Editors (Task Manager & Security)
- Task Manager tab with type select (none/linear), HTMX conditional partial swap, team_key, sync_comments, auto_close, labels_enabled, label_prefix fields
- State mapping key-value editor (read-only phase keys, editable status values) rendered as `table table-sm`
- Security tab with list editors for blocked_commands (regex patterns) and blocked_env_files (glob patterns)
- List editor with `<template>` cloning and `addRow()`/`reindex()` inline JS (~10 lines)
- Cross-field validation: client-side + server-side for max_delay >= base_delay and port range overlap
- `build_complex_settings_context()` provides structured data for Task Manager and Security templates
- `_collect_indexed_fields()` and `_collect_mapping_fields()` helpers for complex form data collection
- Server-side port overlap validator in `WorktreeConfig` Pydantic model

## Technical Implementation

### Key Files

- `src/adw/dashboard/routes.py:1674-2006`: Settings route handler, `build_settings_context()`, `_build_phase_settings()`, `build_complex_settings_context()`, helper functions (`_humanize_field_name`, `_resolve_config_value`, `_format_display_value`), and `_SETTINGS_TABS` constant. Extended to include port_range and retry settings in their parent sections.
- `src/adw/dashboard/partials.py:1141-1216`: Settings content partial route for HTMX tab switching. Task Manager conditional partial route at `GET /partials/settings-section/task-manager`. Includes CSRF token in context.
- `src/adw/dashboard/mutations.py:308-end`: `POST /settings/save` endpoint with `_SECTION_FIELD_MAP`, `_parse_form_value()`, `_collect_indexed_fields()`, `_collect_mapping_fields()`, `_deep_set()`, `_atomic_write_config()`, and `_render_settings_error()`.
- `src/adw/dashboard/dependencies.py:169-191`: `get_config_loader()` and `get_config_registry()` DI providers
- `src/adw/dashboard/templates/partials/settings.html`: Main settings layout with project selector, info banner, tab navigation, and empty states
- `src/adw/dashboard/templates/partials/settings_content.html`: Tab content renderer — editable form for supported sections, read-only display for others. Includes client-side validation script and cross-field validation. Custom layouts for Task Manager and Security tabs.
- `src/adw/dashboard/templates/partials/settings_task_manager_fields.html`: HTMX conditional partial for Task Manager fields (type-dependent rendering, state mapping editor)
- `src/adw/dashboard/templates/partials/toast.html`: Reusable toast notification partial for OOB swaps
- `src/adw/dashboard/templates/base.html:60-66,109`: Nav link, `g s` shortcut wiring, and `#toast-container` for OOB toast swaps
- `src/adw/config/registry.py:114`: Added `retry` section for RetryConfig settings extraction
- `src/adw/models/config.py`: Port range overlap validator in `WorktreeConfig`
- `tests/dashboard/test_settings_save.py`: 64 tests for the save endpoint (20 new for Task Manager/Security)
- `tests/dashboard/test_settings_route.py`: 4 new tests for Task Manager conditional partial
- `tests/unit/models/test_config.py`: 3 new tests for cross-field validation

### Key Patterns

- **Tab content switching via HTMX partial**: Tab clicks hit `GET /partials/settings-content?tab={key}&project={name}` and swap `#settings-content` innerHTML. This avoids full page reloads.

- **Config introspection via ConfigRegistry**: `build_settings_context()` iterates `ConfigRegistry.get_all_settings(section_key)` to discover all fields per section, then resolves current values from the `ProjectConfig` model via `_resolve_config_value()`. For the worktree section, port_range settings are also included; for the llm section, retry settings are included.

- **Section-scoped saves**: Each editable tab wraps its fields in a `<form>` with `hx-post="/settings/save"`. Hidden fields identify the section (`_section`) and project (`_project`). The save endpoint only modifies fields for the submitted section, preserving all other config values.

- **Field mapping**: `_SECTION_FIELD_MAP` maps flat form field names to nested config dict paths. For example, `"branch_prefix"` in the git section maps to `["git", "branch_prefix"]`, and `"max_retries"` in the llm section maps to `["llm", "retry", "max_retries"]`.

- **Load-merge-validate-write**: The save endpoint loads existing `project.yaml` as a raw dict via `yaml.safe_load()`, deep-merges the submitted field values using `_deep_set()`, validates the complete merged dict via `ProjectConfig.model_validate()`, and writes the result atomically using temp file + fsync + rename.

- **Toast via OOB swap**: The save response appends `<div id="toast-container" hx-swap-oob="innerHTML">` alongside the main content HTML. This updates both the form content and the toast container in a single response. The toast auto-dismisses via `setTimeout`.

- **Client-side validation**: An inline `<script>` validates fields on blur events, showing `text-error text-xs` messages below inputs and disabling the save button when errors exist. This is convenience-only; Pydantic server-side validation is the security boundary.

### Editable Sections and Controls

| Section | Field | Control Type | Validation |
|---------|-------|-------------|------------|
| project | language | `<select>` | Required |
| project | platform | `<select>` | Required |
| project | test_command | `<input type="text">` | Optional |
| project | build_command | `<input type="text">` | Optional |
| git | branch_prefix | `<input type="text">` | Must end with `/` |
| git | skip_hooks | `<input type="checkbox">` (toggle) | Boolean |
| git | base_branch | `<input type="text">` | Optional |
| worktree | backend_start | `<input type="number">` | 1–65535 |
| worktree | frontend_start | `<input type="number">` | 1–65535 |
| llm | max_retries | `<input type="number">` | 1–10 |
| llm | base_delay_seconds | `<input type="number">` | 0.1–300 |
| llm | max_delay_seconds | `<input type="number">` | 0.1–300 |
| llm | multiplier | `<input type="number">` | >1.0, ≤5.0 |

### Code Examples

```python
# Building settings context for a section (now includes port/retry fields)
from adw.config.registry import ConfigRegistry
from adw.dashboard.routes import build_settings_context

registry = ConfigRegistry()
sections = build_settings_context(config, registry)
# sections["worktree"] now includes backend_start, frontend_start
# sections["llm"] now includes max_retries, base_delay_seconds, etc.
```

```python
# Save endpoint field mapping
from adw.dashboard.mutations import _SECTION_FIELD_MAP

# Git section maps flat form names to nested config paths
_SECTION_FIELD_MAP["git"]
# {'branch_prefix': ['git', 'branch_prefix'],
#  'skip_hooks': ['git', 'skip_hooks'],
#  'base_branch': ['git', 'base_branch']}
```

```html
<!-- HTMX form save pattern -->
<form hx-post="/settings/save"
      hx-target="#settings-content"
      hx-swap="innerHTML">
  <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
  <input type="hidden" name="_section" value="{{ active_tab }}">
  <input type="hidden" name="_project" value="{{ selected_settings_project }}">
  <!-- form fields -->
  <button type="submit" class="btn btn-primary btn-sm">Save</button>
</form>
```

## How to Use

1. Navigate to `/settings` or press `g s` from any page
2. Select a project from the dropdown to load its configuration
3. Click tab buttons (Basics, Git, etc.) to switch between config sections
4. Fields with an accent dot have values that differ from defaults
5. On editable tabs (Basics, Git, Worktree, LLM Retry), modify field values
6. Client-side validation runs on blur — fix any red error messages
7. Click Save to persist changes to `project.yaml`
8. A toast notification confirms success or shows validation errors

## Configuration

The settings tabs are defined in `_SETTINGS_TABS` in `routes.py`:

| Tab Key | Label | Config Source | Editable |
|---------|-------|---------------|----------|
| project | Basics | Top-level ProjectConfig attributes | Yes |
| git | Git | `config.git.*` | Yes |
| worktree | Worktree | `config.worktree.*` + `config.worktree.port_range.*` | Ports only |
| llm | LLM Retry | `config.llm.*` + `config.llm.retry.*` | Retry only |
| task_manager | Task Manager | `config.task_manager.*` | Yes (custom editor) |
| security | Security | `config.security.*` | Yes (list editors) |
| phases | Phases | Phase-level settings via `ConfigRegistry.get_phase_settings()` | No |

## Notes

- Editing is section-scoped: saving one section preserves all other sections' values
- The `ConfigRegistry` auto-discovers fields from Pydantic model metadata; adding new fields to `ProjectConfig` automatically surfaces them in the read-only display
- Client-side validation is convenience-only; Pydantic server-side validation is authoritative
- The info banner states "Configuration changes take effect on the next ADW run"
- If no `.adw/project.yaml` exists, saving creates the directory and file
- Tests use FastAPI dependency overrides to mock `ProjectRegistryManager` and `IndexManager`
