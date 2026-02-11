# 12. Responsive Behavior

## Breakpoints

| Width | Layout |
|-------|--------|
| ≥1280px | Full layout as designed — stat cards horizontal, side-by-side panels |
| 1024-1279px | Compact — stat cards may wrap to 2 rows, breakdown panels stack |
| <1024px | Not officially supported but should not break |

## Responsive Rules

**Stat cards:**
- `flex flex-wrap gap-4` — cards flow to next line when space is tight
- On compact screens: 3 cards first row, 2 second row

**Active run cards:**
- `flex flex-wrap gap-4` — stack vertically on narrow screens

**Analytics breakdown panels:**
- `grid grid-cols-1 lg:grid-cols-2 gap-4` — side by side on wide, stacked on narrow

**Tables:**
- Feature column gets `truncate` with a `max-w` that shrinks on compact screens
- On very narrow screens, the table scrolls horizontally inside a `overflow-x-auto` wrapper

**Phase pipeline:**
- `steps-horizontal` on wide screens
- Could switch to `steps-vertical` on very narrow screens via responsive class (but since minimum is 1024px, horizontal should always work)

---
