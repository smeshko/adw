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

- docs/architecture/architecture.md
  - Conditions:
    - When understanding the overall system design
    - When adding new modules or packages
    - When modifying core abstractions

- docs/product/prd.md
  - Conditions:
    - When understanding product requirements
    - When implementing new features
    - When prioritizing work

---

## CLI Documentation

- src/adw/cli/README.md (if exists)
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

## Evidence Collection

- src/adw/evidence/README.md (if exists)
  - Conditions:
    - When adding new evidence capture methods
    - When working with mobile screenshots
    - When implementing API response capture

---

## Sprint and Planning

- docs/planning/sprint-status.md
  - Conditions:
    - When checking current sprint progress
    - When updating story status
    - When planning next work items
