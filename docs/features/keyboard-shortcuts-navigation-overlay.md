# Keyboard Shortcuts, Navigation & Overlay

**Date:** 2026-02-12
**Related Files:** `src/adw/dashboard/templates/base.html`, `src/adw/dashboard/templates/partials/keyboard_help.html`, `src/adw/dashboard/partials.py`, `src/adw/dashboard/static/dashboard.css`, `src/adw/dashboard/templates/partials/runs_table.html`, `src/adw/dashboard/templates/partials/recent_runs.html`

## Overview

Adds full keyboard-driven navigation to the ADW dashboard, including 11 shortcuts for page navigation, list traversal, modal triggers, and a `?`-activated help overlay. This enables efficient mouse-free usage of the dashboard with vim-style j/k navigation and two-key `g`-prefix sequences for page switching.

## What Was Built

- **Keyboard shortcut handler**: ~80-line inline IIFE in `base.html` with a `keydown` listener covering all 11 shortcuts
- **Two-key state machine**: `g h` / `g r` / `g a` sequences using a `pendingG` flag with 1-second auto-reset timeout
- **j/k list navigation**: Arrow key and vim-key navigation for any table row marked with `data-navigable-row`
- **Help overlay modal**: DaisyUI `<dialog>` partial at `/partials/keyboard-help` showing all shortcuts in a categorized grid with `kbd` badges
- **Focus highlight CSS**: `.kbd-nav-active` class using `oklch(var(--p))` outline for theme-compatible row highlighting

## Technical Implementation

### Key Files

- `src/adw/dashboard/templates/base.html`: Contains the keyboard shortcut IIFE script block (lines 162-301)
- `src/adw/dashboard/templates/partials/keyboard_help.html`: DaisyUI dialog modal with categorized shortcut grid
- `src/adw/dashboard/partials.py`: `GET /partials/keyboard-help` endpoint (lines 691-697)
- `src/adw/dashboard/static/dashboard.css`: `.kbd-nav-active` outline style (lines 39-43)
- `src/adw/dashboard/templates/partials/runs_table.html`: `data-navigable-row` on `<tr>` elements
- `src/adw/dashboard/templates/partials/recent_runs.html`: `data-navigable-row` on `<tr>` elements

### Key Patterns

- **Input guard pattern**: All shortcuts skip when `e.target.matches('input, textarea, select, [contenteditable]')` or when Ctrl/Meta/Alt modifiers are held. This prevents shortcuts from interfering with form input.

- **Modal guard pattern**: When a dialog is open (`#modal-container dialog[open]`), only `?` (toggle) and `Escape` (close) are permitted. All other shortcuts are suppressed.

- **g-prefix state machine**: A `pendingG` boolean flag is set on `g` keypress, with a `setTimeout` that auto-clears after 1 second. The next keypress checks `pendingG` and routes to the appropriate nav link via `.click()`.

- **data-navigable-row pattern**: Table rows that should be keyboard-navigable are marked with a `data-navigable-row` attribute. The keyboard handler queries `document.querySelectorAll('[data-navigable-row]')` to build the navigable row list. This decouples the keyboard logic from specific template structure.

- **Row selection reset**: The `selectedRowIndex` state resets to -1 on `htmx:afterSettle` when the target is `#main`, ensuring stale selection doesn't persist across page navigations.

### Code Examples

Adding `data-navigable-row` to a new table template:

```html
{% for item in items %}
<tr data-navigable-row
    hx-get="/items/{{ item.id }}"
    hx-target="#main"
    hx-push-url="/items/{{ item.id }}"
    class="hover cursor-pointer">
  <td>{{ item.name }}</td>
</tr>
{% endfor %}
```

The keyboard handler will automatically pick up these rows for j/k navigation and Enter to open.

## How to Use

1. **View shortcuts**: Press `?` to open the help overlay, press `?` again or `Esc` to close
2. **Navigate pages**: Press `g` then `h` (overview), `r` (runs), or `a` (analytics) within 1 second
3. **Browse lists**: Press `j`/`k` or arrow keys to move through table rows, `Enter` to open
4. **Quick actions**: Press `n` for new run modal, `/` to focus search, `r` to refresh
5. **Make tables navigable**: Add `data-navigable-row` attribute to `<tr>` elements with `hx-get` URLs

## Configuration

No configuration options. All shortcuts are hardcoded in the inline script. To add new shortcuts, modify the `keydown` handler in `base.html`.

## Notes

- The keyboard handler uses `var` declarations (not `let`/`const`) to match the existing codebase style
- The IIFE pattern prevents variable leakage to the global scope
- The `.kbd-nav-active` CSS class uses `outline` (not `border`) to avoid layout shift
- The `oklch(var(--p))` color value automatically adapts to both dark and light DaisyUI themes
- The `n` shortcut is restricted to `/` and `/runs` paths to avoid triggering on pages where new run doesn't apply
- Row highlight scrolls into view with `scrollIntoView({block: 'nearest'})` for long lists
