# 8. New Run Flow

**Trigger:** "New Run" button (on overview and runs list pages) or "Re-run" button (on run detail page).
**PRD FRs:** FR12, FR14, FR15

## Modal Design

**DaisyUI:** `modal` component.

```
┌─────────────────────────────────────────────┐
│                                    [✕ Close]│
│  Start New Run                              │
│                                             │
│  Project                                    │
│  ┌───────────────────────────────────┐      │
│  │ Select a project...            ▾  │      │
│  └───────────────────────────────────┘      │
│                                             │
│  Feature Description                        │
│  ┌───────────────────────────────────┐      │
│  │                                   │      │
│  │ Describe the feature to build...  │      │
│  │                                   │      │
│  └───────────────────────────────────┘      │
│                                             │
│            [Cancel]  [Start Run]            │
│                                             │
└─────────────────────────────────────────────┘
```

**Components:**

| Element | DaisyUI | Notes |
|---------|---------|-------|
| Modal wrapper | `modal` with `modal-open` toggle | Opened via HTMX: `hx-get="/partials/new-run" hx-target="#modal-container"` |
| Project select | `select select-bordered w-full` | Populated server-side with registered projects |
| Feature textarea | `textarea textarea-bordered w-full` | 3 rows default. Placeholder: "Describe the feature to build..." |
| Cancel button | `btn btn-ghost` | Closes modal |
| Start button | `btn btn-primary` | Submits form |

**Form submission:**
```html
<form hx-post="/runs/start"
      hx-target="#main"
      hx-push-url="/runs/{new_id}"
      hx-indicator="#start-loading">
  <!-- CSRF token as hidden input -->
  <!-- Project select -->
  <!-- Feature textarea -->
</form>
```

**Validation:**
- Project must be selected (server validates it's registered — FR15)
- Feature description must not be empty
- Server-side validation returns errors inline (HTMX swaps the form with error messages)

**Loading state:**
- After clicking "Start Run", the button shows a `loading loading-spinner loading-sm` indicator
- `hx-indicator` targets the button

**Re-run variant:**
- When opened from a Run Detail page via "Re-run", the modal is pre-populated:
  - Project: pre-selected (disabled/locked)
  - Feature: pre-filled with the previous run's feature description (editable)
- URL: `hx-get="/partials/new-run?from={run_id}"`

**After submission:**
- Server creates the run, returns a redirect to the new Run Detail page
- The new run appears as active with the phase pipeline animating

## Abort Confirmation

**Trigger:** "Abort" button on Run Detail page (active runs only).

**DaisyUI:** `modal` with warning styling.

```
┌─────────────────────────────────────────────┐
│  ⚠ Abort Run?                               │
│                                             │
│  This will stop the current phase and mark  │
│  the run as aborted. This cannot be undone. │
│                                             │
│  Run: 01HQ8K3M...                           │
│  Phase: Build (in progress)                 │
│                                             │
│            [Cancel]  [Abort Run]            │
│                                             │
└─────────────────────────────────────────────┘
```

- Cancel: `btn btn-ghost`
- Abort: `btn btn-error`
- Form: `hx-post="/runs/{id}/abort"` with CSRF token
- After abort: page refreshes to show the run as aborted

---
