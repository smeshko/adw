# 13. Keyboard Shortcuts

**PRD FR36:** Keyboard navigation with shortcut overlay.

## Shortcut Map

| Key | Action | Context |
|-----|--------|---------|
| `?` | Toggle shortcut overlay | Global |
| `g h` | Go to Overview (home) | Global |
| `g r` | Go to Runs List | Global |
| `g a` | Go to Analytics | Global |
| `n` | Open New Run modal | Overview, Runs List |
| `j` / `↓` | Next item in list | Runs List, Overview recent runs |
| `k` / `↑` | Previous item in list | Runs List, Overview recent runs |
| `Enter` | Open selected run | Runs List, Overview recent runs |
| `Esc` | Close modal / go back | Modals, detail pages |
| `/` | Focus search input | Runs List (filter), Log viewer |
| `r` | Refresh | Global |

## Implementation Note

Keyboard shortcuts require a small amount of JavaScript (~30 lines). This is the one area where inline JS is acceptable. Implementation approach:

```html
<script>
document.addEventListener('keydown', (e) => {
  // Skip if user is typing in an input/textarea
  if (e.target.matches('input, textarea, select')) return;
  // Handle shortcuts...
});
</script>
```

## Shortcut Overlay

Triggered by `?`. A modal listing all available shortcuts in a two-column layout.

**DaisyUI:** `modal` with a grid of `kbd` badges:
```html
<kbd class="kbd kbd-sm">g h</kbd> <span>Go to Overview</span>
```

---
