# 1. Design Philosophy

## Guiding Principles

- **Hub-and-spoke navigation** — The overview is a hub. Every section is a compact preview of a full page. Users drill down, not across.
- **Information density without clutter** — Use progressive disclosure. Show summaries first, expand on demand.
- **Developer-native aesthetic** — Monospace data, high contrast, dark default, utilitarian. No decorative flourishes.
- **Server-driven interactivity** — All interactions go through HTMX. No client-side state. URLs are always bookmarkable.
- **Consistent status language** — The same colors, icons, and labels for run status everywhere: overview, detail, list.

## Design Vocabulary

| Status | Color | Icon | DaisyUI Badge |
|--------|-------|------|---------------|
| Running | `warning` (amber) | `●` (pulsing) | `badge-warning` |
| Completed | `success` (green) | `✓` | `badge-success` |
| Failed | `error` (red) | `✗` | `badge-error` |
| Interrupted | `warning` (orange) | `⊘` | `badge-warning badge-outline` |
| Aborted | `neutral` (grey) | `⦻` | `badge-ghost` |

## Typography Rules

| Context | Font | Size |
|---------|------|------|
| UI labels, navigation, headings | System sans-serif (DaisyUI default) | Normal hierarchy |
| Run IDs, durations, token counts, costs, log output | `font-mono` (monospace) | `text-sm` or `text-xs` |
| Feature descriptions | Sans-serif | `text-sm` |
| Stat card values | Sans-serif bold | `text-3xl` or `text-2xl` |

---
