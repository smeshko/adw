# 13. Keyboard Shortcuts

**PRD FR36:** Keyboard navigation with shortcut overlay.

## Shortcut Map

| Key | Action | Context |
|-----|--------|---------|
| `?` | Toggle keyboard help overlay | Global |
| `g h` | Navigate to Overview | Global |
| `g r` | Navigate to Runs | Global |
| `g a` | Navigate to Analytics | Global |
| `n` | Open New Run modal | Overview, Runs |
| `j` / `ArrowDown` | Next row | Tables with `data-navigable-row` |
| `k` / `ArrowUp` | Previous row | Tables with `data-navigable-row` |
| `Enter` | Open selected row | Tables with `data-navigable-row` |
| `/` | Focus search input | Pages with search |
| `r` | Refresh current page | Global |
| `t` | Toggle Terminal Mode | Run Detail |
| `f` | Toggle Focus Mode | Run Detail (active runs) |
| `Escape` | Close modal / exit mode / go back | Global |

## Implementation Note

The keyboard system is ~250 lines in `base.html`. It supports g-prefix chord sequences with a 1-second timeout, skips form inputs (`input`, `textarea`, `select`), skips when modifier keys are held (except Shift for `?`), manages terminal/focus mode flags, and resets `selectedRowIndex` on HTMX swap.

The `?` shortcut loads the keyboard help overlay via:
```javascript
htmx.ajax('GET', '/partials/keyboard-help', {target: '#modal-container'});
```

## Shortcut Overlay

Triggered by `?`. A modal listing all available shortcuts in a two-column layout, loaded as an HTMX partial.

**DaisyUI:** `modal` with a grid of `kbd` badges:
```html
<kbd class="kbd kbd-sm">g h</kbd> <span>Navigate to Overview</span>
```

---
