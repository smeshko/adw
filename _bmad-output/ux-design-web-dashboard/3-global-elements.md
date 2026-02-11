# 3. Global Elements

## 3.1 Header Bar

Persistent across all pages. Never swaps via HTMX.

```
┌─────────────────────────────────────────────────────────────┐
│  ◆ ADW          Overview  Runs  Analytics     [project ▾] ☀ │
└─────────────────────────────────────────────────────────────┘
```

**Components:**

| Element | DaisyUI | Behavior |
|---------|---------|----------|
| Logo + title | `text-lg font-bold` | Links to `/` |
| Nav links | `tabs` or plain links with `font-semibold` + active underline | `hx-get="/{page}" hx-target="#main" hx-push-url` |
| Project filter | `select select-bordered select-sm` | `hx-get` with `?project=` param, triggers full main content reload. "All Projects" as default option. |
| Theme toggle | `swap swap-rotate` (sun/moon icons) | Swaps `data-theme` on `<html>`. Persists choice in `localStorage` (tiny inline script). |

**Active nav indicator:** The current page link gets `tab-active` or an underline via `font-semibold border-b-2 border-primary`.

**Project filter behavior:**
- Populated server-side from `ProjectRegistryManager`
- Selecting a project appends `?project={name}` to the current page URL
- All pages respect this filter — stats scope to that project, runs filter, analytics filter
- "All Projects" clears the filter

## 3.2 Footer / Status Bar

Optional. Sits below `<main>`, updates out-of-band.

```
┌─────────────────────────────────────────────────────────────┐
│  Last updated 3s ago  ·  2 active runs  ·  ↻ Refresh       │
└─────────────────────────────────────────────────────────────┘
```

- `hx-trigger="every 10s"` to refresh the timestamp and active run count
- Manual refresh button: `hx-get` for the current page content
- Uses `hx-swap-oob="true"` to update without affecting the main content area

## 3.3 Page Layout Template

```html
<body data-theme="dark">
  <header>  <!-- 3.1 — never swaps -->
  <main id="main">  <!-- all content swaps happen here -->
  <footer id="status-bar">  <!-- 3.2 — updates out-of-band -->
</body>
```

The `<main>` element is the sole HTMX swap target for navigation. Every page route returns either:
- Full HTML (if no `HX-Request` header) — for direct browser navigation / bookmarks
- Partial HTML fragment (if `HX-Request: true`) — just the `<main>` content for HTMX swaps

This is handled server-side via a Jinja2 base template conditional.

---
