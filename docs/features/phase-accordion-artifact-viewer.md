# Phase Accordion & Artifact Viewer

**Date:** 2026-02-12
**Related Files:** `src/adw/dashboard/routes.py`, `src/adw/dashboard/templates/partials/run_detail.html`, `src/adw/dashboard/templates/partials/phase_detail.html`, `src/adw/dashboard/templates/partials/artifact_viewer.html`

## Overview

The phase accordion adds collapsible per-phase sections to the run detail page, each lazy-loaded via HTMX on first click. Expanding a phase reveals hooks execution results and a list of artifacts produced by that phase. An inline artifact viewer renders markdown files as HTML and all other files in a monospaced pre block, loaded on demand into a shared viewer panel below the accordion.

## What Was Built

- Collapsible DaisyUI accordion (`collapse collapse-arrow bg-base-200`) for each phase on the run detail page, showing phase name, duration, status icon, token count, and cost in the collapsed title
- Lazy-loaded phase detail fragments via `hx-get="/runs/{id}/phases/{phase}" hx-trigger="click once"` — content loads once on first expand, subsequent toggles reuse cached HTML
- Phase detail route (`GET /runs/{run_id}/phases/{phase}`) that loads artifacts from disk via `ArtifactManager` and returns an HTML fragment with hooks and artifacts sub-sections
- Artifact viewer route (`GET /runs/{run_id}/artifacts/{phase}/{filename:path}`) with server-side markdown rendering and inline display in a card panel
- Per-phase data enrichment in `_build_run_detail_context()` computing tokens, cost, and status per phase from `RunContext.phase_tokens`
- Security hardening: phase validation against `PHASE_SEQUENCE`, filename path traversal prevention, HTML escaping before markdown rendering (XSS prevention)

## Technical Implementation

### Key Files

- `src/adw/dashboard/routes.py`: Phase detail route (`phase_detail`), artifact viewer route (`artifact_viewer`), helper functions (`_format_file_size`, `_find_run_entry`), and per-phase data enrichment in `_build_run_detail_context()`
- `src/adw/dashboard/templates/partials/run_detail.html`: Accordion section iterating over `phases_detail`, each with `hx-get` for lazy loading and a loading spinner as default content; includes `#artifact-viewer` target div
- `src/adw/dashboard/templates/partials/phase_detail.html`: HTML fragment with hooks card (type badge, status icon, script name, duration, error) and artifacts card (filename, size, View button with `hx-get` targeting `#artifact-viewer`)
- `src/adw/dashboard/templates/partials/artifact_viewer.html`: Inline viewer card with filename title, close button, prose div for markdown, pre block for text files
- `tests/unit/dashboard/test_run_detail.py`: 33 new tests across `TestPhaseAccordionContext`, `TestPhaseDetailRoute`, `TestArtifactViewerRoute`, `TestFormatFileSize`, `TestFindRunEntry`

### Key Patterns

- **Lazy-Loaded HTMX Accordion**: Each accordion uses `hx-trigger="click once"` so the phase detail fragment is fetched on first expand only. The `once` modifier prevents re-fetching on subsequent toggles. A `loading loading-dots loading-md` spinner shows as default content while loading. This pattern should be used for any dashboard section with expensive-to-load detail content.

- **Phase/Artifact Route Security (NFR10)**: Both the phase detail and artifact viewer routes validate the `phase` parameter against `PHASE_SEQUENCE` (a hardcoded tuple of valid phase names) before constructing any file paths. The artifact viewer additionally rejects filenames containing `..` or starting with `/`. This prevents arbitrary file system access through crafted URLs. Always validate route parameters against known-safe values before using them in file path construction.

- **Safe Markdown Rendering**: Before passing user-generated markdown content to the `markdown` library, the content is HTML-escaped (`&`, `<`, `>` replaced with entities). This prevents stored XSS from artifact content while still allowing markdown formatting. The rendered HTML is then inserted via Jinja2's `| safe` filter. Use this pattern whenever rendering markdown from untrusted sources.

- **Run Entry Lookup via `_find_run_entry()`**: A reusable helper that scans the index for a specific run ID. Returns `None` on any error, enabling simple `if run_entry is None: return 404` guards. Used by both phase detail and artifact viewer routes.

### Code Examples

Lazy-loaded accordion in a Jinja2 template:

```html
<div class="collapse collapse-arrow bg-base-200 mb-2">
  <input type="checkbox" />
  <div class="collapse-title">
    <span class="font-semibold">{{ phase.name }}</span>
  </div>
  <div class="collapse-content"
       hx-get="/runs/{{ run_id }}/phases/{{ phase.phase_key }}"
       hx-trigger="click once"
       hx-swap="innerHTML">
    <span class="loading loading-dots loading-md"></span>
  </div>
</div>
```

Phase validation in a route handler:

```python
from adw.core.constants import PHASE_SEQUENCE

if phase not in PHASE_SEQUENCE:
    return HTMLResponse(
        content='<p class="text-error text-sm">Invalid phase</p>',
        status_code=400,
    )
```

## How to Use

1. **View phase details**: On the run detail page, click any phase accordion to expand it. The first click loads hooks and artifacts data; subsequent clicks toggle without re-fetching.
2. **View artifacts inline**: Click the "View" button next to any artifact. The content loads into the `#artifact-viewer` panel below the accordion. Click "Close" to dismiss.
3. **Add new sub-sections to phase detail**: Edit `partials/phase_detail.html` and add a new card below the existing hooks/artifacts cards. Extend the `phase_detail` route handler to include additional context data.
4. **Add new lazy-loaded sections**: Follow the accordion pattern — add `hx-get`, `hx-trigger="click once"`, and `hx-swap="innerHTML"` to any collapse-content div, with a loading spinner as default content.

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| Cost estimate rate | Python constant | `tokens * 0.000009` | Per-phase cost estimate in `_build_run_detail_context()` |
| Valid phases | Python tuple | `PHASE_SEQUENCE` from `constants.py` | Allowlist for phase parameter validation |
| Markdown extensions | Python list | `["fenced_code", "tables"]` | Extensions passed to `markdown.markdown()` |
| Max viewer height | CSS class | `max-h-96` | Maximum height for artifact viewer content area |

## Notes

- Hooks data is currently always an empty list because `HookResult` objects are not yet persisted in `RunContext`. When hook persistence is implemented, the `phase_detail` route handler will need to load and format hook data from the context.
- The `_find_run_entry()` helper scans all runs with `limit=100000`, which is acceptable for current scale but should be replaced with a direct ID lookup method on `IndexManager` when available.
- Binary file detection is not yet implemented. Currently all artifact content is loaded as text, which may fail for binary files (caught by `UnicodeDecodeError` exception handler).
- The artifact viewer uses `onclick` with `innerHTML=''` for the close button rather than HTMX, keeping it simple and avoiding a round-trip for a client-only operation.
