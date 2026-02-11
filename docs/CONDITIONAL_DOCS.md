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
