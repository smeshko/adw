# 6. Runs List Page

**Route:** `/runs`
**Purpose:** Full, filterable, sortable, paginated list of all runs across all projects.
**PRD FRs:** FR28-31

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER (global — sticky, 52px, bg-header, 4px red bottom) │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  RUNS                                                       │
│  ─────────────────────────── (3px cream bottom border)      │
│                                                             │
│  ┌STATUS│ALL ▾┐ ┌PROJECT│ALL ▾┐ ┌PERIOD│LAST 7 DAYS ▾┐    │
│  [Search features...___________________________]  142 RUNS  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐─┐ │
│  │ RUN ID  STARTED↓  PROJECT  FEATURE  STATUS  …PHASES │░│ │
│  │ ═══════ red 3px bottom border ═══════════════════════│░│ │
│  │ #01KH6G  2m ago   adw-core  Token.. ● RUNNING ■■◪□□ │░│ │
│  │ #01KH5R  18m ago  adw-dash  Analy.. ● RUNNING ■◪□□□ │░│ │
│  │ #01KH4F  2h ago   adw-core  Phase.. ✓ COMPLETED ■■■ │░│ │
│  │ ...                                                  │░│ │
│  └──────────────────────────────────────────────────────┘─┘ │
│   ← offset red shadow (4px 4px 0 accent-red)               │
│                                                             │
│  PAGE 1 OF 15 — 142 TOTAL     ←PREV [1] 2  3 … 15 NEXT→   │
│                                                             │
│  FOOTER (global — sticky bottom, 4px red top, bg-header)   │
└─────────────────────────────────────────────────────────────┘
```

---

## 6.1 Filter Bar

The filter bar is a flex row of inline filter groups, a search input, and a results count. No card wrapper — filters sit directly below the page header.

**Container:** `display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 1.25rem`

### Filter Groups

Each filter is rendered as a **label+select pair** that visually merge into one unit (the label's right border is removed so it fuses with the select).

```html
<div class="filters"
     hx-get="/runs"
     hx-target="#runs-content"
     hx-trigger="change from:select, input from:.search-box changed delay:300ms"
     hx-push-url="true"
     hx-include="[name]">

  <!-- Status filter -->
  <div class="filter-group">
    <span class="filter-label">Status</span>
    <select class="filter-select" name="status">
      <option value="">ALL</option>
      <option value="completed">COMPLETED</option>
      <option value="running">RUNNING</option>
      <option value="failed">FAILED</option>
      <option value="aborted">ABORTED</option>
    </select>
  </div>

  <!-- Project filter -->
  <div class="filter-group">
    <span class="filter-label">Project</span>
    <select class="filter-select" name="project">
      <option value="">ALL</option>
      <!-- Server-rendered from registered projects -->
      <option value="adw-core">ADW-CORE</option>
      <option value="adw-dashboard">ADW-DASHBOARD</option>
      <option value="adw-cli">ADW-CLI</option>
    </select>
  </div>

  <!-- Period filter -->
  <div class="filter-group">
    <span class="filter-label">Period</span>
    <select class="filter-select" name="period">
      <option value="7d">LAST 7 DAYS</option>
      <option value="30d">LAST 30 DAYS</option>
      <option value="">ALL TIME</option>
    </select>
  </div>

  <!-- Search box -->
  <input class="search-box" name="q" placeholder="Search features..." />

  <!-- Results count -->
  <span class="results-count">Showing <strong>142</strong> runs</span>
</div>
```

### Filter Label

| Property | Value |
|----------|-------|
| Font | `Azeret Mono` 9px, weight 700 |
| Transform | `uppercase` |
| Letter spacing | `0.12em` |
| Color | `--text-muted` (`#666`) |
| Padding | `6px 10px` |
| Background | `#252525` |
| Border | `2px solid #444` |
| Border right | `none` (merges visually with the adjacent select) |

### Filter Select

| Property | Value |
|----------|-------|
| Font | `Azeret Mono` 11px, weight 600 |
| Background | `--bg-card` (`#1E1E1E`) |
| Color | `--text-secondary` (`#999`) |
| Border | `2px solid #444` |
| Border radius | `0` (zero radius always) |
| Padding | `4px 8px` |
| Cursor | `pointer` |
| Focus state | `border-color: var(--accent-red); color: var(--text-primary)` |

### Search Box

| Property | Value |
|----------|-------|
| Font | `Inconsolata` 12px, weight 400 |
| Background | `--bg-card` (`#1E1E1E`) |
| Color | `--text-primary` (`#E8E4DF`) cream text |
| Placeholder color | `--text-muted` (`#666`) |
| Border | `2px solid #444` |
| Border radius | `0` |
| Padding | `5px 10px` |
| Flex | `flex: 1; min-width: 200px` (fills remaining row space) |
| Focus state | `border-color: var(--accent-red)` |

### Results Count

| Property | Value |
|----------|-------|
| Font | `Azeret Mono` 10px, weight 700 |
| Transform | `uppercase` |
| Letter spacing | `0.08em` |
| Color | `--text-muted` (`#666`) |
| Count value | `<strong>` in `--accent-cream` (`#E8E4DF`) |
| Positioning | `margin-left: auto` (pushes to far right of flex row) |

### HTMX Behavior

All filters combine into query params: `/runs?status=failed&project=adw-core&period=7d&q=token`

When any filter changes, the table (`#runs-content`) and results count refresh via HTMX, but the filter bar itself maintains its state from URL params. The `hx-push-url` keeps the URL bookmarkable.

**Search debounce:** The search box uses `hx-trigger="input changed delay:300ms"` to avoid excessive requests while typing.

---

## 6.2 Summary / Results Count

The results count is integrated inline within the filter bar (see 6.1 above), pushed to the right edge via `margin-left: auto`. There is no separate summary line — sort is handled by clickable column headers in the table.

---

## 6.3 Runs Table

### Table Card Wrapper

The table is wrapped in a card container with the signature cream border and red offset shadow.

| Property | Value |
|----------|-------|
| Background | `--bg-card` (`#1E1E1E`) |
| Border | `2px solid var(--accent-cream)` (`#E8E4DF`) — harsh border |
| Shadow | `4px 4px 0 var(--accent-red)` — offset red shadow |
| Overflow | `hidden` |
| Margin bottom | `1.25rem` |

### Table Header

| Property | Value |
|----------|-------|
| Background | `#252525` |
| Bottom border | `3px solid var(--accent-red)` |

### Header Cells

| Property | Value |
|----------|-------|
| Font | `Azeret Mono` 9px, weight 800 |
| Transform | `uppercase` |
| Letter spacing | `0.15em` |
| Color | `--accent-cream` (`#E8E4DF`) |
| Padding | `10px 16px` |
| Text align | `left` |
| Hover | `color: var(--accent-red)` |

### Sortable Columns

Sortable columns are clickable and display a sort arrow indicator:

```html
<th class="sorted"
    hx-get="/runs?sort=started&dir=desc"
    hx-target="#runs-content"
    hx-push-url="true">
  Started <span class="sort-arrow">▼</span>
</th>
```

| Sort Arrow Property | Value |
|---------------------|-------|
| Font size | `8px` |
| Margin left | `4px` |
| Default opacity | `0.4` |
| Sorted opacity | `1.0` |
| Sorted color | `var(--accent-red)` |
| Cursor | `pointer` on sortable `th`, `user-select: none` |

### Column Definitions

| Column | Cell Style | Width Hint | Sortable | Notes |
|--------|-----------|------------|----------|-------|
| Run ID | `font-size: 11px; color: --text-muted; font-weight: 600` (mono) | `w-20` | No | Short hash, e.g. `#01KH6G` |
| Started | `font-size: 12px; color: --text-muted` (dim) | `w-24` | Yes (default, descending) | Relative time, e.g. `2 min ago` |
| Project | `font-size: 13px; font-weight: 500` | `w-28` | Yes | Project name |
| Feature | `color: --text-secondary` (muted) | `flex-1` | No | Feature description, truncated |
| Status | Outline badge (see badge spec below) | `w-24` | Yes | Badge component |
| Phases | Compact pip squares (see pips spec below) | `w-20` | No | Visual pipeline indicator |
| Duration | `font-variant-numeric: tabular-nums` (mono) | `w-20` | Yes | e.g. `5m 12s` |
| Tokens | `font-variant-numeric: tabular-nums` (mono) | `w-16` | Yes | e.g. `84.0K` |
| Cost | `font-variant-numeric: tabular-nums` (mono) | `w-16` | Yes | e.g. `$3.18` |

### Status Badges

All badges are outline style — transparent background with 2px colored border. Zero radius.

| Status | Class | Color | Icon |
|--------|-------|-------|------|
| Running | `badge badge-warning` | `--accent-amber` (`#D49A20`) border + text | `●` |
| Completed | `badge badge-success` | `--accent-green` (`#2ECC40`) border + text | `✓` |
| Failed | `badge badge-error` | `--accent-red` (`#C43018`) border + text | `✗` |
| Aborted | `badge badge-ghost` | `#444` border, `--text-muted` text | `⦻` |

Badge typography: `Azeret Mono` 9px, weight 700, uppercase, `letter-spacing: 0.05em`, `padding: 3px 8px`.

### Phase Pips

Compact inline squares representing each phase in the pipeline.

```html
<div class="pipeline-inline">
  <span class="pip completed"></span>
  <span class="pip completed"></span>
  <span class="pip active"></span>
  <span class="pip"></span>
  <span class="pip"></span>
</div>
```

| Pip Property | Value |
|-------------|-------|
| Container | `display: flex; gap: 2px` |
| Pip size | `8px x 8px` square |
| Default (pending) | `border: 1px solid #444` only, no fill |
| `.pip.completed` | `background: var(--accent-green); border-color: var(--accent-green)` |
| `.pip.active` | `background: var(--accent-amber); border-color: var(--accent-amber)` |
| `.pip.failed` | `background: var(--accent-red); border-color: var(--accent-red)` |

### Row Behavior

| Property | Value |
|----------|-------|
| Cursor | `pointer` |
| Hover | `background: var(--bg-card-hover)` (`#252525`) on all `td` cells |
| Row separator | `border-bottom: 1px solid #2A2A2A` on `td` |
| Transition | `background 0.05s` |
| Keyboard nav | Rows have `data-navigable-row` attribute for `j`/`k` navigation |
| Click | `hx-get="/runs/{id}" hx-target="#main" hx-push-url="/runs/{id}"` |

### Full Table HTML

```html
<div id="runs-content">
  <div class="table-card">
    <table>
      <thead>
        <tr>
          <th>Run ID</th>
          <th class="sorted"
              hx-get="/runs?sort=started&dir=desc"
              hx-target="#runs-content"
              hx-push-url="true">
            Started <span class="sort-arrow">▼</span>
          </th>
          <th hx-get="/runs?sort=project&dir=asc"
              hx-target="#runs-content"
              hx-push-url="true">
            Project <span class="sort-arrow">▲</span>
          </th>
          <th>Feature</th>
          <th hx-get="/runs?sort=status&dir=asc"
              hx-target="#runs-content"
              hx-push-url="true">
            Status <span class="sort-arrow">▲</span>
          </th>
          <th>Phases</th>
          <th hx-get="/runs?sort=duration&dir=desc"
              hx-target="#runs-content"
              hx-push-url="true">
            Duration <span class="sort-arrow">▼</span>
          </th>
          <th hx-get="/runs?sort=tokens&dir=desc"
              hx-target="#runs-content"
              hx-push-url="true">
            Tokens <span class="sort-arrow">▼</span>
          </th>
          <th hx-get="/runs?sort=cost&dir=desc"
              hx-target="#runs-content"
              hx-push-url="true">
            Cost <span class="sort-arrow">▼</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr data-navigable-row
            hx-get="/runs/01KH6G"
            hx-target="#main"
            hx-push-url="/runs/01KH6G">
          <td class="run-id">#01KH6G</td>
          <td class="td-dim">2 min ago</td>
          <td>adw-core</td>
          <td class="td-muted">Implement token bucketing for cost tracking</td>
          <td><span class="badge badge-warning">● RUNNING</span></td>
          <td>
            <div class="pipeline-inline">
              <span class="pip completed"></span>
              <span class="pip completed"></span>
              <span class="pip active"></span>
              <span class="pip"></span>
              <span class="pip"></span>
            </div>
          </td>
          <td class="td-mono">3m 21s</td>
          <td class="td-mono">48.2K</td>
          <td class="td-mono">$1.82</td>
        </tr>
        <!-- Additional rows follow same pattern -->
      </tbody>
    </table>
  </div>

  <!-- Pagination rendered inside #runs-content so it refreshes with the table -->
  <div class="pagination">
    <!-- See section 6.4 -->
  </div>
</div>
```

---

## 6.4 Pagination

The pagination bar sits below the table card, inside `#runs-content` so it refreshes alongside the table data.

**Container:** `display: flex; align-items: center; justify-content: space-between`

### Page Info (Left Side)

| Property | Value |
|----------|-------|
| Font | `Azeret Mono` 10px, weight 600 |
| Transform | `uppercase` |
| Letter spacing | `0.08em` |
| Color | `--text-muted` (`#666`) |
| Content | e.g. `PAGE 1 OF 15 — 142 TOTAL RUNS` |

### Page Buttons (Right Side)

Button group with `display: flex; gap: 4px`.

| Property | Value |
|----------|-------|
| Font | `Azeret Mono` 11px, weight 700 |
| Padding | `6px 12px` |
| Background | `--bg-card` (`#1E1E1E`) |
| Color | `--text-secondary` (`#999`) |
| Border | `2px solid #444` |
| Border radius | `0` (zero always) |
| Cursor | `pointer` |
| Transition | `all 0.1s` |

**States:**

| State | Style |
|-------|-------|
| Default | As above |
| Hover | `border-color: var(--accent-cream); color: var(--text-primary)` |
| Active page | `border-color: var(--accent-red); color: var(--accent-red); box-shadow: 2px 2px 0 var(--accent-red)` (`shadow-brutal-sm`) |
| Disabled | `opacity: 0.3; cursor: not-allowed` |

### Pagination HTML

```html
<div class="pagination">
  <span class="page-info">Page 1 of 15 — 142 total runs</span>
  <div class="page-buttons">
    <button class="page-btn" disabled>← PREV</button>
    <button class="page-btn active">1</button>
    <button class="page-btn"
            hx-get="/runs?page=2"
            hx-target="#runs-content"
            hx-push-url="true">2</button>
    <button class="page-btn"
            hx-get="/runs?page=3"
            hx-target="#runs-content"
            hx-push-url="true">3</button>
    <button class="page-btn" disabled>...</button>
    <button class="page-btn"
            hx-get="/runs?page=15"
            hx-target="#runs-content"
            hx-push-url="true">15</button>
    <button class="page-btn"
            hx-get="/runs?page=2"
            hx-target="#runs-content"
            hx-push-url="true">NEXT →</button>
  </div>
</div>
```

- All pagination buttons use `hx-target="#runs-content" hx-push-url="true"`
- Page size: 10 runs per page
- Preserves current filter, sort, and search params in the HTMX request
- Ellipsis button is disabled (non-interactive)
- `← PREV` is disabled when on page 1; `NEXT →` is disabled on the last page

---

## CSS Reference

All styles below use the design system tokens from Section 1 (Design Philosophy).

```css
/* ── FILTERS BAR ── */
.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 1.25rem;
  align-items: center;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0;
}

.filter-label {
  font-family: var(--font-display);
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  padding: 6px 10px;
  background: #252525;
  border: 2px solid #444;
  border-right: none;
}

.filter-select {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 600;
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 2px solid #444;
  border-radius: 0;
  padding: 4px 8px;
  outline: none;
  cursor: pointer;
}
.filter-select:focus {
  border-color: var(--accent-red);
  color: var(--text-primary);
}

.search-box {
  font-family: var(--font-body);
  font-size: 12px;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 2px solid #444;
  border-radius: 0;
  padding: 5px 10px;
  outline: none;
  flex: 1;
  min-width: 200px;
}
.search-box::placeholder { color: var(--text-muted); }
.search-box:focus { border-color: var(--accent-red); }

.results-count {
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-left: auto;
}
.results-count strong { color: var(--accent-cream); }

/* ── TABLE ── */
.table-card {
  background: var(--bg-card);
  border: var(--border-harsh);          /* 2px solid #E8E4DF */
  box-shadow: var(--shadow-offset);     /* 4px 4px 0 #C43018 */
  overflow: hidden;
  margin-bottom: 1.25rem;
}

table { width: 100%; border-collapse: collapse; }

thead { background: #252525; }

th {
  font-family: var(--font-display);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  font-weight: 800;
  padding: 10px 16px;
  text-align: left;
  color: var(--accent-cream);
  border-bottom: 3px solid var(--accent-red);
  cursor: pointer;
  user-select: none;
}
th:hover { color: var(--accent-red); }

th .sort-arrow {
  font-size: 8px;
  margin-left: 4px;
  opacity: 0.4;
}
th.sorted .sort-arrow {
  opacity: 1;
  color: var(--accent-red);
}

td {
  padding: 12px 16px;
  font-size: 13px;
  border-bottom: 1px solid #2A2A2A;
  font-weight: 500;
}

tr[data-navigable-row] {
  cursor: pointer;
  transition: background 0.05s;
}
tr[data-navigable-row]:hover td {
  background: var(--bg-card-hover);
}

.run-id {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
}
.td-muted { color: var(--text-secondary); }
.td-dim   { color: var(--text-muted); font-size: 12px; }
.td-mono  { font-variant-numeric: tabular-nums; }

/* Badges — outline style, zero radius */
.badge {
  font-family: var(--font-display);
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 3px 8px;
  border: 2px solid;
  background: transparent;
}
.badge-success { color: var(--accent-green); border-color: var(--accent-green); }
.badge-warning { color: var(--accent-amber); border-color: var(--accent-amber); }
.badge-error   { color: var(--accent-red);   border-color: var(--accent-red); }
.badge-ghost   { color: var(--text-muted);   border-color: #444; }

/* Phase pips — 8x8 squares */
.pipeline-inline { display: flex; gap: 2px; }
.pip {
  width: 8px;
  height: 8px;
  border: 1px solid #444;
}
.pip.completed { background: var(--accent-green); border-color: var(--accent-green); }
.pip.active    { background: var(--accent-amber); border-color: var(--accent-amber); }
.pip.failed    { background: var(--accent-red);   border-color: var(--accent-red); }

/* ── PAGINATION ── */
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-info {
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

.page-buttons { display: flex; gap: 4px; }

.page-btn {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 700;
  padding: 6px 12px;
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 2px solid #444;
  border-radius: 0;
  cursor: pointer;
  transition: all 0.1s;
}
.page-btn:hover {
  border-color: var(--accent-cream);
  color: var(--text-primary);
}
.page-btn.active {
  border-color: var(--accent-red);
  color: var(--accent-red);
  box-shadow: 2px 2px 0 var(--accent-red);   /* shadow-brutal-sm */
}
.page-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
```

---
