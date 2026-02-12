# 1. Design Philosophy

## Visual Identity: Industrial Brutalist Dark

The dashboard embodies **Industrial Brutalism** — a visual language that mirrors the raw, deterministic nature of the tool itself. No rounded corners, no soft gradients, no apologies. Every surface is a slab of charcoal steel. Cream borders cut harsh against the void. Red offset shadows telegraph depth like welded plate steel. The aesthetic says: _this tool builds things, and it doesn't pretend to be friendly — it's effective._

## Guiding Principles

- **Hub-and-spoke navigation** — The overview is a hub. Every section is a compact preview of a full page. Users drill down, not across.
- **Information density without clutter** — Use progressive disclosure. Show summaries first, expand on demand.
- **Raw utilitarian power** — Monospace everywhere, high contrast, dark default, zero-radius, uppercase authority. No decorative flourishes beyond the intentional brutalist vocabulary (hatching, noise, offset shadows).
- **Server-driven interactivity** — All interactions go through HTMX. No client-side state. URLs are always bookmarkable.
- **Consistent status language** — The same colors, icons, and labels for run status everywhere: overview, detail, list.
- **Zero border-radius** — No rounded corners on any element. Every rectangle is sharp.
- **Offset shadows signal depth** — Hard-edged `4px 4px 0` shadows in accent red, never blurred. Hover grows to 6px with element lift.
- **Noise texture adds grain** — Subtle SVG fractal noise at 3% opacity across the entire viewport adds industrial film-grain.

## Design Vocabulary

| Status | Accent Color | Icon | Badge Style |
|--------|-------------|------|-------------|
| Running | `--accent-orange` (`#D4602A`) | `●` (pulsing) | Outline orange: `badge-warning` |
| Completed | `--accent-green` (`#2ECC40`) | `✓` | Outline green: `badge-success` |
| Failed | `--accent-red` (`#C43018`) | `✗` | Outline red: `badge-error` |
| Aborted | `--text-muted` (`#666`) | `⦻` | Outline gray: `badge-ghost` |

All badges are **outline style** — transparent background with 2px colored border. Zero radius, display font, 9px uppercase.

## Color Palette

### Background Scale (Dark to Darker)

| Token | Hex | DaisyUI Mapping | Usage |
|-------|-----|-----------------|-------|
| `--bg-void` | `#111111` | `base-300` | Page background, deepest surface |
| `--bg-surface` | `#181818` | `base-200` | Elevated page sections |
| `--bg-card` | `#1E1E1E` | `base-100` | Cards, panels, table cells |
| `--bg-card-hover` | `#252525` | `neutral` | Hover state for cards and rows |
| `--bg-header` | `#0A0A0A` | — | Navbar and footer background |

### Accent Colors

| Token | Hex | DaisyUI Mapping | Semantic Usage |
|-------|-----|-----------------|----------------|
| `--accent-red` | `#C43018` | `primary`, `error` | Primary accent, failed states, shadows, header stripes |
| `--accent-orange` | `#D4602A` | `secondary`, `warning` | Active/running states, active run card borders |
| `--accent-green` | `#2ECC40` | `success` | Completed states, success badges |
| `--accent-amber` | `#D49A20` | `accent` | Cost values, elapsed time, token metrics |
| `--accent-cream` | `#E8E4DF` | `info`, `base-content` | Primary text, borders, button outlines |

### Text Hierarchy

| Token | Hex | Usage |
|-------|-----|-------|
| `--text-primary` | `#E8E4DF` | Headlines, primary content, stat values |
| `--text-secondary` | `#999999` | Body text, table cells, descriptions |
| `--text-muted` | `#666666` | Labels, timestamps, metadata, inactive nav |

### Heatmap Scale (5 stops — Analytics)

| Token | Hex |
|-------|-----|
| `--heat-0` | `#1E1E1E` |
| `--heat-1` | `#3D1A12` |
| `--heat-2` | `#5C2518` |
| `--heat-3` | `#8A3520` |
| `--heat-4` | `#C43018` |

## Typography Rules

Both fonts are **monospace** — there are no sans-serif fonts in the brutalist design.

| Role | Font Family | Weight | Transform | Letter Spacing | Usage |
|------|-------------|--------|-----------|----------------|-------|
| **Display** | `Azeret Mono` | 700–900 | `uppercase` | 0.08–0.15em | Headings, labels, badges, nav links, buttons, stat titles |
| **Body** | `Inconsolata` | 400–700 | none | normal | Body text, table data, log output, descriptions |

**Font loading:** Google Fonts with `preconnect` for performance. Fallback: `ui-monospace, monospace`.

### Heading Hierarchy

| Element | Size | Weight | Spacing | Notes |
|---------|------|--------|---------|-------|
| `h1` | 28px | 900 | 0.08em | Page titles. Uppercase. |
| `h2` / section header | 13px | 800 | 0.12em | Prefixed with `//` in accent red. Uppercase. |
| Stat labels | 9px | 700 | 0.15em | `--text-muted`. Uppercase. |
| Badges | 9px (0.65rem) | 700 | 0.06em | Outline style. Uppercase. |
| Nav links | 11px | 700 | 0.1em | Active = accent red + underline. |

### Section Header Pattern

All section headers use the `//` prefix:
```
// ACTIVE RUNS [2]
// RECENT RUNS
// PROJECTS
```

The `//` is rendered in `--accent-red` via CSS `::before { content: '// '; color: var(--accent-red); }`. This references code comments and reinforces the developer-native aesthetic.

## Depth & Shadow System

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-brutal` | `4px 4px 0 var(--accent-red)` | Default card/table depth |
| `--shadow-brutal-hover` | `6px 6px 0 var(--accent-red)` | Hover lift effect |
| `--shadow-brutal-sm` | `2px 2px 0 var(--accent-red)` | Buttons, small elements |

**Hover interaction pattern:**
1. **Rest:** Element at normal position with default shadow.
2. **Hover:** Shadow grows (4px to 6px), element translates `(-1px, -1px)`.
3. **Active/Click:** Shadow collapses to 0, element snaps `(2px, 2px)`.

Transitions: `150ms ease`. Disabled when `prefers-reduced-motion: reduce`.

**Active run cards** use orange shadows (`4px 4px 0 var(--accent-orange)`) instead of red.

## Border System

| Pattern | Value | Usage |
|---------|-------|-------|
| Harsh border | `2px solid #E8E4DF` | Cards, tables, inputs |
| Stripe accent | `4px solid var(--accent-red)` | Header bottom, footer top |
| Thin divider | `1px solid #2A2A2A` | Table row separators |
| Active run left | `4px solid var(--accent-orange)` | Left border on active run cards |
| Phase top (completed) | `3px solid var(--accent-green)` | Phase timeline step |
| Phase top (active) | `3px solid var(--accent-amber)` | Phase timeline step |
| Phase top (pending) | `3px solid #333` | Phase timeline step |
| Phase top (failed) | `3px solid var(--accent-red)` | Phase timeline step |

## Decorative Elements

### Noise Texture Overlay
A full-viewport `::before` pseudo-element on `body` applies SVG fractal noise at `var(--noise-opacity)` (3%). This gives every surface a subtle film-grain texture that reinforces the industrial aesthetic. It is fixed-position with `pointer-events: none`.

### Diagonal Hatching (Stat Cards)
Stat cards feature a corner hatching accent via `::after` — a 36x36px area of repeating `-45deg` linear gradient in accent red at 30% opacity, positioned top-right. Applied automatically via `[data-theme="brutalist-dark"] .stat::after`.

### Page Header Divider
Every page has a `border-bottom: 3px solid var(--accent-cream)` divider below the title, creating a strong horizontal rule that grounds the page heading.

---
