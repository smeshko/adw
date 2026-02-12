# 14. CSS & Theming

## Theme Configuration

**Default theme:** `brutalist-dark` (custom DaisyUI theme defined in `brutalist-theme.css`).
**Alternative:** DaisyUI built-in `light` theme.

Theme toggle: `data-theme` attribute on `<html>`. Persisted in `localStorage('adw-theme')`. Inline script in `<head>` restores before paint. Legacy `dark` values migrated to `brutalist-dark`.

```html
<html data-theme="brutalist-dark">
```

```html
<script>
  // Inline in <head> to prevent flash of wrong theme
  let theme = localStorage.getItem('adw-theme') || 'brutalist-dark';
  if (theme === 'dark') theme = 'brutalist-dark'; // migrate legacy
  document.documentElement.setAttribute('data-theme', theme);
</script>
```

## Custom CSS Properties (in `[data-theme="brutalist-dark"]`)

### DaisyUI Semantic Overrides

- `--color-base-100/200/300`, `--color-primary/secondary/accent/neutral`
- `--color-success/warning/error/info` with `-content` variants
- `--radius-*: 0` (all radiuses zero)
- `--border: 2px`
- `--depth-1/2` for DaisyUI shadow tokens

### Brutalist Custom Tokens

- `--bg-void/surface/card/card-hover/header`
- `--border-color`, `--text-primary/secondary/muted`
- `--accent-red/orange/green/amber/cream`
- `--shadow-brutal/brutal-hover/brutal-sm`
- `--stripe-accent`
- `--font-display`, `--font-body`
- `--heat-0` through `--heat-4`
- `--noise-opacity`

## CSS-Only Animations

```css
/* Active run phase pulse */
@keyframes phase-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.phase-active {
  animation: phase-pulse 2s ease-in-out infinite;
}

/* Smooth content swap transitions */
.htmx-swapping {
  opacity: 0;
  transition: opacity 100ms ease-out;
}
.htmx-settling {
  opacity: 1;
  transition: opacity 200ms ease-in;
}
```

`prefers-reduced-motion` disables transforms.

## Font Stack

- **Display:** `'Azeret Mono', ui-monospace, monospace`
- **Body:** `'Inconsolata', ui-monospace, monospace`
- Loaded via Google Fonts CDN with `preconnect`

All-monospace reinforces the developer-native feel. Azeret Mono provides visual weight for labels and headings while Inconsolata handles readability for data.

## Build Approach

No Tailwind build step. Using Tailwind CSS v4 browser build (CDN) + DaisyUI CDN. Custom theme applied via `brutalist-theme.css` loaded after CDN.

```
CDN: Tailwind CSS v4 browser build
CDN: DaisyUI
Local: src/adw/dashboard/static/brutalist-theme.css
```

## Scrollbar Styling

Custom scrollbars in brutalist theme:
- Width: 8px
- Track: `bg-void`
- Thumb: `#333` with 1px red border

---
