# 9. Interaction Patterns

## 9.1 HTMX Route Map

| Action | Method | URL | Target | Swap | Push URL |
|--------|--------|-----|--------|------|----------|
| Navigate to Overview | GET | `/` | `#main` | `innerHTML` | `/` |
| Navigate to Runs List | GET | `/runs` | `#main` | `innerHTML` | `/runs` |
| Navigate to Run Detail | GET | `/runs/{id}` | `#main` | `innerHTML` | `/runs/{id}` |
| Navigate to Analytics | GET | `/analytics` | `#main` | `innerHTML` | `/analytics` |
| Filter overview by project | GET | `/?project={name}` | `#main` | `innerHTML` | `/?project={name}` |
| Filter runs list | GET | `/runs?status=&project=&...` | `#runs-content` | `innerHTML` | Yes |
| Change analytics time range | GET | `/analytics?range=30d` | `#analytics-content` | `innerHTML` | Yes |
| Refresh active runs (poll) | GET | `/partials/active-runs` | `#active-runs` | `outerHTML` | No |
| Refresh stats (poll) | GET | `/partials/stats` | `#stats-row` | `outerHTML` | No |
| Refresh recent runs (poll) | GET | `/partials/recent-runs` | `#recent-runs` | `outerHTML` | No |
| Load phase detail (lazy) | GET | `/runs/{id}/phases/{phase}` | `.phase-content` | `innerHTML` | No |
| Load artifact content | GET | `/runs/{id}/artifacts/{path}` | `#artifact-viewer` | `innerHTML` | No |
| Load LLM prompt/response | GET | `/runs/{id}/phases/{phase}/prompt` | Inline target | `innerHTML` | No |
| Open new run modal | GET | `/partials/new-run` | `#modal-container` | `innerHTML` | No |
| Submit new run | POST | `/runs/start` | `#main` | `innerHTML` | `/runs/{new_id}` |
| Open abort modal | GET | `/partials/abort/{id}` | `#modal-container` | `innerHTML` | No |
| Submit abort | POST | `/runs/{id}/abort` | `#main` | `innerHTML` | No |
| Search logs | GET | `/runs/{id}/logs?q=&level=&phase=` | `#log-content` | `innerHTML` | No |

## 9.2 SSE (Server-Sent Events)

Used for real-time updates on active runs.

| Stream | URL | Events | Used On |
|--------|-----|--------|---------|
| Run progress | `/runs/{id}/events` | `phase-update`, `run-complete`, `run-failed` | Run Detail page (active runs) |
| Log stream | `/runs/{id}/logs/stream` | `log-line` | Run Detail page (log viewer, active phase) |

**SSE connection lifecycle:**
- Connected when viewing an active run's detail page
- Disconnected when navigating away (HTMX handles this automatically when the SSE element is removed from DOM)
- Auto-reconnect on network interruption (HTMX SSE extension default behavior)

**Event: `phase-update`**
- Payload: HTML fragment for the phase pipeline + metadata
- Swap: `hx-swap-oob="true"` to update the pipeline and elapsed time without touching other page content

**Event: `run-complete` / `run-failed`**
- Payload: Full run header + pipeline refresh
- Triggers: action buttons swap (remove Abort, show Re-run), status badge update

## 9.3 Polling Strategy

| Section | Interval | Condition |
|---------|----------|-----------|
| Active runs (overview) | 3s | Always when on overview |
| Stats row (overview) | 30s | Always when on overview |
| Recent runs (overview) | 15s | Always when on overview |
| Status bar footer | 10s | Always (global) |
| Runs list table | None | Manual refresh or filter change only |
| Analytics | None | Manual range change only |

**Polling pause:** When the browser tab is not visible (`document.visibilityState === "hidden"`), HTMX naturally pauses polling. No additional logic needed.

## 9.4 Out-of-Band Updates

When a polling request returns data, it can include out-of-band swaps to keep related sections in sync:

- Active runs poll returns `hx-swap-oob="true" id="stats-row"` to refresh stats if a run completed since last poll
- Stats poll returns `hx-swap-oob="true" id="status-bar"` to update the footer

## 9.5 Loading Indicators

**DaisyUI:** `loading loading-spinner` or `loading loading-dots`

- **Navigation:** During page-level swaps, show a `loading loading-spinner loading-sm` indicator in the header nav area. Use `hx-indicator="#nav-loading"`.
- **Lazy-loaded content:** Phase details, artifact content, LLM text — show `loading loading-dots` centered in the target area.
- **Form submission:** Button-level indicator — the submit button shows a spinner and disables itself.
- **Polling:** No visible indicator — polling should be invisible to the user.

---
