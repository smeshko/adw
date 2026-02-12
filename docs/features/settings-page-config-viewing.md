# Settings Page — Config Viewing

**Date:** 2026-02-12
**Related Files:** `src/adw/dashboard/routes.py`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/dependencies.py`, `src/adw/dashboard/templates/partials/settings.html`, `src/adw/dashboard/templates/partials/settings_content.html`

## Overview

The Settings page provides a read-only config viewer in the dashboard. Users select a project from a dropdown, and all configuration values from `.adw/project.yaml` are displayed in tabbed sections (Basics, Git, Worktree, LLM Retry, Task Manager, Security, Phases) with current values, defaults, descriptions, and change indicators.

## What Was Built

- Settings page route at `GET /settings` with dual-response pattern (full page vs HTMX partial)
- Settings content partial at `GET /partials/settings-content` for tab switching via HTMX
- Project selector that swaps settings content when a different project is chosen
- Config field rendering with label, current value, default value, description, type hint, and modified indicator
- Phase-specific settings tab with per-phase grouping
- Empty states for no projects registered and no project selected
- `g s` keyboard shortcut for navigation
- ConfigLoader and ConfigRegistry dependency injection providers

## Technical Implementation

### Key Files

- `src/adw/dashboard/routes.py:1674-1916`: Settings route handler, `build_settings_context()`, `_build_phase_settings()`, helper functions (`_humanize_field_name`, `_resolve_config_value`, `_format_display_value`), and `_SETTINGS_TABS` constant
- `src/adw/dashboard/partials.py:1141-1195`: Settings content partial route for HTMX tab switching
- `src/adw/dashboard/dependencies.py:169-191`: `get_config_loader()` and `get_config_registry()` DI providers
- `src/adw/dashboard/templates/partials/settings.html`: Main settings layout with project selector, info banner, tab navigation, and empty states
- `src/adw/dashboard/templates/partials/settings_content.html`: Tab content renderer for regular sections and phases
- `src/adw/dashboard/templates/base.html:60-66`: Nav link and `g s` shortcut wiring

### Key Patterns

- **Tab content switching via HTMX partial**: Tab clicks hit `GET /partials/settings-content?tab={key}&project={name}` and swap `#settings-content` innerHTML. The macro `tab_content_url()` in the template builds the URL with the correct tab and project params. This avoids full page reloads.

- **Config introspection via ConfigRegistry**: `build_settings_context()` iterates `ConfigRegistry.get_all_settings(section_key)` to discover all fields per section, then resolves current values from the `ProjectConfig` model via `_resolve_config_value()`. This means new config fields are automatically displayed without template changes.

- **Settings field display dict**: Each field is rendered as a dict with keys: `name`, `label`, `current_value`, `display_value`, `default_value`, `display_default`, `description`, `type_hint`, `is_changed`, `is_required`. The `is_changed` flag drives the accent dot indicator.

- **Project selector with HTMX swap**: The project dropdown uses `hx-get="/settings"` targeting `#settings` with `outerHTML` swap and `hx-push-url="true"`, so selecting a project reloads the entire settings partial while updating the URL.

### Code Examples

```python
# Building settings context for a section
from adw.config.registry import ConfigRegistry
from adw.dashboard.routes import build_settings_context

registry = ConfigRegistry()
sections = build_settings_context(config, registry)
# sections["git"] = [{"name": "branch_prefix", "label": "Branch Prefix", ...}, ...]
```

```html
<!-- HTMX tab switching pattern -->
<a class="tab {% if active_tab == tab_key %}tab-active{% endif %}"
   hx-get="/partials/settings-content?tab={{ tab_key }}&project={{ project }}"
   hx-target="#settings-content"
   hx-swap="innerHTML">{{ tab_label }}</a>
```

## How to Use

1. Navigate to `/settings` or press `g s` from any page
2. Select a project from the dropdown to load its configuration
3. Click tab buttons (Basics, Git, etc.) to switch between config sections
4. Fields with an accent dot have values that differ from defaults

## Configuration

The settings tabs are defined in `_SETTINGS_TABS` in `routes.py`:

| Tab Key | Label | Config Source |
|---------|-------|---------------|
| project | Basics | Top-level ProjectConfig attributes |
| git | Git | `config.git.*` |
| worktree | Worktree | `config.worktree.*` |
| llm | LLM Retry | `config.llm.*` |
| task_manager | Task Manager | `config.task_manager.*` |
| security | Security | `config.security.*` |
| phases | Phases | Phase-level settings via `ConfigRegistry.get_phase_settings()` |

## Notes

- Settings page is currently read-only — editing will be a future story
- The `ConfigRegistry` auto-discovers fields from Pydantic model metadata; adding new fields to `ProjectConfig` automatically surfaces them
- The info banner states "Configuration changes take effect on the next ADW run" — this is a static notice, not connected to any edit functionality yet
- Tests use FastAPI dependency overrides to mock `ProjectRegistryManager` and `IndexManager`
