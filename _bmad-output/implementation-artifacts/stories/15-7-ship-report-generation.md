# Story 15.7: Ship Report Generation

Status: ready-for-dev
Linear Issue: not-configured
Epic: 15 - Ship Phase & Deployment
Created: 2026-01-18

---

## Story

As a developer,
I want a comprehensive ship report as an artifact,
So that I have a record of what was deployed and how.

## Acceptance Criteria

**Given** ship phase completes (success or failure)
**When** report generated
**Then** it includes structured fields for post.sh parsing:
```
DEPLOYMENT_STATUS: SUCCESS | FAILED | BLOCKED
PR_MERGE_APPROVED: true | false
VERSION_DEPLOYED: x.y.z | N/A
PR_NUMBER: 123
```

**Given** report is generated
**When** saved as artifact
**Then** `ship_report.md` contains:
- Pre-flight summary with risk assessment
- Execution log (commands and results)
- Release notes
- Failure analysis (if applicable)
- Verification recommendations

**Given** ship phase completes
**When** artifacts captured
**Then** config.yaml defines:
```yaml
artifacts:
  - name: ship_report
    pattern: "ship_report.md"
    required: true
  - name: release_notes
    pattern: "release_notes.md"
    required: false
```

## Tasks / Subtasks

### Task 1: Define Report Generation Instructions (Final step in instructions.xml)
- [x] Create final step in `ship/instructions.xml` for report generation
- [x] Compile all information from prior steps
- [x] Generate comprehensive markdown report
- [x] Include structured fields at top for parsing

### Task 2: Implement Structured Status Section
- [x] Always include at report top:
  ```markdown
  DEPLOYMENT_STATUS: SUCCESS
  PR_MERGE_APPROVED: true
  VERSION_DEPLOYED: 1.2.3
  PR_NUMBER: 456
  ```
- [x] Use exact format (field: value) for post.sh parsing
- [x] Valid DEPLOYMENT_STATUS values: SUCCESS, FAILED, BLOCKED
- [x] VERSION_DEPLOYED: actual version or "N/A"

### Task 3: Implement Pre-Flight Summary Section
- [x] Include from step 2 analysis:
  - Risk level (LOW/MEDIUM/HIGH)
  - Risk justification
  - Breaking changes detected
  - Security-sensitive changes
  - PR state summary

### Task 4: Implement Execution Log Section
- [x] Include from step 3 execution:
  - Commands executed (or "No commands configured")
  - Each command's result (success/failure)
  - Output summaries (not full logs)
  - Timing information if available
  - Post-publish hook results

### Task 5: Implement Release Notes Section
- [x] Include full release notes from step 4
- [x] Or indicate "Release notes generation skipped" if not applicable
- [x] Reference artifact file: `release_notes.md`

### Task 6: Implement Failure Analysis Section (Conditional)
- [x] Only include if `DEPLOYMENT_STATUS: FAILED`
- [x] Include from step 5 diagnosis:
  - Failed command identification
  - Error output
  - Diagnosis explanation
  - Remediation steps
  - Recovery path

### Task 7: Implement Verification Section
- [x] Provide post-deployment verification recommendations:
  - If publish succeeded: check package registry
  - If version bumped: verify git tags
  - If PR merged: confirm branch deleted
  - General: smoke test recommendations

### Task 8: Implement Artifact Configuration
- [x] Verify config.yaml defines ship_report artifact
- [x] Mark ship_report as required (phase fails without it)
- [x] Mark release_notes as optional
- [x] Verify artifact patterns match generated files

### Task 9: Write Tests
- [ ] Test structured fields format
- [ ] Test pre-flight section generation
- [ ] Test execution log section
- [ ] Test release notes inclusion
- [ ] Test failure analysis conditional
- [ ] Test verification recommendations
- [ ] Test artifact creation
- [ ] Test required artifact validation

---

## Dependencies

- **Depends On:** 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
- **Blocks:** None (final story)
- **Can Parallel With:** None

### Dependency Rationale
- Requires all prior stories to compile full report
- Pre-flight summary from 15.2
- Execution log from 15.3
- Release notes from 15.4
- Failure analysis from 15.5
- Final status from 15.6

---

## Developer Context

### Technical Requirements

1. **Report Structure**
   - Structured fields at top for machine parsing
   - Human-readable sections below
   - Markdown format for easy reading
   - Comprehensive but not verbose

2. **Artifact Requirements**
   - ship_report.md is REQUIRED
   - release_notes.md is OPTIONAL
   - Stored in `.adw/runs/{run_id}/artifacts/ship/`

3. **Status Field Format**
   - Exact format for grep parsing
   - Field name, colon, space, value
   - One field per line
   - No additional formatting

### Architecture Compliance

**Modified Files:**
```
src/adw/defaults/commands/ship/config.yaml       # Artifact definitions
src/adw/defaults/commands/ship/ship/instructions.xml  # Final step
```

**Artifact Location:**
```
.adw/runs/{run_id}/artifacts/ship/ship_report.md
.adw/runs/{run_id}/artifacts/ship/release_notes.md
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| None | - | Pure markdown generation |

### File Structure Requirements

**config.yaml Artifact Definition:**
```yaml
timeout_seconds: 900

artifacts:
  - name: ship_report
    pattern: "ship_report.md"
    required: true
    description: "Full deployment report with status fields"
  - name: release_notes
    pattern: "release_notes.md"
    required: false
    description: "Generated release notes in Keep a Changelog format"
```

**Ship Report Template:**
```markdown
# Ship Phase Report

DEPLOYMENT_STATUS: {{status}}
PR_MERGE_APPROVED: {{approved}}
VERSION_DEPLOYED: {{version}}
PR_NUMBER: {{pr_number}}

---

## Pre-Flight Summary

**Risk Level:** {{risk_level}}

### Risk Assessment
{{risk_justification}}

### Breaking Changes
{{breaking_changes_list}}

### PR State
- Mergeable: {{mergeable}}
- Review Status: {{review_decision}}
- Checks: {{check_status}}

---

## Execution Log

### Commands Executed
{{#commands_configured}}
1. **{{command_name}}**: {{result}}
   - Exit Code: {{exit_code}}
   - Duration: {{duration}}
{{/commands_configured}}
{{^commands_configured}}
_No deployment commands configured_
{{/commands_configured}}

### Post-Publish Hooks
{{post_publish_results}}

---

## Release Notes

{{release_notes_content}}

---

{{#deployment_failed}}
## Failure Analysis

### Failed Step
{{failed_step}}

### Error Output
```
{{error_output}}
```

### Diagnosis
{{diagnosis}}

### Remediation
{{remediation_steps}}

---
{{/deployment_failed}}

## Verification Recommendations

{{verification_recommendations}}

---

_Report generated by ADW Ship Phase_
_Run ID: {{run_id}}_
_Timestamp: {{timestamp}}_
```

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/ship/test_report_generation.py
class TestShipReport:
    def test_structured_fields_format(self):
        """Status fields match expected format for parsing."""

    def test_includes_preflight_summary(self):
        """Report includes pre-flight risk assessment."""

    def test_includes_execution_log(self):
        """Report includes command execution results."""

    def test_includes_release_notes(self):
        """Report includes or references release notes."""

    def test_includes_failure_analysis_when_failed(self):
        """Failure analysis included when DEPLOYMENT_STATUS: FAILED."""

    def test_excludes_failure_analysis_when_success(self):
        """Failure analysis omitted when successful."""

    def test_includes_verification(self):
        """Report includes verification recommendations."""

    def test_artifact_created(self):
        """ship_report.md artifact is created."""

    def test_required_artifact_validation(self):
        """Phase fails if ship_report not generated."""
```

---

## Previous Story Intelligence

**From Story 15.1:**
- Artifact definitions in config.yaml
- ship_report required, release_notes optional

**From Story 15.2:**
- Pre-flight risk assessment
- PR state information

**From Story 15.3:**
- Command execution results
- Post-publish hook results

**From Story 15.4:**
- Release notes content
- Version header information

**From Story 15.5:**
- Failure diagnosis
- Remediation steps

**From Story 15.6:**
- Final status determination
- PR merge decision

---

## Git Intelligence

**Report as Artifact:**
- Stored with run artifacts
- Available for debugging
- Historical record of deployments

---

## Latest Technical Information

**Markdown Best Practices:**
- Use headers for sections
- Code blocks for technical output
- Horizontal rules for separation
- Consistent formatting

**Status Field Parsing:**
```bash
# Simple parsing with grep/cut
STATUS=$(grep "^DEPLOYMENT_STATUS:" report.md | cut -d' ' -f2)
```

---

## Project Context Reference

See: `_bmad-output/architecture.md#State Persistence`

Key patterns and rules from project context:
- **Artifacts in phase folder**: `artifacts/ship/`
- **Required vs optional**: Phase fails without required artifacts
- **Markdown format**: Human and machine readable

---

## Dev Notes

### Implementation Approach

1. Collect data from all prior steps
2. Generate structured status fields
3. Build each report section
4. Conditionally include failure analysis
5. Add verification recommendations
6. Save as ship_report.md artifact

### Key Design Decisions

1. **Structured fields at top**: Easy parsing by post.sh
2. **Comprehensive coverage**: All ship phase information
3. **Conditional sections**: Failure analysis only when failed
4. **Required artifact**: Phase must generate report
5. **Historical record**: Useful for debugging and audit

### Report Section Order

1. Status fields (for parsing)
2. Pre-flight summary
3. Execution log
4. Release notes
5. Failure analysis (if applicable)
6. Verification recommendations
7. Metadata (run ID, timestamp)

### Status Field Values

| Field | Values | Description |
|-------|--------|-------------|
| DEPLOYMENT_STATUS | SUCCESS, FAILED, BLOCKED | Overall ship result |
| PR_MERGE_APPROVED | true, false | Whether to merge PR |
| VERSION_DEPLOYED | x.y.z, N/A | Deployed version |
| PR_NUMBER | integer | GitHub PR number |

### References

- [Source: _bmad-output/epics/epic-15-ship-phase-deployment.md#Story 15.7]
- [Source: _bmad-output/architecture.md#State Persistence]
- [Source: Artifact configuration patterns]

---

## Dev Agent Record

### Context Reference

Epic 15: Ship Phase & Deployment - Story 15.7

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
