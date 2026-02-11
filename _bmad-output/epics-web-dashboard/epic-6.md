# Epic 6: View Modes & Keyboard Navigation

Power users can navigate the dashboard with keyboard shortcuts, toggle terminal mode for raw log output, and enter focus mode for dedicated single-run monitoring — optimizing the dashboard for keyboard-driven developer workflows.

**FRs covered:** FR39-FR41 (3 FRs)

### Story 6.1: Keyboard Shortcuts & Overlay

As a developer,
I want to navigate the dashboard using keyboard shortcuts and view a shortcut reference overlay,
So that I can use the dashboard efficiently without reaching for the mouse.

**Acceptance Criteria:**

**Given** the dashboard is loaded on any page
**When** the user presses `?`
**Then** a keyboard shortcut overlay modal opens using DaisyUI `modal` (FR39, UX §13)
**And** the modal shows all available shortcuts in a two-column layout with `kbd kbd-sm` badges:
| Key | Action | Context |
|-----|--------|---------|
| `?` | Toggle shortcut overlay | Global |
| `g h` | Go to Overview (home) | Global |
| `g r` | Go to Runs List | Global |
| `g a` | Go to Analytics | Global |
| `n` | Open New Run modal | Overview, Runs List |
| `j` / `↓` | Next item in list | Runs List, Overview recent runs |
| `k` / `↑` | Previous item in list | Runs List, Overview recent runs |
| `Enter` | Open selected run | Runs List, Overview recent runs |
| `Esc` | Close modal / go back | Modals, detail pages |
| `/` | Focus search input | Runs List, Log viewer |
| `r` | Refresh | Global |
**And** pressing `?` again or `Esc` closes the overlay

**Given** the user presses `g` followed by `h`
**When** the key sequence is recognized
**Then** the dashboard navigates to the overview page via HTMX (same as clicking the Overview nav link) (FR39)

**Given** the user presses `g` followed by `r`
**When** the key sequence is recognized
**Then** the dashboard navigates to the runs list page (FR39)

**Given** the user presses `g` followed by `a`
**When** the key sequence is recognized
**Then** the dashboard navigates to the analytics page (FR39)

**Given** the user is on the runs list or overview with recent runs
**When** the user presses `j` or `↓`
**Then** the next item in the list is highlighted/focused
**When** the user presses `k` or `↑`
**Then** the previous item is highlighted/focused
**When** the user presses `Enter`
**Then** the focused run opens (navigates to its detail page) (FR39)

**Given** the user presses `n` on the overview or runs list
**When** the key is recognized
**Then** the New Run modal opens (FR39)

**Given** the user presses `/`
**When** the key is recognized and a search input is on the page
**Then** the search/filter input is focused (FR39)

**Given** the user presses `r`
**When** the key is recognized
**Then** the current page content refreshes (FR39)

**Given** the user presses `Esc`
**When** a modal is open
**Then** the modal closes
**When** on a detail page with no modal
**Then** navigation goes back (equivalent to the back link) (FR39)

**Given** the user is typing in an input, textarea, or select
**When** any shortcut key is pressed
**Then** the shortcut is NOT triggered — normal typing behavior is preserved (UX §13)

**Technical notes:**
- Implementation: ~30 lines of inline JavaScript in a `<script>` tag (UX §13)
- This is the only client-side JS beyond HTMX, theme toggle, and copy button
- Two-key sequences (`g h`, `g r`, `g a`) require a simple state machine tracking pending `g` press
- Event listener: `document.addEventListener('keydown', ...)` with `e.target.matches('input, textarea, select')` guard
- Keyboard shortcuts component: `keyboard_help.html` partial

---

### Story 6.2: Terminal Mode & Focus Mode

As a developer,
I want to toggle terminal mode for raw log output and enter focus mode for dedicated single-run monitoring,
So that I can get a distraction-free view of logs or a single run's progress.

**Acceptance Criteria:**

**Given** the user activates terminal mode (via keyboard shortcut or UI toggle)
**When** terminal mode is enabled
**Then** the dashboard switches to a monospace scrolling view displaying raw log output (FR40)
**And** the view uses `font-mono` with a dark background, filling the main content area
**And** log entries stream or display in chronological order
**And** standard dashboard navigation remains available in the header

**Given** terminal mode is active
**When** the user deactivates it (via the same toggle or `Esc`)
**Then** the dashboard returns to the normal view state

**Given** the user is viewing an active run
**When** focus mode is activated (via keyboard shortcut or UI button)
**Then** the dashboard content area is replaced with a single-run live view showing: phase progress pipeline (full-width, animated), streaming logs for the current phase, elapsed time updating in real-time (FR41)
**And** the focus mode uses SSE for real-time updates (same as run detail active variant)
**And** the header remains visible for navigation

**Given** focus mode is active
**When** the run completes, fails, or is aborted
**Then** the view updates to show the final status
**And** the user can exit focus mode to return to the normal dashboard

**Given** focus mode is active
**When** the user presses `Esc` or clicks a navigation link
**Then** focus mode exits and the dashboard returns to normal navigation

**Technical notes:**
- Terminal mode: CSS classes for terminal appearance in `dashboard/static/dashboard.css` (UX §6 architecture scope)
- Focus mode: Replaces `#main` content with a specialized single-run view using existing SSE infrastructure
- Both modes are CSS-driven with minimal additional JS
- Focus mode reuses the SSE streams from Story 2.4 (`/runs/{id}/events`, `/runs/{id}/logs/stream`)
