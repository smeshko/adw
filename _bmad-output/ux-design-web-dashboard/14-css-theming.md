# 14. CSS & Theming

## Theme Configuration

**Default theme:** DaisyUI `dark` theme.
**Alternative:** DaisyUI `light` theme.

```html
<html data-theme="dark">
```

Theme toggle persists via `localStorage`:
```html
<script>
  // Inline in <head> to prevent flash of wrong theme
  const theme = localStorage.getItem('adw-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', theme);
</script>
```

## Custom CSS Properties

Extend DaisyUI defaults for dashboard-specific styling:

```css
:root {
  /* Phase status colors */
  --phase-success: oklch(var(--su));
  --phase-error: oklch(var(--er));
  --phase-active: oklch(var(--wa));
  --phase-pending: oklch(var(--bc) / 0.2);

  /* Chart colors */
  --chart-primary: oklch(var(--p));
  --chart-primary-light: oklch(var(--p) / 0.4);

  /* Data density */
  --table-row-height: 2.25rem;
  --card-padding-compact: 0.75rem;
}
```

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

## Tailwind Configuration

Since we're using the Tailwind standalone CLI (no Node.js), the config is minimal:

```js
// tailwind.config.js
module.exports = {
  content: ["./templates/**/*.html"],
  plugins: [require("daisyui")],
  daisyui: {
    themes: ["dark", "light"],
    darkTheme: "dark",
  },
}
```

Build command:
```bash
./tailwindcss -i src/input.css -o static/css/output.css --minify
```

## Font Stack

DaisyUI defaults are used. No custom fonts to load — keeps page load fast.

For monospace contexts (`font-mono`), the browser's default monospace font is used (typically `Menlo`, `Monaco`, `Consolas`, or `Liberation Mono`).

---
