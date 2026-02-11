# Epic 3: Run Management

User can start new runs, abort active runs, and re-run previous runs directly from the browser — transforming the dashboard from a monitoring tool into a full command center.

**FRs covered:** FR12-FR15 (4 FRs)

### Story 3.1: New Run Modal & Form Submission

As a developer,
I want to start a new ADW run by selecting a project and describing a feature directly from the dashboard,
So that I can trigger runs without switching to the CLI.

**Acceptance Criteria:**

**Given** the user clicks the "+ New Run" button on the overview or runs list page
**When** the button is clicked
**Then** a DaisyUI `modal` is opened via `hx-get="/partials/new-run" hx-target="#modal-container"` (UX §8)
**And** the modal contains: a close button (`✕`), title "Start New Run", project select, feature textarea, cancel and start buttons

**Given** the new run modal is displayed
**When** the form renders
**Then** the project select is a `select select-bordered w-full` populated server-side with all registered projects from `ProjectRegistryManager` (FR12)
**And** the feature textarea is `textarea textarea-bordered w-full` with 3 rows and placeholder "Describe the feature to build..." (FR12)
**And** a CSRF token is included as a hidden form input (FR53, NFR9)
**And** the cancel button is `btn btn-ghost` and closes the modal
**And** the start button is `btn btn-primary`

**Given** the user fills in the form and clicks "Start Run"
**When** the form submits
**Then** the form submits via `hx-post="/runs/start" hx-target="#main" hx-push-url="/runs/{new_id}"` (UX §8)
**And** the start button shows a `loading loading-spinner loading-sm` indicator and disables itself during submission (`hx-indicator="#start-loading"`) (UX §8, §9.5)

**Given** the form is submitted with a valid project and feature
**When** the server processes the request
**Then** the server validates the project exists and is registered (FR15)
**And** the run is created and the response redirects to the new Run Detail page
**And** the new run appears as active with the phase pipeline animating (UX §8)
**And** starting from the dashboard produces identical results to starting via CLI (NFR26)

**Given** the form is submitted with invalid data
**When** the project is not selected or feature is empty
**Then** the server returns the modal form with inline error messages via HTMX swap (UX §8, §11.2)
**And** error messages appear below the affected field in `text-error text-sm`

**Given** the form is submitted with a project that no longer exists
**When** the server validates
**Then** an inline validation error is shown: "Project not found or not registered" (FR15)

**Given** a concurrent CLI operation is modifying run data
**When** the dashboard starts a run simultaneously
**Then** the system handles the concurrent operation without data corruption (NFR19)

**Architecture requirements:**
- Extract `core/run_trigger.py` from `webhook/runner.py` so dashboard can start runs without importing webhook
- POST endpoint in `dashboard/mutations.py` with CSRF validation from `dependencies.py`
- Dashboard MUST NOT import from `webhook/` module

---

### Story 3.2: Re-run Flow

As a developer,
I want to start a new run pre-populated with context from a previous run,
So that I can quickly retry or iterate on a previous feature without retyping details.

**Acceptance Criteria:**

**Given** the user is on a run detail page
**When** the "Re-run" button (`btn btn-primary btn-outline btn-sm`) is clicked
**Then** the New Run modal opens pre-populated via `hx-get="/partials/new-run?from={run_id}" hx-target="#modal-container"` (FR14, UX §8)

**Given** the re-run modal is displayed
**When** the form renders
**Then** the project select is pre-selected with the previous run's project (disabled/locked — user cannot change project for re-run) (UX §8)
**And** the feature textarea is pre-filled with the previous run's feature description (editable — user can modify before submitting) (FR14)
**And** CSRF token is included as a hidden input
**And** the modal title reflects "Re-run" context

**Given** the user modifies the feature description and submits
**When** the form posts
**Then** a new run is created with the pre-selected project and updated feature
**And** the user is redirected to the new run's detail page with the pipeline animating

**Given** the re-run modal is displayed
**When** the user clicks cancel
**Then** the modal closes and the user remains on the original run detail page

---

### Story 3.3: Abort Active Run

As a developer,
I want to abort an active run with a confirmation step,
So that I can stop a run that's going wrong without accidental cancellations.

**Acceptance Criteria:**

**Given** the user is on an active run's detail page
**When** the "Abort" button (`btn btn-error btn-outline btn-sm`) is clicked
**Then** an abort confirmation modal opens via `hx-get="/partials/abort/{id}" hx-target="#modal-container"` (FR13, UX §8)

**Given** the abort confirmation modal is displayed
**When** it renders
**Then** it shows a DaisyUI `modal` with warning styling (`⚠ Abort Run?`) (UX §8)
**And** the body text reads: "This will stop the current phase and mark the run as aborted. This cannot be undone."
**And** it displays the run ID (`font-mono`) and current phase (e.g., "Build (in progress)")
**And** cancel button: `btn btn-ghost`
**And** abort button: `btn btn-error`

**Given** the user clicks "Abort Run" in the confirmation modal
**When** the form submits
**Then** it posts via `hx-post="/runs/{id}/abort" hx-target="#main"` with a CSRF token (FR13, FR53)
**And** the run is stopped and marked as aborted
**And** the page refreshes to show the run as aborted (grey status, `badge-ghost`)
**And** the Abort button is no longer visible (run is no longer active)

**Given** the user clicks "Cancel" in the abort modal
**When** the modal closes
**Then** the user remains on the run detail page and the run continues running

**Given** a concurrent CLI operation is running on the same run
**When** the dashboard aborts the run
**Then** the system handles the concurrent operation without data corruption (NFR19)

**Architecture requirements:**
- POST endpoint: `POST /runs/{id}/abort` in `dashboard/mutations.py`
- Uses `core/run_trigger.py` for abort logic — shared with webhook
- CSRF validated via `dependencies.py`
