# Conditional Documentation

This file lists documentation that should be read under specific conditions. When working on certain parts of the codebase, consult the relevant documentation to ensure consistency and adherence to established patterns.

---

## Architecture Decision Records

- docs/architecture/adrs/ADR-001-test-reduction-strategy.md
  - Conditions:
    - When writing new unit tests
    - When adding tests to existing test files
    - When reviewing test code
    - When deciding whether a test is worth writing
    - When consolidating redundant tests
    - When auditing test quality

---

## Testing Documentation

- docs/testing/TEST_REDUCTION_PLAN.md
  - Conditions:
    - When understanding which test categories are considered waste
    - When identifying tests for deletion or consolidation
    - When reviewing test file structure

---

## Core Documentation

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

---

## Project Documentation Index

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

---

## Architecture Documentation

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

---

## Development Documentation

- _bmad-output/development-guide.md
  - Conditions:
    - When setting up the development environment
    - When learning development commands (test, lint, build)
    - When adding new features or commands
    - When debugging issues

- _bmad-output/source-tree-analysis.md
  - Conditions:
    - When navigating the codebase
    - When understanding module purposes
    - When adding new modules or packages
    - When locating entry points

---

## API and Data Model Documentation

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

---

## CLI Documentation

- _bmad-output/development-guide.md (CLI section)
  - Conditions:
    - When adding new CLI commands
    - When modifying command arguments or flags
    - When working with Typer integration

---

## Security Documentation

- docs/architecture/adrs/ (security-related ADRs)
  - Conditions:
    - When working with secret redaction
    - When modifying dangerous command patterns
    - When implementing security interceptors

---

## Sprint and Planning

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
