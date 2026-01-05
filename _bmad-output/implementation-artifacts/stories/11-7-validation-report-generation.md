# Story 11.7: Validation Report Generation

Status: draft
Linear Issue: not-configured
Epic: 11 - Validation Loop
Created: 2026-01-05

---

## Story

As a developer,
I want a validation report summarizing the loop results,
so that I understand what was checked and decided.

## Acceptance Criteria

**Given** validation loop completes
**When** report is generated
**Then** it includes: iterations_run, issues_found, issues_fixed, issues_dismissed, issues_deferred

**Given** the report
**When** stored
**Then** it's at `.adw/runs/<id>/artifacts/validation/report.md`

**Given** deferred issues
**When** report is generated
**Then** they're formatted for inclusion in PR description

**Given** validation confidence
**When** calculated
**Then** it's: HIGH (all resolved), MEDIUM (some deferred), LOW (many deferred or dismissed)

## Tasks / Subtasks

### Task 1: Create ValidationReportGenerator
- [ ] Create `src/adw/validation/report.py` with `ValidationReportGenerator` class
- [ ] Inject state manager for data access
- [ ] Define `generate() -> ValidationReport` method
- [ ] Return structured report model

### Task 2: Create ValidationReport Model
- [ ] Create `ValidationReport` Pydantic model with:
  - `run_id: str`
  - `generated_at: datetime`
  - `iterations_run: int`
  - `issues_found: int`
  - `issues_fixed: int`
  - `issues_dismissed: int`
  - `issues_deferred: int`
  - `confidence: ConfidenceLevel`
  - `duration_seconds: float`
- [ ] Add `deferred_issues: list[DeferredIssueSummary]`

### Task 3: Implement Confidence Calculation
- [ ] Create `ConfidenceLevel` enum: HIGH, MEDIUM, LOW
- [ ] Calculate based on issue resolution ratios:
  - HIGH: all resolved, no deferred
  - MEDIUM: some deferred (< 30%)
  - LOW: many deferred (>= 30%) or many dismissed
- [ ] Include confidence explanation in report

### Task 4: Generate Markdown Report
- [ ] Create `to_markdown() -> str` method
- [ ] Include summary section with metrics
- [ ] Include resolved issues section (brief)
- [ ] Include deferred issues section (detailed)
- [ ] Include dismissed issues section (with reasons)

### Task 5: Generate PR Description Section
- [ ] Create `to_pr_section() -> str` method
- [ ] Format deferred issues as "Known Issues" section
- [ ] Include confidence level as badge
- [ ] Keep format concise for PR descriptions

### Task 6: Store Report Artifact
- [ ] Store at `.adw/runs/<id>/artifacts/validation/report.md`
- [ ] Create JSON version at `report.json` for programmatic access
- [ ] Include timestamp in report header

### Task 7: Add Report to Phase Output
- [ ] ValidationPhase returns report in PhaseResult
- [ ] Include report path in phase artifacts
- [ ] Pass deferred issues to Document phase for PR

### Task 8: Write Tests
- [ ] Unit tests for ValidationReportGenerator (5 tests)
- [ ] Unit tests for confidence calculation (4 tests)
- [ ] Unit tests for markdown generation (4 tests)
- [ ] Unit tests for PR section generation (3 tests)
- [ ] Integration test for full report cycle (2 tests)

---

## Dependencies

- **Depends On:** Story 11.5
- **Blocks:** None
- **Can Parallel With:** None

### Dependency Rationale
- Story 11.5: Report generation needs to know final exit state, limits reached, and loop summary

---

## Developer Context

### Technical Requirements

1. **Report Content**
   - Summary metrics at a glance
   - Detailed sections for each issue category
   - Confidence level with explanation
   - Timestamps for tracking

2. **Markdown Formatting**
   - GitHub-flavored markdown
   - Collapsible sections for large lists
   - Code blocks for file locations
   - Tables for metrics

3. **PR Integration**
   - Concise format suitable for PR descriptions
   - "Known Issues" section for deferred items
   - Confidence badge/indicator

### Architecture Compliance

**File Location:** `src/adw/validation/report.py`

**Storage Structure:**
```
.adw/runs/<run_id>/artifacts/validation/
├── report.md        # Human-readable report
└── report.json      # Machine-readable report
```

**Class Structure:**
```python
# src/adw/validation/report.py
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"      # All resolved, none deferred
    MEDIUM = "MEDIUM"  # Some deferred (<30%)
    LOW = "LOW"        # Many deferred (>=30%) or many dismissed

class DeferredIssueSummary(BaseModel):
    issue_id: str
    source: str
    severity: str
    description: str
    reason: str
    file_path: str | None = None

class ValidationReport(BaseModel):
    run_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float

    # Iteration metrics
    iterations_run: int
    max_iterations: int
    exit_reason: str

    # Issue metrics
    issues_found: int
    issues_fixed: int
    issues_dismissed: int
    issues_deferred: int

    # Confidence
    confidence: ConfidenceLevel
    confidence_explanation: str

    # Detailed lists
    deferred_issues: list[DeferredIssueSummary] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# Validation Report",
            f"",
            f"**Run ID:** {self.run_id}",
            f"**Generated:** {self.generated_at.isoformat()}",
            f"**Duration:** {self.duration_seconds:.1f}s",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Iterations | {self.iterations_run}/{self.max_iterations} |",
            f"| Issues Found | {self.issues_found} |",
            f"| Issues Fixed | {self.issues_fixed} |",
            f"| Issues Dismissed | {self.issues_dismissed} |",
            f"| Issues Deferred | {self.issues_deferred} |",
            f"| Exit Reason | {self.exit_reason} |",
            f"",
            f"## Confidence: {self.confidence.value}",
            f"",
            f"{self.confidence_explanation}",
            f"",
        ]

        if self.deferred_issues:
            lines.extend([
                f"## Deferred Issues",
                f"",
                f"The following issues were deferred for later resolution:",
                f"",
            ])
            for issue in self.deferred_issues:
                lines.extend([
                    f"### {issue.issue_id}",
                    f"",
                    f"- **Source:** {issue.source}",
                    f"- **Severity:** {issue.severity}",
                    f"- **Description:** {issue.description}",
                    f"- **Reason:** {issue.reason}",
                ])
                if issue.file_path:
                    lines.append(f"- **Location:** `{issue.file_path}`")
                lines.append("")

        return "\n".join(lines)

    def to_pr_section(self) -> str:
        """Generate PR description section for known issues."""
        if not self.deferred_issues:
            return ""

        badge = {
            ConfidenceLevel.HIGH: "![HIGH](https://img.shields.io/badge/confidence-HIGH-green)",
            ConfidenceLevel.MEDIUM: "![MEDIUM](https://img.shields.io/badge/confidence-MEDIUM-yellow)",
            ConfidenceLevel.LOW: "![LOW](https://img.shields.io/badge/confidence-LOW-red)",
        }[self.confidence]

        lines = [
            f"## Known Issues {badge}",
            f"",
            f"The following issues were identified but deferred:",
            f"",
        ]
        for issue in self.deferred_issues:
            lines.append(f"- **{issue.source}:** {issue.description}")
            if issue.file_path:
                lines.append(f"  - Location: `{issue.file_path}`")

        return "\n".join(lines)


class ValidationReportGenerator:
    def __init__(
        self,
        state_manager: ValidationStateManager,
        config: ValidationConfig,
    ):
        self.state_manager = state_manager
        self.config = config

    def generate(
        self,
        loop_summary: dict,
        issues: list[ValidationIssue],
        start_time: datetime,
    ) -> ValidationReport:
        """Generate validation report from loop results."""
        duration = (datetime.utcnow() - start_time).total_seconds()

        # Collect deferred issues
        deferred = [
            DeferredIssueSummary(
                issue_id=i.id,
                source=i.source.value,
                severity=i.severity.value,
                description=i.description,
                reason=i.triage_reason or "Unknown",
                file_path=i.location.file_path if i.location else None,
            )
            for i in issues
            if i.triage_decision == "DEFER"
        ]

        # Calculate confidence
        confidence, explanation = self._calculate_confidence(
            issues_found=len(issues),
            issues_fixed=loop_summary["resolved"],
            issues_dismissed=loop_summary["dismissed"],
            issues_deferred=loop_summary["deferred"],
        )

        return ValidationReport(
            run_id=self.state_manager.run_id,
            duration_seconds=duration,
            iterations_run=loop_summary["iterations_run"],
            max_iterations=self.config.max_iterations,
            exit_reason=loop_summary.get("exit_reason", "COMPLETED"),
            issues_found=len(issues),
            issues_fixed=loop_summary["resolved"],
            issues_dismissed=loop_summary["dismissed"],
            issues_deferred=loop_summary["deferred"],
            confidence=confidence,
            confidence_explanation=explanation,
            deferred_issues=deferred,
        )

    def _calculate_confidence(
        self,
        issues_found: int,
        issues_fixed: int,
        issues_dismissed: int,
        issues_deferred: int,
    ) -> tuple[ConfidenceLevel, str]:
        """Calculate confidence level based on issue resolution."""
        if issues_found == 0:
            return ConfidenceLevel.HIGH, "No issues found during validation."

        deferred_ratio = issues_deferred / issues_found if issues_found > 0 else 0
        dismissed_ratio = issues_dismissed / issues_found if issues_found > 0 else 0

        if issues_deferred == 0 and dismissed_ratio < 0.5:
            return ConfidenceLevel.HIGH, f"All {issues_found} issues resolved or appropriately handled."

        if deferred_ratio < 0.3:
            return ConfidenceLevel.MEDIUM, f"{issues_deferred} issues deferred ({deferred_ratio:.0%}). Review recommended."

        return ConfidenceLevel.LOW, f"{issues_deferred} issues deferred ({deferred_ratio:.0%}). Manual review required."

    def save(self, report: ValidationReport) -> Path:
        """Save report to artifacts directory."""
        artifacts_dir = self.state_manager.validation_dir.parent / "artifacts" / "validation"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Save markdown
        md_path = artifacts_dir / "report.md"
        md_path.write_text(report.to_markdown())

        # Save JSON
        json_path = artifacts_dir / "report.json"
        json_path.write_text(report.model_dump_json(indent=2))

        return md_path
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| Pydantic | 2.12+ | Report model |
| pathlib | stdlib | File operations |
| datetime | stdlib | Timestamps |

### File Structure Requirements

**New Files:**
- `src/adw/validation/report.py`

**Modified Files:**
- `src/adw/validation/__init__.py` - Export ValidationReportGenerator
- `src/adw/validation/phase.py` - Generate report at end

**Test Files:**
- `tests/unit/validation/test_report.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/validation/test_report.py
class TestValidationReportGenerator:
    def test_generate_report(self, mock_state, sample_issues):
        """Report generated with correct metrics."""

    def test_generate_with_no_issues(self, mock_state):
        """Report handles zero issues gracefully."""

    def test_generate_includes_deferred(self, mock_state, deferred_issues):
        """Deferred issues included in report."""

    def test_save_creates_both_formats(self, tmp_path):
        """Both MD and JSON files created."""

    def test_save_in_artifacts_dir(self, tmp_path):
        """Files created in artifacts/validation/."""

class TestConfidenceCalculation:
    def test_high_all_resolved(self):
        """HIGH when all issues resolved."""

    def test_high_no_issues(self):
        """HIGH when no issues found."""

    def test_medium_some_deferred(self):
        """MEDIUM when < 30% deferred."""

    def test_low_many_deferred(self):
        """LOW when >= 30% deferred."""

class TestMarkdownGeneration:
    def test_includes_summary_table(self, sample_report):
        """Markdown includes summary metrics table."""

    def test_includes_deferred_section(self, report_with_deferred):
        """Markdown includes deferred issues section."""

    def test_no_deferred_section_when_empty(self, sample_report):
        """No deferred section when none deferred."""

    def test_github_flavored(self, sample_report):
        """Uses GitHub-flavored markdown."""

class TestPRSection:
    def test_includes_confidence_badge(self, sample_report):
        """PR section includes confidence badge."""

    def test_lists_deferred_issues(self, report_with_deferred):
        """PR section lists all deferred issues."""

    def test_empty_when_no_deferred(self, sample_report):
        """Returns empty string when no deferred."""
```

---

## Previous Story Intelligence

**Learnings from Story 11.5:**
- Loop summary includes iteration counts and exit reason
- Exit reasons: ALL_RESOLVED, MAX_ITERATIONS, STALL_DETECTED

**Learnings from Story 11.6:**
- State manager provides access to persisted data
- Issues and triage decisions available for report

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 9: PR description generation
- Markdown generation patterns

**Established Patterns:**
- Reports stored in artifacts directory
- Both human and machine-readable formats
- Include timestamps in reports

---

## Latest Technical Information

**Markdown Report Best Practices (2025):**
- Use GitHub-flavored markdown for compatibility
- Include collapsible sections for long content
- Use tables for metrics
- Include badges for visual status

**PR Integration:**
- Keep known issues section concise
- Use shields.io badges for confidence
- Link to full report if available

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Artifacts in runs/**: Reports go in artifacts subdirectory
- **Dual format**: Both MD and JSON for flexibility
- **Structured models**: Use Pydantic for reports
- **PR integration**: Format for GitHub PR descriptions

---

## Dev Notes

### Report Example

```markdown
# Validation Report

**Run ID:** 01H...
**Generated:** 2026-01-05T10:30:00Z
**Duration:** 45.2s

## Summary

| Metric | Value |
|--------|-------|
| Iterations | 3/5 |
| Issues Found | 8 |
| Issues Fixed | 5 |
| Issues Dismissed | 1 |
| Issues Deferred | 2 |
| Exit Reason | ALL_RESOLVED |

## Confidence: MEDIUM

2 issues deferred (25%). Review recommended.

## Deferred Issues

### VI-01H...

- **Source:** TEST
- **Severity:** WARNING
- **Description:** Flaky test in integration suite
- **Reason:** Intermittent failure, requires investigation
- **Location:** `tests/integration/test_api.py`
```

### Implementation Approach

1. Create ConfidenceLevel enum
2. Create DeferredIssueSummary model
3. Create ValidationReport model
4. Implement to_markdown() method
5. Implement to_pr_section() method
6. Implement ValidationReportGenerator
7. Add confidence calculation
8. Integrate with ValidationPhase
9. Write comprehensive tests

### References

- [Source: _bmad-output/epics/epic-11-validation-loop.md#Story 11.7]
- [Source: _bmad-output/architecture.md#Artifacts]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 11: Validation Loop - Story 11.7

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

### Completion Notes List

### File List
