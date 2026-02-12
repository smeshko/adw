# 3. Global Elements

## 3.1 Header Bar

Persistent across all pages. Never swaps via HTMX. Sticky at top with `z-index: 100`.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ADW_DASHBOARD          Overview  Runs  Analytics  │  [project ▾] ☀ │
├═════════════════════════════════════════════════════════════════════┤
  ▲ 4px solid accent-red stripe
```

**Visual treatment:**
- Background: `--bg-header` (`#0A0A0A`) — the darkest surface.
- Height: `52px`.
- Bottom border: `4px solid var(--accent-red)` — the signature stripe accent.

**Components:**

| Element | Brutalist Style | Behavior |
|---------|----------------|----------|
| Logo | `ADW_DASHBOARD` — Azeret Mono 15px, weight 900, uppercase, 0.15em spacing. The underscore renders in `--accent-red`. | Links to `/` |
| Nav links | `btn btn-ghost btn-sm` — Azeret Mono 11px, weight 700, uppercase, 0.1em spacing. Color: `--text-muted`. | `hx-get="/{page}" hx-target="#main" hx-push-url` |
| Active nav | Active link gets `border-b-2 border-primary` (3px accent red underline) + `--accent-red` text color. | Managed via JS on `htmx:pushedIntoHistory` |
| Divider | 2px × 24px vertical bar in `#333`. Separates nav from controls. | Static |
| Project filter | `select select-bordered select-sm` — Azeret Mono 11px, weight 600, uppercase. Zero radius. `bg-card`, `border: 2px solid #444`. Focus: `border-color: accent-red`. | `hx-get` with `?project=` param |
| Theme toggle | `swap swap-rotate` with sun/moon SVGs. `btn btn-ghost btn-sm btn-circle`. Color: `--text-secondary`. | Toggles `data-theme` between `brutalist-dark` and `light`. Persists in `localStorage('adw-theme')`. |

**Active nav indicator:** Updated via `htmx:pushedIntoHistory` event. Maps URL path to `data-page` attribute on nav links.

**Project filter behavior:**
- Populated server-side from `ProjectRegistryManager`
- Selecting a project appends `?project={name}` to the current page URL
- All pages respect this filter — stats scope to that project, runs filter, analytics filter
- "All Projects" clears the filter
- On navigation, the filter's `hx-get` path updates to match the current page

## 3.2 Footer / Status Bar

Persistent. Updates out-of-band.

```
┌═════════════════════════════════════════════════════════════════════┐
  ▲ 4px solid accent-red stripe
├─────────────────────────────────────────────────────────────────────┤
│           Last updated 12s ago  ·  2 active runs  ·  ↻            │
└─────────────────────────────────────────────────────────────────────┘
```

**Visual treatment:**
- Background: `--bg-header` (`#0A0A0A`) — matches the navbar.
- Top border: `4px solid var(--accent-red)` — mirrors the header stripe.
- Font: Azeret Mono, 10px, weight 600, uppercase, 0.08em spacing.
- Text color: `--text-muted`.
- Timestamp value: `--accent-amber` (`font-mono`).

**HTMX:**
- `hx-get="/partials/status-bar" hx-trigger="every 10s" hx-target="#status-bar" hx-swap="outerHTML"`
- Refresh button: `btn btn-ghost btn-xs` — reloads current page content into `#main`.

**Hidden in Terminal Mode:** `body.terminal-mode-active #status-bar { display: none; }`.

## 3.3 Page Layout Template

```html
<html data-theme="brutalist-dark">
<head>
  <!-- DaisyUI + Tailwind CSS v4 (CDN) -->
  <!-- HTMX + SSE extension (vendored) -->
  <!-- brutalist-theme.css — DaisyUI theme overrides + custom properties -->
  <!-- dashboard.css — HTMX transitions, animations, terminal/focus mode -->
</head>
<body class="min-h-screen bg-base-200 flex flex-col">
  <header class="navbar">  <!-- 3.1 — never swaps -->
  <main id="main" class="container mx-auto p-4 flex-1">  <!-- all content swaps happen here -->
  <div id="modal-container"></div>  <!-- modals render here -->
  <footer id="status-bar" class="footer">  <!-- 3.2 — updates out-of-band -->
</body>
```

The `<main>` element is the sole HTMX swap target for navigation. Every page route returns either:
- Full HTML (if no `HX-Request` header) — wrapped in `base.html` for direct browser navigation / bookmarks
- Partial HTML fragment (if `HX-Request: true`) — just the `<main>` content for HTMX swaps

**CSS layering order:**
1. DaisyUI base CSS (CDN)
2. Tailwind CSS v4 browser build (CDN)
3. `brutalist-theme.css` — Custom DaisyUI theme + properties + utilities + component overrides
4. `dashboard.css` — HTMX transitions, animations, terminal/focus mode, dashboard-specific tokens

**Theme restoration:** An inline `<script>` in `<head>` reads `localStorage('adw-theme')` before paint to prevent flash-of-wrong-theme. Legacy `dark` values are migrated to `brutalist-dark`.

---
