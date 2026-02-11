# 11. States & Edge Cases

## 11.1 Empty States

Each section needs a graceful empty state — not a blank void, but a helpful message.

**No registered projects (first-time user):**
```
┌──────────────────────────────────────────────┐
│                                              │
│  Welcome to ADW Dashboard                    │
│                                              │
│  No projects registered yet. Register a      │
│  project from the CLI to get started:        │
│                                              │
│  $ adw global register                       │
│                                              │
└──────────────────────────────────────────────┘
```
DaisyUI: `hero` or centered `card` with `text-base-content/60`.

**No runs yet (projects exist but no runs):**
```
┌──────────────────────────────────────────────┐
│                                              │
│  No runs yet                                 │
│                                              │
│  Start your first run from the CLI or use    │
│  the New Run button above.                   │
│                                              │
│              [+ Start a Run]                 │
│                                              │
└──────────────────────────────────────────────┘
```

**No active runs:** The active runs section simply doesn't render. No "no active runs" message needed — its absence is the message.

**No runs matching filters (runs list page):**
```
No runs match your filters. Try adjusting the status or date range.  [Clear filters]
```

**No analytics data for time range:**
```
No data for the selected period. Try a wider time range.
```

## 11.2 Error States

**Data layer error (can't read index):**
- Show an `alert alert-error` at the top of the affected section:
  ```
  ⚠ Unable to load run data. The index file may be corrupted or locked.
  ```
- Rest of the page still renders with whatever data is available

**HTMX request failure:**
- DaisyUI doesn't have a built-in error toast, but we can use a positioned `alert` that auto-dismisses
- HTMX `htmx:responseError` event handler shows an error banner:
  ```html
  <div id="error-banner" class="alert alert-error fixed top-16 right-4 w-auto z-50 hidden">
    <span>Request failed. <button hx-get="..." class="link">Retry</button></span>
  </div>
  ```
- Show via `htmx:responseError` event (small inline JS, ~5 lines)

**Run not found (404):**
- Return a centered message in `#main`: "Run not found. It may have been deleted."
- Back link to overview

**Start run validation error:**
- Server returns the modal form with inline error messages (standard HTMX form pattern)
- Error messages appear below the affected field in `text-error text-sm`

## 11.3 Loading States

**Initial page load:** Server-rendered — no loading state needed. The page arrives complete.

**Navigation between pages:** Brief `loading loading-spinner` in the header area (via `hx-indicator`).

**Lazy-loaded content (phase details, artifacts, LLM text):**
- Target area shows `loading loading-dots loading-md` centered
- Content replaces the loader when the response arrives

**Polling refreshes:** Invisible. No loading indicators for background refreshes.

---
