# ADW Design System — Industrial Brutalist Dark

Reference spec for the ADW dashboard visual language. All tokens live in
`src/adw/dashboard/static/brutalist-theme.css` and are activated by
`data-theme="brutalist-dark"` on `<html>`.

---

## 1. Color Palette

### Backgrounds

| Token            | Hex       | Usage                        |
|------------------|-----------|------------------------------|
| `--bg-void`      | `#111111` | Page background              |
| `--bg-surface`   | `#181818` | Navbar, elevated surfaces    |
| `--bg-card`      | `#1E1E1E` | Card / panel backgrounds     |
| `--bg-card-hover`| `#252525` | Hover states                 |
| `--bg-header`    | `#0A0A0A` | Header, footer, table heads  |

### Text

| Token              | Hex       | Usage              |
|--------------------|-----------|--------------------|
| `--text-primary`   | `#E8E4DF` | Body text (cream)  |
| `--text-secondary` | `#999999` | Secondary text     |
| `--text-muted`     | `#666666` | Muted / disabled   |

### Accents

| Token            | Hex       | Usage                           |
|------------------|-----------|---------------------------------|
| `--accent-red`   | `#C43018` | Primary accent, shadows, errors |
| `--accent-orange`| `#D4602A` | Active / running states         |
| `--accent-green` | `#2ECC40` | Success / completed             |
| `--accent-amber` | `#D49A20` | Warning, costs, highlights      |
| `--accent-cream` | `#E8E4DF` | Borders, button outlines        |

### Heatmap Scale

| Stop       | Hex       |
|------------|-----------|
| `--heat-0` | `#1E1E1E` |
| `--heat-1` | `#3D1A12` |
| `--heat-2` | `#5C2518` |
| `--heat-3` | `#8A3520` |
| `--heat-4` | `#C43018` |

### DaisyUI Semantic Mapping

| DaisyUI Token     | Maps To         |
|-------------------|-----------------|
| `--color-primary` | `--accent-red`  |
| `--color-secondary`| `--accent-orange` |
| `--color-accent`  | `--accent-amber`|
| `--color-success` | `--accent-green`|
| `--color-warning` | `--accent-orange`|
| `--color-error`   | `--accent-red`  |
| `--color-info`    | `--accent-cream`|

---

## 2. Typography

### Fonts

| Role    | Family          | Weights    | Usage                              |
|---------|-----------------|------------|------------------------------------|
| Display | Azeret Mono     | 400–900    | Headings, labels, badges, buttons  |
| Body    | Inconsolata     | 400–700    | Body text, table cells, logs       |

### Scale

| Element     | Family       | Size     | Weight | Letter-spacing | Transform  |
|-------------|-------------|----------|--------|----------------|------------|
| h1          | Azeret Mono | 1.5rem   | 900    | 0.12em         | UPPERCASE  |
| h2          | Azeret Mono | 1.25rem  | 800    | 0.10em         | UPPERCASE  |
| h3–h4       | Azeret Mono | 1rem     | 700    | 0.08em         | UPPERCASE  |
| Body        | Inconsolata | 0.875rem | 400    | normal         | none       |
| Stat title  | Azeret Mono | 0.7rem   | 700    | 0.08em         | UPPERCASE  |
| Badge       | Azeret Mono | 0.65rem  | 700    | 0.06em         | UPPERCASE  |
| Label       | Azeret Mono | 0.65rem  | 600    | 0.06em         | UPPERCASE  |

### Section Header Pattern

Headings use the `// PREFIX` pattern:

```css
.section-header::before {
  content: '// ';
  color: var(--accent-red);
}
```

Apply via `.section-header` class or use in templates where appropriate.

---

## 3. Spacing & Layout

| Token                    | Value    |
|--------------------------|----------|
| `--card-padding-compact` | `0.75rem`|
| `--table-row-height`     | `2.25rem`|
| Container                | Tailwind `container mx-auto p-4` |
| Card gaps                | `gap-4`  |
| Section spacing          | `mb-6` or `mt-6` |

---

## 4. Borders & Shadows

### Borders

| Pattern          | CSS                            | Usage                      |
|------------------|--------------------------------|----------------------------|
| Primary border   | `2px solid #E8E4DF`            | Cards, inputs, tables      |
| Accent stripe    | `4px solid #C43018`            | Header bottom, footer top  |
| Table head       | `3px solid #C43018`            | Below thead row            |
| Row separator    | `1px solid #2A2A2A`            | Between table rows         |

### Shadows

| Token                    | CSS                      | Usage                  |
|--------------------------|--------------------------|------------------------|
| `--shadow-brutal`        | `4px 4px 0 #C43018`     | Cards, tables, default |
| `--shadow-brutal-hover`  | `6px 6px 0 #C43018`     | Hover states           |
| `--shadow-brutal-sm`     | `2px 2px 0 #C43018`     | Buttons, pagination    |

### Radius

**Zero everywhere.** All DaisyUI radius tokens are set to `0`.

---

## 5. Component Catalog

### Stat Cards

- Border: `2px solid cream`
- Shadow: `4px 4px 0 red`
- Diagonal hatching in top-right corner (CSS `::after` pseudo-element)
- Hover: shadow grows to `6px 6px`, card shifts `-1px`
- Title: Azeret Mono, uppercase, `0.7rem`, `--text-secondary`
- Value: Azeret Mono, `font-mono`, `--text-primary`

### Tables

- Wrapper: card with cream border + brutal shadow
- `thead`: background `--bg-header`, bottom `3px solid red`
- `th`: Azeret Mono uppercase, cream color
- `tbody tr`: `1px solid #2A2A2A` separator
- Zebra: even rows `#1A1A1A`
- Hover row: `--bg-card-hover`

### Badges (Status)

All badges are **outline-only** (transparent background):

| Status       | Border + Text Color  |
|--------------|---------------------|
| `completed`  | `--accent-green`    |
| `running`    | `--accent-orange`   |
| `failed`     | `--accent-red`      |
| `interrupted`| `--accent-orange` (outline variant) |
| `aborted`    | `--text-muted`      |

### Buttons

| Variant   | Style                                          |
|-----------|-------------------------------------------------|
| Primary   | Outline cream, `2px 2px 0 red` shadow           |
| Primary hover | Fill red, shadow grows, `-1px` translate     |
| Danger    | Outline red                                     |
| Ghost     | No border, `--text-secondary`, hover fills card |

### Phase Pipeline

- DaisyUI `.steps` component
- Step circles: success = green, warning = orange
- Active step: `phase-pulse` animation
- Labels: Azeret Mono uppercase, `0.65rem`

### Active Run Cards

- Cream border + **orange left border** (`4px`)
- Shadow: `4px 4px 0 orange`
- Hover: shadow grows to `6px 6px`

### Project Cards

- Standard cream border + red shadow
- Selected: `ring-primary` (red ring)

### Cost Strip

- Joined card layout with cost summary, mini bar chart, link
- Bar chart bars use `--accent-red`

### Pagination

- `.join` group — all buttons `border-radius: 0`
- Active page: red background, cream text, `2px 2px 0 red` shadow

### Tabs (Time Range)

- Container: cream border, `--bg-surface` background
- Active tab: red background, cream text
- Inactive: `--text-secondary`

### Filters

- Label: Azeret Mono uppercase
- Select/Input: cream border, `--bg-card` background
- Focus: `2px solid red` outline

### Bar Charts

- Alternating `--accent-red` / `--accent-orange` bars (odd/even)
- No border-radius on bars

### Progress Bars (Budget)

- Background: `#2A2A2A`
- No border-radius
- Height: `0.75rem`

### Alerts / Toasts

- No border-radius
- `2px solid` border
- Inconsolata font

---

## 6. Status Color Vocabulary

| Status      | Color            | Used For                    |
|-------------|------------------|-----------------------------|
| Success     | `#2ECC40` green  | Completed runs, positive trends |
| Active      | `#D4602A` orange | Running, in-progress        |
| Error       | `#C43018` red    | Failed, negative trends     |
| Warning     | `#D49A20` amber  | Cost alerts, budget         |
| Neutral     | `#666666` muted  | Aborted, disabled           |

---

## 7. Noise Texture

A subtle film-grain overlay via `body::before` pseudo-element:
- SVG `feTurbulence` filter as data-URI (no external files)
- Opacity: `var(--noise-opacity)` = `0.03`
- Fixed position, covers full viewport
- `pointer-events: none`, `z-index: 9999`

---

## 8. Do's and Don'ts

### Do

- Use `border-radius: 0` on everything — sharp corners are the identity
- Use offset shadows (`4px 4px 0 red`) instead of soft drop shadows
- Use Azeret Mono for headings, labels, and badges; Inconsolata for body
- Use the `// PREFIX` pattern for section headings
- Use cream (`#E8E4DF`) for borders and primary text
- Use outline-only badges (transparent bg, colored border)
- Keep the noise overlay subtle (`opacity: 0.03`)

### Don't

- Don't use rounded corners, `border-radius`, or `rounded-*` Tailwind classes
- Don't use soft/blurred box shadows (`box-shadow: 0 4px 6px rgba(...)`)
- Don't use gradients for backgrounds — flat solid colors only
- Don't use sans-serif fonts — everything is monospace
- Don't use filled/solid badges — always outline
- Don't use light/pastel colors for accents — high contrast only
- Don't add decorative icons or illustrations — the typography is the decoration

---

## 9. File Map

| File | Purpose |
|------|---------|
| `src/adw/dashboard/static/brutalist-theme.css` | Theme definition + component overrides |
| `src/adw/dashboard/static/dashboard.css` | HTMX transitions, animations, layout tokens |
| `src/adw/dashboard/templates/base.html` | Loads fonts & theme, sets `data-theme` |
| `docs/design-system-brutalist.md` | This document |
