# Phase Config Editor

**Date:** 2026-02-13
**Related Files:** `src/adw/dashboard/partials.py`, `src/adw/dashboard/mutations.py`, `src/adw/dashboard/templates/partials/settings_phase_editor.html`, `src/adw/dashboard/templates/partials/settings_content.html`, `tests/dashboard/test_settings_phase.py`

## Overview

The Phase Config Editor replaces the read-only Phases tab on the Settings page with an interactive sub-tab editor for each of the 5 ADW phases (plan, build, validate, document, ship). Each phase has its own form with base fields (enabled, timeout, LLM model), optional input_files key-value pairs, and phase-specific sections (doc_mappings for document, commands/bypass_ci for ship). Configs save independently per phase to `.adw/commands/{phase}/config.yaml`.

## What Was Built

- Sub-tab navigation within the Phases tab — 5 phase tabs loaded via HTMX partials
- Phase editor form with base fields: enabled toggle, timeout_seconds number input, llm.model select
- Key-value pair editor for input_files (variable name to file path mappings)
- Document phase section: doc_mappings two-column editor (source_pattern + docs_dir)
- Ship phase section: version_bump command, publish command, bypass_ci toggle
- Per-phase save to `.adw/commands/{phase}/config.yaml` with directory auto-creation
- Disabled phase UI: opacity-50 dimmed fields when enabled toggle is off
- "Using defaults" indicator when no config file exists on disk
- Error preservation: validation errors re-render the form with submitted data intact

## Technical Implementation

### Key Files

- `src/adw/dashboard/partials.py:1282-1395`: `PHASE_DEFAULTS` constant and `phase_config_partial()` route — loads phase config from disk or falls back to defaults, builds template context with phase-specific fields
- `src/adw/dashboard/mutations.py:704-965`: `save_phase_settings()` route — parses form data including indexed key-value pairs, validates via phase-specific Pydantic model, writes YAML atomically; `_render_phase_editor_error()` preserves form on validation failure
- `src/adw/dashboard/templates/partials/settings_phase_editor.html`: Phase editor template with conditional sections, key-value editors, and inline JS for dynamic row management
- `src/adw/dashboard/templates/partials/settings_content.html:20-43`: Phase sub-tab navigation with HTMX-driven content loading
- `tests/dashboard/test_settings_phase.py`: 26 tests covering all phases, field types, validation, and save-reload flows

### Key Patterns

- **Sub-tab navigation with HTMX partial loading**: Each phase sub-tab fires `hx-get="/partials/settings-phase/{phase}?project={name}"` targeting `#phase-content`. The container auto-loads the first phase (plan) via `hx-trigger="load"`. This nests inside the existing settings tab system.

- **Per-phase config files (not project.yaml)**: Unlike other settings tabs that save to `.adw/project.yaml`, phase configs write to separate files at `.adw/commands/{phase}/config.yaml`. This uses `YAMLWithComments.generate_phase_yaml()` for comment-annotated output and `_atomic_write_config()` for crash-safe writes.

- **PHASE_DEFAULTS fallback**: When no config file exists, `PHASE_DEFAULTS` provides story-specified values (plan: 900s/opus, build: 1800s/sonnet, validate: 900s/opus, document: 900s/haiku, ship: 1200s/sonnet). The template shows a "Using defaults" note to indicate no file has been saved yet.

- **Two-column key-value editor**: Extends the single-column list editor from Security tab. Uses `<template id="tpl-input_files">` with two inputs per row. `addKVRow(id)` clones the template, `reindexKV(id)` renumbers both `_key.N` and `_val.N` fields. Same pattern used for doc_mappings.

- **Error preservation with form re-rendering**: `_render_phase_editor_error()` re-renders the phase editor template with the user's submitted data and an error toast, so the form is not lost on validation failure. This mirrors the `_render_settings_error()` pattern from the main settings save.

- **Phase-specific Pydantic validation**: `get_config_class(phase)` from `adw.commands.loader` resolves the correct model (e.g., `PlanConfig`, `DocumentConfig`, `ShipConfig`). The save endpoint validates the complete config dict against this model before writing.

### Code Examples

```python
# Loading phase config with fallback to defaults
from adw.dashboard.partials import PHASE_DEFAULTS

defaults = PHASE_DEFAULTS["plan"]  # {"timeout": 900, "model": "opus"}
```

```python
# Saving phase config via form data
# POST /settings/phase/plan/save
# Form fields:
#   enabled=true, timeout_seconds=1200, llm_model=opus
#   input_files_key.0=prd, input_files_val.0=docs/prd.md
#   input_files_key.1=arch, input_files_val.1=docs/architecture.md
```

```html
<!-- Sub-tab navigation pattern -->
<a class="tab tab-active"
   hx-get="/partials/settings-phase/plan?project={{ selected_settings_project | urlencode }}"
   hx-target="#phase-content"
   hx-swap="innerHTML">
  Plan
</a>
```

```javascript
// Two-column key-value row editor (~15 lines inline JS)
function addKVRow(id) {
  var tpl = document.getElementById('tpl-' + id);
  var list = document.getElementById('list-' + id);
  list.appendChild(tpl.content.cloneNode(true));
  reindexKV(id);
}
function reindexKV(id) {
  var rows = document.getElementById('list-' + id).querySelectorAll('.kv-row');
  rows.forEach(function(row, i) {
    row.querySelector('.kv-key').name = id + '_key.' + i;
    row.querySelector('.kv-val').name = id + '_val.' + i;
  });
}
```

## How to Use

1. Navigate to `/settings`, select a project, click the **Phases** tab
2. Five sub-tabs appear: Plan, Build, Validate, Document, Ship
3. Click a phase tab to load its editor (Plan loads by default)
4. Toggle **Enabled** on/off — disabled phases dim the remaining fields
5. Adjust **Timeout** (seconds) and **LLM Model** (opus/sonnet/haiku)
6. Add **Input Files** mappings: variable name (left) and file path (right)
7. For **Document** phase: add doc_mappings rows (source_pattern + docs_dir)
8. For **Ship** phase: set version_bump command, publish command, toggle bypass_ci
9. Click **Save** — config writes to `.adw/commands/{phase}/config.yaml`

## Configuration

| Field | Phases | Type | Default | Description |
|-------|--------|------|---------|-------------|
| enabled | All | toggle | true | Enable/disable phase execution |
| timeout_seconds | All | number | Phase-dependent | Max execution time (60-7200s) |
| llm.model | All | select | Phase-dependent | LLM model (opus/sonnet/haiku) |
| input_files | All | key-value | {} | Variable name to file path mappings |
| doc_mappings | Document | list of pairs | [] | source_pattern + docs_dir rows |
| commands.version_bump | Ship | text | "" | Shell command for version bumping |
| commands.publish | Ship | text | "" | Shell command for publishing |
| bypass_ci | Ship | toggle | false | Skip CI checks with --admin flag |

**Phase Defaults:**

| Phase | Timeout | Model |
|-------|---------|-------|
| Plan | 900s | opus |
| Build | 1800s | sonnet |
| Validate | 900s | opus |
| Document | 900s | haiku |
| Ship | 1200s | sonnet |

## Notes

- Each phase saves independently — saving Plan does not affect Build config
- Phase configs use separate files (`.adw/commands/{phase}/config.yaml`), not `project.yaml`
- The "Using defaults" note appears when no config file exists; saving creates the file
- Disabled phases show dimmed fields (opacity-50) but the toggle itself remains interactive
- Validation errors preserve the form with submitted data so the user can correct and re-save
- `YAMLWithComments` generates human-readable YAML with inline comments from schema metadata
- Tests use FastAPI dependency overrides with temp project directories, following the pattern from `test_settings_save.py`
