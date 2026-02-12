# Epic 7: Settings & Configuration

User can view, edit, validate, and save project and phase configuration for any registered project directly from the dashboard — replacing manual YAML file editing with a curated form-based editor that mirrors the init wizard's settings structure, with inline validation and visual indicators for non-default values.

**FRs covered:** FR54-FR66 (13 FRs)

### Story 7.1: Settings Page Scaffold & Config Viewing

As a developer,
I want to navigate to a Settings page in the dashboard, select a project, and see all configuration values with their defaults and descriptions,
So that I can review my project's complete configuration in the browser without opening YAML files.

**Acceptance Criteria:**

**Given** the dashboard is loaded
**When** the page renders
**Then** a "Settings" link appears in the header nav bar after "Analytics"
**And** the link uses `hx-get="/settings" hx-target="#main" hx-push-url="/settings"` (FR54)
**And** `g s` keyboard shortcut navigates to the settings page

**Given** the user navigates to `/settings`
**When** the settings page renders
**Then** a project selector dropdown is displayed at the top of the page, populated from `ProjectRegistryManager` (FR55)
**And** the dropdown defaults to the first registered project (or the globally selected project if a project filter is active)
**And** selecting a different project swaps the settings content via `hx-get="/settings?project={path}" hx-target="#settings-content" hx-swap="innerHTML"`

**Given** a project is selected
**When** the settings page loads
**Then** the project's `.adw/project.yaml` is loaded via `ConfigLoader`
**And** all settings are displayed organized in horizontal tab sections: **Basics**, **Git**, **Ports**, **LLM Retry**, **Task Manager**, **Security** (FR56, FR59)
**And** a separate **Phases** tab shows phase-level configuration

**Given** settings are displayed
**When** each field renders
**Then** each field shows: a label (setting name), the current value (or "not set" if absent), the default value in muted text, and a short description of what it controls (FR59)
**And** fields are displayed as read-only text in this story (editing enabled in Story 7.2)

**Given** the settings page is displayed
**When** the user views the page
**Then** an info banner at the top states: "Configuration changes take effect on the next ADW run." (FR65)

**Given** no projects are registered
**When** the user navigates to `/settings`
**Then** an empty state message is shown: "No projects registered. Register a project from the CLI to configure it." with `$ adw global register` hint

**Given** a project is selected but no `.adw/project.yaml` exists
**When** the settings page loads
**Then** all settings display their default values with a note: "No project configuration file found. Defaults shown. Save to create `.adw/project.yaml`."

**Given** the user navigates directly to `/settings` via browser address bar
**When** the server receives the request without `HX-Request` header
**Then** the full HTML page is returned including base shell (dual-response pattern)

**Architecture requirements:**
- Page route in `dashboard/routes.py`: `GET /settings` with dual-response pattern
- Settings content partial in `dashboard/partials.py`: `GET /partials/settings-content` for project switching
- New dependency providers in `dashboard/dependencies.py`:
  - `get_config_loader(project_path) -> ConfigLoader` — loads project config from `.adw/project.yaml`
  - `get_config_registry() -> ConfigRegistry` — provides metadata (defaults, descriptions, types) for all settings
- Template files: `pages/settings.html`, `partials/settings_content.html`, `partials/settings_section_{name}.html` for each tab
- Dashboard module reads from `adw.config` (ConfigLoader, ConfigRegistry) but does NOT import from `cli/wizard/`
- Add "Settings" to nav in `base.html` header
- Add `g s` to keyboard shortcut handler in `base.html`

**UX/Component specifications:**
- Project selector: `select select-bordered` at top of page, full width or left-aligned, matching existing project filter style
- Tab sections: `tabs tabs-box` horizontal tabs (matching analytics time range pattern), one tab per settings group
- Each tab loads its section partial via `hx-get="/partials/settings-section/{section}" hx-target="#section-content"`
- Field layout: `form-control` with `label` above, value display below, description as `text-xs text-base-content/50`
- Info banner: `alert alert-info` at top of settings content area
- Empty state: centered card matching existing empty state pattern
- Responsive: tabs wrap to 2 rows at compact widths (1024-1279px)

**Technical notes:**
- `ConfigRegistry.get_all_settings(section)` provides field metadata (name, type, default, description) — use this to drive the field rendering, not hardcoded field lists
- `ConfigLoader(project_root).load()` returns `ProjectConfig` Pydantic model — extract current values from this
- For projects without `.adw/project.yaml`, `ConfigLoader` returns defaults — this is existing behavior
- Settings page does NOT poll — it's a static view that refreshes on project change or save

---

### Story 7.2: Settings Editing & Save Infrastructure

As a developer,
I want to edit project-level settings (Basics, Git, Ports, LLM Retry) and save changes that persist to disk,
So that I can modify my project configuration from the browser without editing YAML files manually.

**Acceptance Criteria:**

**Given** the settings page is displayed with a project selected
**When** the Basics tab is active
**Then** the following fields are editable:
| Field | Control | Validation |
|-------|---------|------------|
| language | `select` dropdown (python, javascript, go, rust, java, ruby, php) | Required |
| platform | `select` dropdown (cli, web, api) | Required |
| test_command | `input` text field | Optional, string |
| build_command | `input` text field | Optional, string |

**Given** the settings page is displayed
**When** the Git tab is active
**Then** the following fields are editable:
| Field | Control | Validation |
|-------|---------|------------|
| branch_prefix | `input` text field | Must start with letter, end with `/`, alphanumeric/hyphens/underscores/slashes |
| skip_hooks | `toggle` switch | Boolean |
| base_branch | `input` text field | Optional, string |

**Given** the settings page is displayed
**When** the Ports tab is active
**Then** the following fields are editable:
| Field | Control | Validation |
|-------|---------|------------|
| backend_port_start | `input` number field | Range: 1-65535 |
| frontend_port_start | `input` number field | Range: 1-65535 |

**Given** the settings page is displayed
**When** the LLM Retry tab is active
**Then** the following fields are editable:
| Field | Control | Validation |
|-------|---------|------------|
| max_retries | `input` number field | Range: 1-10 |
| base_delay_seconds | `input` number field | Range: 0.1-300.0 |
| max_delay_seconds | `input` number field | Range: 0.1-300.0 |
| multiplier | `input` number field | Range: >1.0, ≤5.0 |

**Given** the user modifies a field value
**When** the field loses focus or the value changes
**Then** client-side validation runs immediately (FR61)
**And** invalid values show a red `text-error text-xs` message below the field
**And** the save button remains disabled while any validation error exists

**Given** the user has made changes and all fields are valid
**When** the user clicks the "Save" button
**Then** the form submits via `hx-post="/settings/save" hx-target="#settings-content"` with CSRF token (NFR9)
**And** the save button shows `loading loading-spinner loading-sm` during submission
**And** the server validates all values via Pydantic model validation (NFR10a)
**And** on success, the server writes `project.yaml` using `YAMLWithComments` generator with atomic writes (FR62, NFR19a)
**And** a success toast appears: `alert alert-success` at `fixed top-16 right-4 w-auto z-50` that auto-dismisses after 3 seconds (FR63)
**And** the settings content refreshes to show the saved values

**Given** the user clicks Save
**When** server-side validation fails (e.g., Pydantic rejects values)
**Then** an error toast appears: `alert alert-error` with the validation error message (FR63)
**And** the form retains the user's input so they can correct and retry

**Given** the project does not have a `.adw/` directory or `project.yaml`
**When** the user saves settings
**Then** the system creates the `.adw/` directory and `project.yaml` file (FR66)
**And** the file is generated using `YAMLWithComments` with all configured values as active YAML and unconfigured values as comments

**Architecture requirements:**
- Save mutation in `dashboard/mutations.py`: `POST /settings/save` with `Depends(validate_csrf)`
- Save endpoint receives form data, constructs a dict, validates via `ProjectConfig.model_validate()`
- On validation success, use `YAMLWithComments` to generate and write `project.yaml`
- Use `atomic_write_config()` pattern (from `config/yaml_generator.py`) for safe file writes (NFR19a)
- Form fields use `name` attributes matching the YAML key path (e.g., `git.branch_prefix`, `llm.retry.max_retries`)
- CSRF token included as `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`
- Each section tab content is a `<form>` element — save submits the active section

**UX/Component specifications:**
- Form controls: `input input-bordered` for text/number, `select select-bordered` for dropdowns, `toggle` for booleans
- Field layout: 2-column grid on wide screens (`grid grid-cols-2 gap-4`), single column at compact widths
- Save button: `btn btn-primary` positioned at bottom-right of each section, with `loading loading-spinner loading-sm` on submit
- Toast: reuse existing HTMX error toast pattern at `fixed top-16 right-4 w-auto z-50`, auto-dismiss via `setTimeout` (~5 lines inline JS)
- Validation errors: `text-error text-xs mt-1` below the input field
- Disabled save: `btn-disabled opacity-50` when validation errors exist

**Technical notes:**
- `YAMLWithComments` generates well-formatted YAML with section headers — no need to preserve existing file contents
- The save endpoint should accept partial updates — only the fields in the submitted section are changed; other sections remain as-is. Load existing config, merge changes, write full file.
- Client-side validation is convenience only — Pydantic validation on the server is the security boundary (NFR10a)
- Toast auto-dismiss: use `htmx:afterSwap` event or a tiny inline script that removes the toast element after 3s

---

### Story 7.3: Complex Field Editors (Task Manager & Security)

As a developer,
I want to configure Task Manager integration (including state mappings) and Security patterns using specialized editors,
So that I can manage complex nested configuration without hand-editing YAML key-value pairs and lists.

**Acceptance Criteria:**

**Given** the settings page is displayed
**When** the Task Manager tab is active
**Then** the following fields are editable:
| Field | Control | Validation |
|-------|---------|------------|
| type | `select` dropdown (none, linear) | Required |
| team_key | `input` text field | 2-10 uppercase letters, shown only when type ≠ none |
| sync_comments | `toggle` switch | Boolean, shown only when type ≠ none |
| auto_close | `toggle` switch | Boolean, shown only when type ≠ none |
| labels_enabled | `toggle` switch | Boolean, shown only when type ≠ none |
| label_prefix | `input` text field | String, shown only when labels_enabled is true |

**Given** Task Manager type is set to "linear"
**When** the state_mapping section renders
**Then** a key-value editor is displayed showing the phase-to-status mapping
**And** the editor shows 5 rows (plan, build, validate, document, ship) + 1 row for "failed"
**And** the key column displays the phase name (read-only)
**And** the value column is an editable `input` text field with the current Linear status (e.g., "In Progress", "In Review", "Done")
**And** default state mapping values are shown as placeholder text

**Given** Task Manager type is set to "none"
**When** the tab renders
**Then** all fields except "type" are hidden (conditional display)
**And** a helper text explains: "Enable a task manager to configure integration settings."

**Given** the settings page is displayed
**When** the Security tab is active
**Then** the following fields are editable:
| Field | Control |
|-------|---------|
| blocked_commands | List editor — each item is a regex pattern string |
| blocked_env_files | List editor — each item is a glob pattern string |

**Given** the blocked_commands list editor is displayed
**When** the user views it
**Then** each existing pattern is shown as an editable `input` text row with a remove (×) button
**And** an "Add Pattern" button appends a new empty row at the bottom
**And** removing the last item leaves an empty list (not null)

**Given** the user removes a pattern from the list
**When** they click the (×) button
**Then** the row is removed from the DOM immediately (client-side)
**And** the change is not persisted until Save is clicked

**Given** the blocked_env_files list editor is displayed
**When** the user interacts with it
**Then** it behaves identically to the blocked_commands list editor
**And** placeholder text shows: e.g., `.env`, `.env.local`, `*.pem`, `*.key`

**Given** the user edits LLM Retry settings (from Story 7.2)
**When** `max_delay_seconds` is set to a value less than `base_delay_seconds`
**Then** a cross-field validation error appears: "Max delay must be ≥ base delay" (FR61)
**And** the save button is disabled

**Given** the user edits Ports settings (from Story 7.2)
**When** backend and frontend port ranges overlap (considering `max_concurrent` of 15)
**Then** a cross-field validation error appears: "Port ranges overlap. Backend {start}-{end} conflicts with Frontend {start}-{end}." (FR61)
**And** the save button is disabled

**Architecture requirements:**
- Conditional field display: use HTMX swap on Task Manager `type` change — `hx-get="/partials/settings-section/task-manager?type={value}" hx-target="#task-manager-fields"` to re-render the section with correct visibility
- Key-value editor: server-rendered rows with `name="task_manager.state_mapping.{phase}"` for each row
- List editor: dynamically add/remove rows client-side using a minimal inline script (~10 lines) that clones a template row; rows use indexed names like `security.blocked_commands.0`, `security.blocked_commands.1`, etc.
- Cross-field validation runs client-side on field change and server-side on save
- Save endpoint (from Story 7.2) already handles full form submission — no new endpoint needed

**UX/Component specifications:**
- Key-value editor: `table table-sm` with `th` for phase names and `td` containing `input input-bordered input-sm`
- List editor: `flex flex-col gap-2`, each row is `flex gap-2` with `input input-bordered flex-1` and `btn btn-ghost btn-sm btn-circle` for remove (×)
- "Add" button: `btn btn-ghost btn-sm` with `+` icon, below the list
- Conditional sections: hidden/shown via `hx-swap` on type change, not CSS toggle (server decides what to render)
- Cross-field errors: displayed as `alert alert-error alert-sm` between the related fields

**Technical notes:**
- State mapping defaults (from wizard): plan → "In Progress", build → "In Progress", validate → "In Review", document → "In Review", ship → "Done", failed → "In Progress"
- List editor row addition uses a `<template>` element cloned by a tiny inline script — no framework needed
- Cross-field validation for ports requires knowing `max_concurrent` (default 15) to calculate range end

---

### Story 7.4: Phase Config Editor

As a developer,
I want to view and edit configuration for each of the 5 ADW phases (plan, build, validate, document, ship) including phase-specific settings,
So that I can fine-tune timeouts, LLM models, and deployment settings per phase without editing individual config.yaml files.

**Acceptance Criteria:**

**Given** the settings page is displayed
**When** the user clicks the "Phases" tab
**Then** a sub-tab row is displayed with 5 phase tabs: Plan, Build, Validate, Document, Ship
**And** the first phase (Plan) is selected by default
**And** each phase tab loads its config via `hx-get="/partials/settings-phase/{phase}?project={path}" hx-target="#phase-content"`

**Given** a phase tab is selected
**When** the phase config section renders
**Then** the following base fields are displayed for all phases (FR57):
| Field | Control | Validation | Default |
|-------|---------|------------|---------|
| enabled | `toggle` switch | Boolean | true |
| timeout_seconds | `input` number field | Positive integer | Varies by phase (plan: 900, build: 1800, validate: 900, document: 900, ship: 1200) |
| llm.model | `select` dropdown (opus, sonnet, haiku) | Required | Varies by phase (plan: opus, build: sonnet, validate: opus, document: haiku, ship: sonnet) |

**Given** a phase tab is selected
**When** the phase has `input_files` configured
**Then** a key-value editor is displayed showing variable name → file path mappings
**And** the user can add, edit, and remove input_files entries
**And** each row has: variable name `input` + file path `input` + remove (×) button

**Given** the Document phase tab is selected
**When** the phase config renders
**Then** an additional "Doc Mappings" section is shown (FR58)
**And** each doc mapping row has: `source_pattern` input (glob, e.g., `src/**/*.py`) + `docs_dir` input (directory path) + remove (×) button
**And** an "Add Mapping" button appends a new empty row

**Given** the Ship phase tab is selected
**When** the phase config renders
**Then** additional ship-specific fields are shown (FR58):
| Field | Control | Validation |
|-------|---------|------------|
| commands.version_bump | `input` text field | Optional, shell command string |
| commands.publish | `input` text field | Optional, shell command string |
| bypass_ci | `toggle` switch | Boolean, default: true |

**Given** the user edits phase settings and clicks Save
**When** the form submits
**Then** the save endpoint writes the phase config to `.adw/commands/{phase}/config.yaml` using `YAMLWithComments`
**And** if the config file doesn't exist, it is created along with the directory structure (FR66)
**And** a success toast appears confirming the save

**Given** a phase is disabled via the toggle
**When** the toggle is switched off
**Then** the remaining fields in that phase section are visually dimmed (`opacity-50`) but remain visible
**And** the disabled state is saved when the user clicks Save

**Given** a phase config file doesn't exist yet
**When** the phase tab loads
**Then** all fields show their default values
**And** a note appears: "Using defaults. Save to create phase config file."

**Architecture requirements:**
- Phase config partials in `dashboard/partials.py`: `GET /partials/settings-phase/{phase}` returns the form for a specific phase
- Phase config loading: use `CommandConfig` subclass resolution via `get_config_class(phase)` to load the correct model (ValidateCommandConfig, ShipCommandConfig, DocumentCommandConfig, or base CommandConfig)
- Phase config save: extend the save mutation to handle `POST /settings/phase/{phase}/save` — validates via the phase-specific Pydantic model, writes to `.adw/commands/{phase}/config.yaml`
- Directory creation: `os.makedirs(project_root / ".adw" / "commands" / phase, exist_ok=True)` before writing

**UX/Component specifications:**
- Phase sub-tabs: `tabs tabs-box tabs-sm` inside the main Phases tab content area
- Phase icons: optional — Plan (pencil), Build (hammer), Validate (check), Document (book), Ship (rocket) — or just text labels
- Disabled phase: entire form section gets `opacity-50 pointer-events-none` except the enabled toggle
- Input files / doc mappings: same list editor component as Security blocked_commands (Story 7.3), but with 2 columns per row
- Ship commands: standard text inputs with `font-mono` for shell command appearance

**Technical notes:**
- Phase config resolution: check `.adw/commands/{phase}/config.yaml` first (project-level), fall back to bundled defaults
- `get_config_class(phase)` from `adw.commands.loader` maps phase names to the correct Pydantic model: "validate" → `ValidateCommandConfig`, "ship" → `ShipCommandConfig`, "document" → `DocumentCommandConfig`, others → `CommandConfig`
- Default timeout and model values per phase come from the wizard's phase defaults — these should be sourced from `ConfigRegistry` or hardcoded in the template as defaults
- Each phase has its own save button — phases are saved independently (not all at once)

---

### Story 7.5: Reset to Defaults, Changed Indicators & Validation Polish

As a developer,
I want to see which settings I've changed from defaults, reset individual fields back to their defaults, and have complete inline validation across all fields,
So that I have full confidence in my configuration and can easily undo changes.

**Acceptance Criteria:**

**Given** the settings page is displayed with a project's config loaded
**When** a field's current value differs from its default value
**Then** the field label shows a small accent indicator (colored dot or bold weight) to signal it's been customized (FR60)
**And** the default value is shown as `text-xs text-base-content/50` below the input: "Default: {value}"

**Given** a field has been changed from its default
**When** the user views the field
**Then** a small reset button (↺ icon, `btn btn-ghost btn-xs`) appears next to the field label (FR64)
**And** clicking the reset button immediately sets the field value back to its default
**And** the accent indicator disappears
**And** the reset is a client-side change — not persisted until Save is clicked

**Given** a field is at its default value
**When** the user views the field
**Then** no accent indicator or reset button is shown
**And** the default value hint is still displayed

**Given** the user is editing settings
**When** they change a field value in real-time
**Then** the accent indicator and reset button update immediately (client-side) to reflect whether the value matches the default

**Given** cross-field validation rules exist
**When** the user edits related fields
**Then** all cross-field validations run on every change:
- LLM Retry: `max_delay_seconds >= base_delay_seconds`
- Ports: backend and frontend ranges must not overlap (considering max_concurrent)
- Port values: must not exceed 65535 when combined with max_concurrent
**And** cross-field errors are shown between the related fields as `alert alert-warning text-sm`

**Given** a field has a specific type constraint
**When** the user enters an invalid value
**Then** validation runs on blur (for text fields) or on change (for selects/toggles):
- Number fields: reject non-numeric input, enforce min/max range
- Text fields: enforce pattern (e.g., branch_prefix must end with `/`)
- Required fields: show "This field is required" if empty
**And** the validation message appears as `text-error text-xs` immediately below the field

**Given** the settings page loads for a section
**When** there are fields with current values that differ from defaults
**Then** a section-level summary shows: "{N} settings customized" in `text-xs text-base-content/50` next to the section tab label

**Given** the user navigates away from the settings page with unsaved changes
**When** they click a nav link or use a keyboard shortcut
**Then** no unsaved-changes warning is shown (out of scope — keep it simple for MVP)

**Architecture requirements:**
- Default values sourced from `ConfigRegistry.get_all_settings(section)` — each setting entry includes `default` field
- Changed-from-default comparison: done server-side when rendering the section partial (pass `is_default: bool` per field in template context)
- Reset is client-side only (JavaScript sets the input value to the default stored in a `data-default` attribute)
- Cross-field validation: implemented as inline `<script>` in the section partial (~15-20 lines per section)
- Section summary count: computed server-side, rendered in the tab label

**UX/Component specifications:**
- Changed indicator: `badge badge-xs badge-primary` dot before the field label, or `font-semibold` on the label text
- Reset button: `btn btn-ghost btn-xs` with `↺` icon, positioned inline after the label
- Default hint: `text-xs text-base-content/50 mt-0.5` below the input: "Default: {value}"
- Section summary: `badge badge-sm badge-ghost` inside the tab label: e.g., "Git (2)"
- Cross-field errors: `alert alert-warning py-1 px-2 text-xs` between related field groups
- Field-level errors: `text-error text-xs mt-1` directly below the input

**Technical notes:**
- Each input element carries `data-default="{default_value}"` for client-side comparison
- The inline reset script: `input.value = input.dataset.default; input.dispatchEvent(new Event('change'))`
- Changed count per section: `sum(1 for field in section_fields if current_value != default_value)` computed in the route handler
- No `beforeunload` warning for unsaved changes — keeping MVP simple
- Validation script should be a reusable function defined once in `base.html` or a static JS file, invoked per-section with field configs
