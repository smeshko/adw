---
title: Conditional Documentation Guide
description: Find documentation based on your current task
author: ADW Team
date: 2026-01-25
---

# Conditional Documentation Guide

This guide helps you find relevant documentation based on what you're working on.

## Instructions

- Review the task you need to perform
- Check the conditions below
- Read the relevant documentation before proceeding
- Only read documentation if conditions match your task

## Documentation Map

- docs/architecture/adrs/ADR-001-test-reduction-strategy.md
  - Conditions:
    - When writing new unit tests
    - When adding tests to existing test files
    - When reviewing test code
    - When deciding whether a test is worth writing
    - When consolidating redundant tests
    - When auditing test quality

- docs/testing/TEST_REDUCTION_PLAN.md
  - Conditions:
    - When understanding which test categories are considered waste
    - When identifying tests for deletion or consolidation
    - When reviewing test file structure

- README.md
  - Conditions:
    - When first understanding the project structure
    - When learning commands to run the application
    - When setting up the development environment

- _bmad-output/architecture.md
  - Conditions:
    - When understanding the overall system design
    - When adding new modules or packages
    - When modifying core abstractions

- _bmad-output/prd.md
  - Conditions:
    - When understanding product requirements
    - When implementing new features
    - When prioritizing work

- _bmad-output/index.md
  - Conditions:
    - When navigating project documentation
    - When looking for specific documentation files
    - When onboarding to the project

- _bmad-output/project-overview.md
  - Conditions:
    - When getting a high-level understanding of the project
    - When reviewing project metrics and capabilities
    - When explaining the project to others

- _bmad-output/architecture-summary.md
  - Conditions:
    - When understanding the layered architecture
    - When reviewing data flow between components
    - When adding new integration points

- docs/arch-high-level.md
  - Conditions:
    - When understanding system-level architecture
    - When reviewing component relationships

- docs/arch-orchestrator.md
  - Conditions:
    - When modifying the orchestration engine
    - When adding new phases to the pipeline

- docs/arch-phase-pipeline.md
  - Conditions:
    - When working with phase execution
    - When adding or modifying pipeline behavior

- _bmad-output/development-guide.md
  - Conditions:
    - When setting up the development environment
    - When learning development commands (test, lint, build)
    - When adding new features or commands
    - When debugging issues
    - When adding new CLI commands
    - When modifying command arguments or flags
    - When working with Typer integration

- _bmad-output/source-tree-analysis.md
  - Conditions:
    - When navigating the codebase
    - When understanding module purposes
    - When adding new modules or packages
    - When locating entry points

- _bmad-output/api-contracts-root.md
  - Conditions:
    - When working with the webhook server
    - When adding new API endpoints
    - When integrating external providers (GitHub, Linear)
    - When modifying webhook behavior

- _bmad-output/data-models-root.md
  - Conditions:
    - When adding new Pydantic models
    - When modifying existing model schemas
    - When understanding model relationships
    - When working with configuration models

- docs/architecture/adrs/
  - Conditions:
    - When working with secret redaction
    - When modifying dangerous command patterns
    - When implementing security interceptors

- docs/planning/sprint-status.md
  - Conditions:
    - When checking current sprint progress
    - When updating story status
    - When planning next work items

- _bmad-output/epics/index.md
  - Conditions:
    - When reviewing implementation epics
    - When planning story work
    - When understanding feature scope

- docs/features/dashboard-base-template-navigation-theme.md
  - Conditions:
    - When adding a new page route to the dashboard
    - When implementing HTMX partial endpoints for the dashboard
    - When modifying the dashboard navigation header or status bar footer
    - When working with the dashboard theme toggle or design tokens
    - When troubleshooting the dashboard dual-response pattern (full page vs HTMX partial)

- docs/features/stat-cards-status-vocabulary.md
  - Conditions:
    - When adding or modifying stat cards on the dashboard overview page
    - When rendering run status badges anywhere in the dashboard
    - When adding new status types to the ADW status vocabulary
    - When implementing trend comparison data for dashboard statistics
    - When creating new HTMX polling partials that refresh via OOB swap

- docs/features/cost-strip-empty-states-error-handling.md
  - Conditions:
    - When adding or modifying the cost summary strip on the dashboard overview
    - When implementing empty states for new dashboard sections
    - When adding error banners or error resilience to dashboard data loading
    - When working with the HTMX error toast or retry mechanism
    - When implementing 404 or not-found handling for dashboard resources

- docs/features/recent-runs-project-breakdown.md
  - Conditions:
    - When adding data tables with HTMX polling to the dashboard overview
    - When implementing project filter behavior for dashboard sections
    - When creating clickable card layouts with DaisyUI for the dashboard
    - When building partial routes that share context builders with full page routes

- docs/features/active-runs-phase-pipeline.md
  - Conditions:
    - When adding real-time polling sections to the dashboard overview
    - When displaying phase progression for ADW runs in the dashboard
    - When implementing new HTMX partial endpoints with empty-state polling patterns
    - When using the phase pipeline component macro in dashboard templates
    - When loading RunContext data in dashboard partials with fallback handling

- docs/features/analytics-time-range-stat-cards.md
  - Conditions:
    - When adding new stat cards or metrics to the analytics page
    - When implementing time-range filtering for analytics data
    - When computing period-over-period delta comparisons for dashboard statistics
    - When adding bookmarkable HTMX tab navigation with query parameter preservation
- docs/features/runs-list-pagination-sorting.md
  - Conditions:
    - When adding a new paginated list page to the dashboard
    - When implementing sort or filter controls with HTMX in the dashboard
    - When using the triple-response pattern (full page / partial / table-only) for dashboard routes
    - When building DaisyUI join-based pagination with HTMX for the dashboard
    - When adding paginated query methods to the IndexManager
- docs/features/new-run-modal-form-submission.md
  - Conditions:
    - When adding new modal dialogs to the ADW dashboard
    - When creating CSRF-protected form submission endpoints in the dashboard
    - When extracting shared logic from webhook module to core for dashboard use
    - When implementing HTMX form validation with inline error re-rendering in the dashboard
    - When triggering ADW runs programmatically from new entry points
- docs/features/run-detail-page-layout-metadata.md
  - Conditions:
    - When implementing a new detail or drill-down page in the dashboard
    - When loading RunContext data for enriched display on dashboard run detail pages
    - When adding context-aware back navigation between dashboard pages
    - When displaying full metadata cards with clipboard copy functionality in the dashboard
- docs/features/runs-filter-bar-status-project-date.md
  - Conditions:
    - When adding filter controls to dashboard list pages
    - When implementing HTMX filter bars that persist across table-only swaps
    - When combining multiple filter params with hx-include for HTMX requests
    - When adding "Clear all" reset functionality to filtered dashboard views
    - When syncing filter state between global header controls and page-level filters
- docs/features/rerun-flow.md
  - Conditions:
    - When implementing re-run or retry functionality for dashboard runs
    - When pre-populating modal forms with data from existing records in the dashboard
    - When using disabled form elements with hidden input workarounds in HTMX forms
    - When preserving form state across validation error re-rendering in the dashboard

- docs/features/phase-accordion-artifact-viewer.md
  - Conditions:
    - When adding lazy-loaded HTMX accordion sections to the dashboard
    - When implementing artifact browsing or file viewing in the ADW dashboard
    - When adding new phase detail routes with security validation for the dashboard
    - When rendering user-supplied markdown content safely in the dashboard
    - When extending the run detail page with new expandable sections

- docs/features/llm-interaction-log-viewer.md
  - Conditions:
    - When adding LLM prompt or response viewers to the ADW dashboard
    - When implementing log search or filtering functionality in the dashboard
    - When building HTMX debounced multi-filter controls for the dashboard
    - When parsing or displaying ADW live.log content in the dashboard
    - When loading LLM token statistics from run response JSON files
- docs/features/abort-active-run.md
  - Conditions:
    - When implementing destructive action confirmation modals in the ADW dashboard
    - When adding abort or interruption functionality to ADW runs
    - When using OOB swaps to clear modal containers after HTMX form submission
    - When performing dual status validation (index + RunContext) for run operations
- docs/features/daily-usage-chart-breakdown-panels.md
  - Conditions:
    - When adding new chart visualizations to the analytics page
    - When implementing breakdown panels for the analytics dashboard
    - When extending the StatsAggregator with new aggregation methods
    - When computing server-side bar heights for CSS-only charts
    - When adding new phase or model tracking to the ADW pipeline

- docs/features/budget-section-breakdown-table.md
  - Conditions:
    - When adding budget tracking or spending limits to the ADW analytics page
    - When implementing server-side sortable tables with HTMX in the dashboard
    - When using the `analytics_url` macro to preserve query parameters across analytics interactions
    - When configuring the `ADW_MONTHLY_BUDGET` environment variable
    - When adding new columns or sort options to the analytics breakdown table

- docs/features/active-failed-run-sse-streaming.md
  - Conditions:
    - When adding SSE streaming endpoints to the ADW dashboard
    - When implementing real-time log tailing for active runs in the dashboard
    - When rendering OOB (out-of-band) swap HTML fragments for live HTMX updates
    - When implementing failed run diagnostics with auto-expanded accordions in the dashboard
    - When using `overflow-anchor` CSS for auto-scrolling streaming content
- docs/features/keyboard-shortcuts-navigation-overlay.md
  - Conditions:
    - When adding new keyboard shortcuts to the ADW dashboard
    - When implementing j/k list navigation for new table views in the dashboard
    - When modifying the keyboard shortcut overlay modal content
    - When adding two-key sequence shortcuts (g-prefix pattern) to the dashboard
    - When using the `data-navigable-row` attribute for keyboard-navigable lists

- docs/features/terminal-focus-view-modes.md
  - Conditions:
    - When adding a new view mode or alternate display layout to the ADW dashboard
    - When implementing keyboard-toggled UI modes in the dashboard
    - When reusing SSE streams in new dashboard view contexts
    - When adding mode-specific CSS styling with theme variable integration in the dashboard
    - When implementing Escape-key exit hierarchies for modal/mode layering in the dashboard

- docs/features/settings-page-config-viewing.md
  - Conditions:
    - When adding new editable config sections or tabs to the Settings page
    - When implementing HTMX form save endpoints with CSRF validation in the dashboard
    - When using the load-merge-validate-write pattern for project.yaml modifications
    - When adding toast notifications via HTMX OOB swap in the dashboard
    - When mapping flat form field names to nested config paths in the dashboard
    - When integrating ConfigLoader or ConfigRegistry in new dashboard routes
    - When displaying project config field metadata with defaults and descriptions

- docs/features/complex-field-editors-task-manager-security.md
  - Conditions:
    - When adding new complex field editors (key-value or list) to the Settings page
    - When implementing HTMX conditional partial swaps for type-dependent form fields in the dashboard
    - When collecting indexed or mapping form fields from Starlette FormData in the dashboard
    - When adding cross-field validation rules to Settings form sections
    - When editing Task Manager integration or Security blocked patterns configuration

- docs/features/phase-config-editor.md
  - Conditions:
    - When adding or modifying phase-specific configuration editors on the Settings page
    - When implementing per-phase config save to `.adw/commands/{phase}/config.yaml`
    - When using the key-value pair editor pattern with `addKVRow()`/`reindexKV()` in dashboard templates
    - When extending phase config models or adding new phase-specific fields
    - When working with `PHASE_DEFAULTS` or `get_config_class()` for phase configuration

- docs/features/reset-defaults-changed-indicators-validation.md
  - Conditions:
    - When adding reset-to-default functionality to settings fields
    - When implementing changed-from-default indicators on the Settings page
    - When extending client-side validation in Settings forms
    - When computing changed-count badges for settings tab labels
    - When adding dynamic accent dot or reset button UI patterns to editable fields
