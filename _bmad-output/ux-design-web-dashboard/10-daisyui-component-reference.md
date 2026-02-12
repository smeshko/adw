# 10. DaisyUI Component Reference

Quick reference for the DaisyUI components used across the dashboard. All components are overridden by `brutalist-theme.css` via `[data-theme="brutalist-dark"]` selectors.

| Component | DaisyUI Class | Brutalist Override |
|-----------|--------------|-------------------|
| Stats row | `stats` (individual `.stat`) | `bg-card`, cream border, red offset shadow, hatching corner `::after`, hover lift |
| Card | `card card-bordered` | `bg-card`, cream border, red shadow, zero radius |
| Active run card | `card` + `border-l-4 border-warning` | 4px orange left border, orange shadow |
| Table | `table` in bordered card | `bg-header` header row, 3px red bottom border, cream header text, #2A2A2A row borders |
| Badge | `badge badge-{status}` | Outline only (transparent bg, 2px colored border), Azeret Mono 9px uppercase |
| Button primary | `btn btn-primary` | Transparent bg, cream border, cream text, red shadow-sm. Hover: red bg |
| Button danger | `btn btn-error` / `btn-danger` | Transparent bg, red border, red text. Hover: red bg, cream text |
| Button ghost | `btn btn-ghost` | text-secondary. Hover: bg-card-hover |
| Select | `select select-bordered` | Zero radius, cream border, bg-card. Focus: red border |
| Input | `input input-bordered` | Zero radius, cream border, bg-card. Focus: red outline |
| Tabs (analytics) | `tabs-box` | Zero radius, bg-surface, cream border. Active: red bg |
| Steps (pipeline) | `steps steps-horizontal` | Azeret Mono, tiny uppercase. success/warning after-colors |
| Join (pagination) | `join .btn` | Zero radius. Active: red bg, red border, cream text, shadow-sm |
| Progress | `progress` | Zero radius, 0.75rem height, #2A2A2A track |
| Alert | `alert` | Zero radius, 2px border |
| Loading | `loading` | Color: accent-red |
| Swap (theme) | `swap swap-rotate` | text-secondary |
| Modal | `modal` + `modal-box` | New run, abort confirmation, keyboard help overlay |

> **Note:** All custom properties and overrides live in `src/adw/dashboard/static/brutalist-theme.css`. Custom utilities: `.shadow-brutal`, `.shadow-brutal-hover`, `.shadow-brutal-sm`, `.font-display`, `.font-body`, `.uppercase-brutal`, `.section-header`, `.stripe-top/.stripe-bottom/.stripe-left`, `.border-brutal`, `.hatch-corner`.

---
