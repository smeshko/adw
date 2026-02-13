# Reset to Defaults, Changed Indicators & Validation Polish

**Date:** 2026-02-13
**Related Files:** `src/adw/dashboard/routes.py`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/mutations.py`, `src/adw/dashboard/templates/partials/settings.html`, `src/adw/dashboard/templates/partials/settings_content.html`, `tests/dashboard/test_settings_indicators.py`

## Overview

This feature adds visual feedback for settings that differ from their defaults, provides a one-click reset button to restore defaults, and completes inline validation for all editable fields. Tab labels show a count badge when fields in that section differ from defaults. Each editable field has an accent dot indicator, a reset (↺) button, and a "Default: {value}" hint. Validation is enhanced with required field checks and port upper bound cross-field rules.

## What Was Built

- Changed-count badges on tab labels: e.g. "Git (2)" when 2 git fields differ from defaults
- Accent dot indicator (●) next to changed field labels — toggles dynamically via JS
- Reset (↺) button next to changed field labels — restores field to its `data-default` value client-side
- "Default: {value}" hint shown below all editable fields (always visible, not just when changed)
- Required field validation for `language` and `platform` selects
- Port + max_concurrent upper bound validation: `port + 15 - 1 <= 65535`
- `change` event triggers on text/number inputs (in addition to existing `blur`)
- `updateIndicators()` JS function that keeps accent dots and reset buttons in sync on every edit

## Technical Implementation

### Key Files

- `src/adw/dashboard/routes.py:1892-1940`: `compute_changed_counts()` — computes per-section count of fields differing from defaults, including task_manager and security complex sections
- `src/adw/dashboard/routes.py:2098-2103`: `changed_counts` added to settings route context
- `src/adw/dashboard/partials.py:1278-1282`: `changed_counts` added to settings content partial context
- `src/adw/dashboard/mutations.py:672-679`: `changed_counts` added to save success context
- `src/adw/dashboard/mutations.py:1035-1042`: `changed_counts` added to save error context
- `src/adw/dashboard/templates/partials/settings.html:57-62`: Tab badge rendering with `{% if changed_counts.get(tab_key, 0) > 0 %}`
- `src/adw/dashboard/templates/partials/settings_content.html:202-212`: Accent dot with `id="dot-{name}"` and reset button with `id="reset-{name}"`, both conditionally hidden
- `src/adw/dashboard/templates/partials/settings_content.html:432-475`: `updateIndicators()` and `resetField()` JS functions
- `tests/dashboard/test_settings_indicators.py`: 19 tests covering unit and integration scenarios

### Key Patterns

- **Server-side tab count computation**: `compute_changed_counts()` takes `settings_sections` (from `build_settings_context()`), `task_manager_context`, and `security_context` and returns a `dict[str, int]`. Standard sections count `is_changed` flags. Task manager compares 6 fields against known defaults. Security checks for non-empty blocked lists.

- **Dynamic client-side indicators**: The accent dot and reset button are rendered in the DOM with `hidden` class when value matches default. `updateIndicators(input)` reads `input.dataset.default`, compares to current value (with checkbox special-case: `input.checked.toString()` vs `"true"/"false"`), and toggles visibility. This runs on `blur`, `change`, and page load.

- **Reset is client-side only**: `resetField(input)` sets `input.value = input.dataset.default` (or `input.checked` for checkboxes), then dispatches a synthetic `change` event. This triggers `updateIndicators` and `validate` for immediate feedback. The change is NOT persisted until the user clicks Save.

- **Required field validation**: Added `language` and `platform` to the `rules` object with `function(v) { return !v || !v.trim() ? 'This field is required' : ''; }`. These fire on `change` for select elements.

- **Port upper bound cross-rules**: Two new entries in `crossRules` check `port + 15 - 1 > 65535` for both `backend_start` and `frontend_start` independently. Error message: "Port + 15 concurrent exceeds 65535".

### Code Examples

```python
# Computing changed counts for tab badges
from adw.dashboard.routes import compute_changed_counts

counts = compute_changed_counts(
    settings_sections,  # from build_settings_context()
    complex_ctx["task_manager_context"],
    complex_ctx["security_context"],
)
# counts = {"project": 2, "git": 1, "worktree": 0, ...}
```

```javascript
// Client-side indicator update
function updateIndicators(input) {
  var name = input.name;
  var dot = document.getElementById('dot-' + name);
  var resetBtn = document.getElementById('reset-' + name);
  var defaultVal = input.dataset.default;
  var currentVal = input.type === 'checkbox'
    ? input.checked.toString()
    : input.value;
  var changed = currentVal !== defaultVal;
  dot.classList.toggle('hidden', !changed);
  resetBtn.classList.toggle('hidden', !changed);
}
```

### Configuration Table

| Element | ID Pattern | Visibility | Purpose |
|---------|-----------|------------|---------|
| Accent dot | `dot-{field_name}` | Shown when changed | Visual indicator |
| Reset button | `reset-{field_name}` | Shown when changed | Restore default |
| Default hint | `default-hint-{field_name}` | Always shown | Show default value |
| Error span | `error-{field_name}` | Shown on validation error | Error message |

## Testing

19 tests in `tests/dashboard/test_settings_indicators.py`:

- **TestComputeChangedCounts** (5 tests): Unit tests for `compute_changed_counts()` — empty sections, standard sections with changed flags, task manager changed fields, security non-empty lists
- **TestIsChangedFlags** (3 tests): Verify `build_settings_context()` sets `is_changed` correctly for default config, changed config, and None config
- **TestTabBadgesInHTML** (3 tests): Integration tests asserting badge presence/absence and correct count in rendered HTML
- **TestIndicatorsInHTML** (5 tests): Integration tests for accent dot visibility, reset button visibility, and default hint display
- **TestComplexSectionCounts** (3 tests): Task manager type changed, security blocked commands, all-defaults zero counts
