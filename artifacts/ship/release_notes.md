## [Unreleased] - 2026-02-11

### Added
- Add daily token breakdown to stats aggregator
- Create cost summary strip template
- Add cost strip context builder and wire into overview route
- Add new run button and rewrite overview template
- Verify no-projects empty state (task 5)
- Verify no-runs empty state (task 6)
- Enhance htmx error toast with retry link
- Implement 404 run not found page
- Verify overview template wiring (task 10)

### Fixed
- Add error resilience to page context builder
- Harden error toast against XSS and fix data-error empty state logic
- Strengthen test assertions for daily token bucketing and date labels

### Documentation
- Add feature doc for cost strip, empty states, and error handling

### Other
- Add unit tests for cost strip, empty states, and error handling (task 11)
