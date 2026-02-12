# Epic List

## Epic 1: Dashboard Foundation & Live Overview
User can launch the web dashboard from the CLI and see a comprehensive, auto-refreshing overview of all ADW activity — aggregate stats, active runs with phase progression, recent runs, per-project breakdown, and cost summary — with dark theme, responsive layout, and HTMX-powered navigation.

**FRs covered:** FR1-FR11, FR42-FR44, FR45-FR53 (27 FRs)

**Architecture scope:** Shared server factory (`server/app.py`, `config.py`, `middleware.py`), dashboard module scaffold (`routes.py`, `partials.py`, `dependencies.py`, `error_handlers.py`), template hierarchy (`base.html`, pages, partials, components), static assets (vendored HTMX, `dashboard.css`), CLI command (`cli/dashboard_web.py`), dual-response pattern, polling partials, DaisyUI + Tailwind via CDN, Jinja2 dependency.

**UX scope:** Persistent header (nav, project filter, theme toggle), overview page (stat cards, active run cards with mini phase pipeline, recent runs table, project cards, cost summary strip), footer/status bar, empty states (no projects, no runs), loading indicators, status design vocabulary, typography rules, responsive behavior, dark theme with localStorage persistence, CSS animations (phase-pulse, HTMX transitions), custom CSS properties.

## Epic 2: Run Detail & Deep Inspection
User can deep-dive into any run to see full metadata, phase-by-phase progression, browse artifacts inline, view LLM prompt/response exchanges, and search/stream logs — enabling the full "Debug Detective" workflow for understanding what happened in any run.

**FRs covered:** FR16-FR27 (12 FRs)

**Architecture scope:** Run detail page route with dual-response, lazy-loaded partials (`phase_detail.html`, `artifact_viewer.html`, `log_viewer.html`, `llm_viewer.html`), SSE streams (`/runs/{id}/events`, `/runs/{id}/logs/stream`), reusable components (`phase_pipeline.html`, `status_badge.html`).

**UX scope:** Run header (context-aware back link, status badge, action buttons placeholder), full-width phase pipeline with per-phase duration, metadata card (2-column grid, copy button for run ID, PR/Linear links), phase accordion with lazy-loaded sub-sections (hooks, artifacts, LLM interaction, logs), log viewer (search, severity filter, phase filter, streaming for active runs), failed run variant (auto-expand failed phase, error alert, pre-filter ERROR logs), active run variant (pulsing indicator, SSE elapsed time, streaming logs).

## Epic 3: Run Management
User can start new runs, abort active runs, and re-run previous runs directly from the browser — transforming the dashboard from a monitoring tool into a full command center.

**FRs covered:** FR12-FR15 (4 FRs)

**Architecture scope:** Extract `core/run_trigger.py` from `webhook/runner.py`, refactor `webhook/server.py` to use shared factory, `dashboard/mutations.py` (POST endpoints), CSRF token generation and validation in `dependencies.py`, new run and abort modals in partials.

**UX scope:** New Run modal (project select populated from registry, feature textarea, CSRF hidden input, loading spinner on submit, server-side validation with inline errors), re-run variant (pre-populated project + feature from previous run), abort confirmation modal (warning styling, run ID, current phase, cancel + abort buttons), action buttons on run detail page (Abort for active, Re-run for all).

## Epic 4: Runs List & Filtering
User can browse, filter, sort, and paginate through their complete run history across all projects — enabling efficient navigation of large run histories.

**FRs covered:** FR28-FR31 (4 FRs)

**Architecture scope:** Runs list page route with dual-response, `runs_table.html` partial for HTMX filter/sort/page swaps, query param handling for filters.

**UX scope:** Runs list page with "New Run" button, filter bar (status dropdown, project dropdown, date from/to inputs), summary line (count + sort dropdown), zebra table with row click navigation, pagination (15/page, DaisyUI join component), "Clear all filters" link, empty state for no filter matches.

## Epic 5: Cost & Token Analytics
User can analyze token usage and costs with time-range filtering, daily usage charts, and breakdowns by project, phase, and model — providing full visibility into ADW resource consumption.

**FRs covered:** FR32-FR38 (7 FRs)

**Architecture scope:** Analytics page route with dual-response, `analytics_content.html` partial for time-range swaps, CSS-only chart components (`chart_bar.html`), server-side percentage calculations.

**UX scope:** Time range tabs (7d/30d/90d/all, DaisyUI tabs-boxed), stat cards with delta indicators, stacked daily usage bar chart (CSS-only, input/output token segments, day labels, legend), by-project horizontal bar breakdown (clickable for project filter), by-phase horizontal bar breakdown, by-model breakdown, budget section (progress bar, color-coded by usage level), detailed breakdown table (per-project metrics, sortable columns).

## Epic 6: View Modes & Keyboard Navigation
Power users can navigate the dashboard with keyboard shortcuts, toggle terminal mode for raw log output, and enter focus mode for dedicated single-run monitoring — optimizing the dashboard for keyboard-driven developer workflows.

**FRs covered:** FR39-FR41 (3 FRs)

**Architecture scope:** Inline JavaScript (~30 lines) for keyboard event handling, CSS classes for terminal mode and focus mode in `dashboard.css`, `keyboard_help.html` component.

**UX scope:** Keyboard shortcut overlay (`?` toggle, DaisyUI modal with `kbd` badges), navigation shortcuts (`g h/r/a`), list navigation (`j/k`, `Enter` to open), action shortcuts (`n` new run, `/` search focus, `r` refresh, `Esc` close/back), terminal mode (monospace scrolling view), focus mode (replaces dashboard with single-run live view).

## Epic 7: Settings & Configuration
User can view, edit, validate, and save project and phase configuration for any registered project directly from the dashboard — replacing manual YAML file editing with a curated form-based editor that mirrors the init wizard's settings structure, with inline validation and visual indicators for non-default values.

**FRs covered:** FR54-FR66 (13 FRs)

**Architecture scope:** New page route (`/settings`) with dual-response, settings section partials for tab swaps, save mutation endpoint in `mutations.py`, new `Depends()` providers for `ConfigLoader` and `ConfigRegistry`, `pages/settings.html`, `partials/settings_*.html` section forms, Pydantic validation on save, atomic YAML writes via `YAMLWithComments`.

**UX scope:** Settings nav link + `g s` keyboard shortcut, project selector dropdown, tabbed sections for project-level settings (Basics, Git, Ports, Task Manager, LLM Retry, Security), phase config tabs with per-phase forms, form controls (inputs, selects, toggles, list editors, key-value editor for state_mapping), inline validation with error text, changed-from-default indicators, save button with loading spinner, success/error toast, reset-to-default per-field buttons.
