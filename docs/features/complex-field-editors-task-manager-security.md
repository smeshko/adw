# Complex Field Editors — Task Manager & Security

**Date:** 2026-02-12
**Related Files:** `src/adw/dashboard/mutations.py`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/routes.py`, `src/adw/dashboard/templates/partials/settings_content.html`, `src/adw/dashboard/templates/partials/settings_task_manager_fields.html`, `src/adw/models/config.py`

## Overview

Specialized form editors for Task Manager integration and Security patterns on the Settings page. Task Manager uses a conditional HTMX partial (type=none hides fields, type=linear shows config + state mapping key-value editor). Security uses list editors with `<template>` cloning for blocked_commands and blocked_env_files. Cross-field validation enforces port range non-overlap and delay ordering constraints.

## What Was Built

- Task Manager tab with type select that swaps conditional fields via HTMX
- State mapping key-value editor (read-only phase keys, editable status text inputs) as `table table-sm`
- Security tab with list editors for blocked_commands (regex) and blocked_env_files (glob) patterns
- List editor with `<template>` cloning, `addRow()`, `reindex()` inline JS
- `build_complex_settings_context()` to provide structured data for custom templates
- `_collect_indexed_fields()` and `_collect_mapping_fields()` for complex form data parsing
- Cross-field validation (client-side JS + server-side Pydantic) for port overlap and delay ordering
- Server-side port range overlap validator in `WorktreeConfig`

## Technical Implementation

### Key Files

- `src/adw/dashboard/routes.py:1928-2003`: `build_complex_settings_context()` — builds `task_manager_context` and `security_context` dicts from ProjectConfig, with defaults for unset values
- `src/adw/dashboard/partials.py:1141-1215`: `task_manager_fields()` — conditional partial route at `GET /partials/settings-section/task-manager` that renders fields or helper text based on type param
- `src/adw/dashboard/mutations.py:382-431`: `_collect_indexed_fields()` and `_collect_mapping_fields()` — extract indexed list fields (`prefix.0`, `prefix.1`) and dot-keyed mapping fields (`prefix.plan`, `prefix.build`) from form data
- `src/adw/dashboard/mutations.py:560-603`: Complex field handling in save — state_mapping collection for task_manager, blocked_patterns metadata preservation and blocked_env_files collection for security
- `src/adw/dashboard/templates/partials/settings_content.html:49-181`: Task Manager and Security custom tab layouts with forms
- `src/adw/dashboard/templates/partials/settings_task_manager_fields.html`: HTMX conditional partial template with toggle fields and state mapping table
- `src/adw/models/config.py:319-330`: Port range overlap validation in WorktreeConfig model validator

### Key Patterns

- **HTMX conditional partial swap**: The Task Manager type `<select>` has `hx-get="/partials/settings-section/task-manager"` with `hx-target="#task-manager-fields"`. Changing the type swaps the content of the container — `none` shows helper text, `linear` shows all config fields and state mapping editor. The `hx-vals` attribute passes the current project so the partial can load existing config values.

- **List editor with template cloning**: Security blocked patterns use a `<template>` element containing the row markup. `addRow(id)` clones the template content and appends it to the list container. `reindex(id)` renumbers all `name` attributes (`id.0`, `id.1`, ...) so the server receives correctly indexed fields. This is ~10 lines of inline JS.

- **Indexed field collection**: `_collect_indexed_fields(form, prefix)` scans FormData for keys matching `prefix.N`, extracts the integer index, sorts by index, and returns non-empty values as an ordered list. Used for security list fields.

- **Mapping field collection**: `_collect_mapping_fields(form, prefix)` scans FormData for keys matching `prefix.key`, returns a dict of `{key: value}`. Used for state_mapping.

- **Blocked pattern metadata preservation**: When saving security blocked_commands, the save endpoint builds a lookup from existing `blocked_patterns` entries (which have `description`, `severity`, `category` metadata). Unchanged pattern strings keep their original metadata; new patterns get defaults.

- **Cross-field validation**: Client-side JS defines `crossRules` array with `fields` (trigger inputs), `target` (where to show error), and `check` function. The `validate()` function runs applicable cross-rules after per-field validation passes. Server-side, `WorktreeConfig` validates port range non-overlap in its Pydantic model validator.

### Code Examples

```python
# Collecting indexed list fields from form data
from adw.dashboard.mutations import _collect_indexed_fields

# Form data: {"blocked_commands.0": "rm\\s+-rf", "blocked_commands.1": "DROP TABLE"}
patterns = _collect_indexed_fields(form, "blocked_commands")
# Result: ["rm\\s+-rf", "DROP TABLE"]
```

```python
# Collecting mapping fields from form data
from adw.dashboard.mutations import _collect_mapping_fields

# Form data: {"state_mapping.plan": "Todo", "state_mapping.build": "In Progress"}
mapping = _collect_mapping_fields(form, "state_mapping")
# Result: {"plan": "Todo", "build": "In Progress"}
```

```javascript
// List editor inline JS pattern (~10 lines)
function addRow(id) {
  var tpl = document.getElementById('tpl-' + id);
  var list = document.getElementById('list-' + id);
  var clone = tpl.content.cloneNode(true);
  list.appendChild(clone);
  reindex(id);
}
function reindex(id) {
  var list = document.getElementById('list-' + id);
  list.querySelectorAll('input[type="text"]').forEach(function(input, i) {
    input.name = id + '.' + i;
  });
}
```

## How to Use

1. Navigate to `/settings`, select a project, click the **Task Manager** tab
2. Change the **Type** dropdown from `none` to `linear` — config fields appear via HTMX swap
3. Fill in team_key (2-10 uppercase letters), toggle sync_comments/auto_close/labels_enabled
4. Edit state mapping status values (phase keys are read-only)
5. Click **Save** to persist
6. For **Security** tab: add/remove blocked command patterns and env file patterns using list editors
7. Click **+ Add Pattern** to add rows, click the X button to remove rows

## Configuration

| Field | Section | Type | Default | Description |
|-------|---------|------|---------|-------------|
| type | task_manager | select | none | Integration type (none/linear) |
| team_key | task_manager | text | "" | Team prefix for ID detection (2-10 uppercase) |
| sync_comments | task_manager | toggle | false | Post comments on status transitions |
| auto_close | task_manager | toggle | false | Close task when PR is merged |
| labels_enabled | task_manager | toggle | true | Enable label management |
| label_prefix | task_manager | text | "adw:" | Prefix for ADW-managed labels |
| state_mapping.* | task_manager | key-value | phase defaults | Map ADW phases to task statuses |
| blocked_commands | security | list | [] | Regex patterns for commands to block |
| blocked_env_files | security | list | [] | Glob patterns for env files to block |

## Notes

- Task Manager fields are conditionally rendered — only visible when type is not `none`
- The state mapping editor always shows all 6 phases (plan, build, validate, document, ship, failed) with read-only keys
- Security blocked_patterns are stored as structured objects with metadata (description, severity, category); the editor only exposes the pattern string but preserves metadata on save
- Cross-field validation runs on blur for both the source and target fields
- Port range overlap validation uses a concurrent ports count of 15 per range
- Empty list entries are filtered out on save (empty strings discarded by `_collect_indexed_fields`)
- Empty state_mapping values are filtered out on save to avoid storing blank statuses
