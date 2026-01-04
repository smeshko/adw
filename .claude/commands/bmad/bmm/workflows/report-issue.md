---
description: Capture, document, and route QA issues found during manual testing
argument-hint: "<description> | Example: /report-issue \"App crashes when clicking extract button\""
---

## Report QA Issue

Document a QA issue with structured tracking and automatic routing based on severity.

### Quick Start

If `$ARGUMENTS` is provided, use it as the initial issue description to speed up capture.

### Workflow Execution

Load and execute the report-issue workflow:

1. Load workflow configuration: `.bmad/bmm/workflows/4-implementation/report-issue/workflow.yaml`
2. Load workflow instructions: `.bmad/bmm/workflows/4-implementation/report-issue/instructions.xml`
3. Execute the workflow steps

### What This Workflow Does

1. **Initialize** - Loads sprint-status.yaml, gets next issue number
2. **Capture** - Prompts for severity, type, component, description, repro steps, evidence
3. **Document** - Creates issue file in `docs/sprint-artifacts/issues/`, copies screenshots/logs to assets
4. **Route** - Based on severity:
   - **Critical**: Adds `bugfix-ISS-XXX` to development_status, prompts to create story
   - **Major**: Adds `ux-fix-ISS-XXX` to development_status, prompts to create story
   - **Minor**: Logs to issues backlog only

### Output Files

- Issue file: `docs/sprint-artifacts/issues/ISS-{number}-{slug}.md`
- Evidence: `docs/sprint-artifacts/issues/assets/ISS-{number}-*`
- Tracking: Updated `sprint-status.yaml`

### Integration

- Links to `/bmad:bmm:workflows:create-story` for Critical/Major issues
- Links to `/bmad:bmm:workflows:dev-story` for implementing fixes
- Links to `/codex-review` for code review
