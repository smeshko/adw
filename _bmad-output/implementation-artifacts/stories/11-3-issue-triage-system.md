# Story 11.3: Issue Triage System

Status: draft
Linear Issue: not-configured
Epic: 11 - Validation Loop
Created: 2026-01-05

---

## Story

As a developer,
I want to triage validation issues into FIX, DISMISS, or DEFER,
so that I control which issues block the pipeline.

## Acceptance Criteria

**Given** issues are found
**When** triage runs
**Then** each issue is categorized: FIX, DISMISS, or DEFER

**Given** `triage_mode: auto` in config
**When** triage runs
**Then** LLM decides based on issue severity and context

**Given** `triage_mode: manual` in config
**When** triage runs
**Then** user is prompted for each issue (or batch)

**Given** a DISMISSED issue
**When** recorded
**Then** it's logged with reasoning and doesn't block pipeline

**Given** a DEFERRED issue
**When** recorded
**Then** it's added to PR description as "Known Issues"

**Given** a FIX issue
**When** recorded
**Then** it enters the fix queue for the next iteration

## Tasks / Subtasks

### Task 1: Create TriageDecision Enum
- [ ] Add to `src/adw/validation/models.py`:
  - `TriageDecision` enum: FIX, DISMISS, DEFER
- [ ] Add `triage_decision` and `triage_reason` fields to ValidationIssue (if not already present)
- [ ] Create `TriagedIssue` wrapper with decision metadata

### Task 2: Create TriageSystem Class
- [ ] Create `src/adw/validation/triage.py` with `TriageSystem` class
- [ ] Implement `triage(issues: list[ValidationIssue], mode: str) -> list[TriagedIssue]`
- [ ] Support modes: "auto", "manual", "hybrid"
- [ ] Inject LLM executor for auto mode
- [ ] Handle empty issues list gracefully

### Task 3: Implement Auto Triage
- [ ] Create `_auto_triage(issue: ValidationIssue) -> TriageDecision`
- [ ] Build prompt with issue details and severity context
- [ ] Parse LLM response for FIX/DISMISS/DEFER decision
- [ ] Extract reasoning from LLM response
- [ ] Apply `auto_dismiss_info` config (auto-dismiss INFO severity)

### Task 4: Implement Manual Triage
- [ ] Create `_manual_triage(issue: ValidationIssue) -> TriageDecision`
- [ ] Display issue details using Rich formatting
- [ ] Prompt user with options: [F]ix, [D]ismiss, de[F]er, [S]kip
- [ ] Support batch selection for multiple similar issues
- [ ] Capture user's reasoning for audit trail

### Task 5: Implement Hybrid Triage
- [ ] Create `_hybrid_triage(issues: list[ValidationIssue]) -> list[TriagedIssue]`
- [ ] Auto-triage INFO and WARNING severity
- [ ] Manual triage for ERROR severity
- [ ] Allow user to override auto decisions
- [ ] Provide summary before committing decisions

### Task 6: Add Triage Rules Engine
- [ ] Create `TriageRules` class for configurable rules
- [ ] Support rules like: "always dismiss linting warnings"
- [ ] Support patterns: "auto-fix test failures in {path}"
- [ ] Load rules from `.adw/triage-rules.yaml`
- [ ] Apply rules before LLM/manual triage

### Task 7: Implement Triage Logging
- [ ] Log each triage decision with reasoning
- [ ] Create triage audit trail in run artifacts
- [ ] Store triage statistics (counts by decision type)
- [ ] Support `--dry-run` mode to preview decisions

### Task 8: Write Tests
- [ ] Unit tests for TriageSystem (6 tests)
- [ ] Unit tests for auto triage (5 tests)
- [ ] Unit tests for manual triage - mocked input (4 tests)
- [ ] Unit tests for hybrid triage (4 tests)
- [ ] Unit tests for triage rules (4 tests)
- [ ] Integration test for full triage flow (2 tests)

---

## Dependencies

- **Depends On:** Story 11.2
- **Blocks:** Story 11.5
- **Can Parallel With:** Story 11.4, Story 11.6

### Dependency Rationale
- Story 11.2: Triage system operates on ValidationIssue objects with severity and source
- Story 11.5: Exit conditions need triage decisions (FIX/DISMISS/DEFER) to determine completion

---

## Developer Context

### Technical Requirements

1. **Triage Mode Selection**
   - Auto: LLM makes all decisions based on severity/context
   - Manual: User prompted for each issue interactively
   - Hybrid: Auto for low severity, manual for errors

2. **LLM Integration**
   - Use existing LLM executor from Epic 3
   - Structured prompt for consistent decisions
   - Fallback to manual if LLM fails

3. **User Interaction**
   - Rich prompts with syntax highlighting for code issues
   - Support batch operations for efficiency
   - Clear keyboard shortcuts for decisions

### Architecture Compliance

**File Location:** `src/adw/validation/triage.py`

**Class Structure:**
```python
# src/adw/validation/triage.py
from enum import Enum
from dataclasses import dataclass
from typing import Protocol

class TriageDecision(str, Enum):
    FIX = "FIX"
    DISMISS = "DISMISS"
    DEFER = "DEFER"

@dataclass
class TriageResult:
    issue: ValidationIssue
    decision: TriageDecision
    reason: str
    auto_decided: bool = False

class TriageSystem:
    def __init__(
        self,
        llm_executor: LLMExecutor,
        config: ValidationConfig,
        console: Console | None = None,
    ):
        self.llm = llm_executor
        self.config = config
        self.console = console or Console()
        self.rules = TriageRules.load_from_config(config)

    async def triage(
        self,
        issues: list[ValidationIssue],
        mode: str | None = None,
    ) -> list[TriageResult]:
        """Triage all issues according to mode."""
        mode = mode or self.config.triage_mode
        if mode == "auto":
            return await self._auto_triage_all(issues)
        elif mode == "manual":
            return self._manual_triage_all(issues)
        else:  # hybrid
            return await self._hybrid_triage_all(issues)

    async def _auto_triage_all(
        self,
        issues: list[ValidationIssue],
    ) -> list[TriageResult]:
        """Use LLM to triage all issues."""
        results = []
        for issue in issues:
            # Check rules first
            rule_decision = self.rules.evaluate(issue)
            if rule_decision:
                results.append(TriageResult(
                    issue=issue,
                    decision=rule_decision.decision,
                    reason=rule_decision.reason,
                    auto_decided=True,
                ))
                continue

            # Auto-dismiss INFO if configured
            if self.config.auto_dismiss_info and issue.severity == IssueSeverity.INFO:
                results.append(TriageResult(
                    issue=issue,
                    decision=TriageDecision.DISMISS,
                    reason="Auto-dismissed INFO severity",
                    auto_decided=True,
                ))
                continue

            # LLM triage
            decision = await self._llm_triage(issue)
            results.append(decision)

        return results
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| Rich | 13.9+ | Interactive prompts and formatting |
| asyncio | stdlib | Async LLM calls |
| Pydantic | 2.12+ | Model validation |
| PyYAML | 6.0+ | Rules file loading |

### File Structure Requirements

**New Files:**
- `src/adw/validation/triage.py`
- `src/adw/validation/rules.py`

**Modified Files:**
- `src/adw/validation/__init__.py` - Export TriageSystem
- `src/adw/validation/models.py` - Add TriageDecision if not present

**Test Files:**
- `tests/unit/validation/test_triage.py`
- `tests/unit/validation/test_rules.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/validation/test_triage.py
class TestTriageSystem:
    async def test_auto_triage_uses_llm(self, mock_llm):
        """Auto mode calls LLM for each issue."""

    async def test_auto_triage_auto_dismiss_info(self, mock_config):
        """INFO severity auto-dismissed when configured."""

    async def test_auto_triage_respects_rules(self, mock_rules):
        """Rules are applied before LLM triage."""

    def test_manual_triage_prompts_user(self, mock_console):
        """Manual mode prompts for each issue."""

    async def test_hybrid_auto_for_warnings(self, mock_llm):
        """Hybrid mode auto-triages non-errors."""

    async def test_hybrid_manual_for_errors(self, mock_console):
        """Hybrid mode prompts for errors."""

class TestTriageRules:
    def test_load_from_yaml(self, tmp_path):
        """Rules loaded from YAML file."""

    def test_pattern_matching(self):
        """Rules match issues by pattern."""

    def test_severity_filter(self):
        """Rules can filter by severity."""

    def test_no_match_returns_none(self):
        """No matching rule returns None."""
```

---

## Previous Story Intelligence

**Learnings from Story 11.1:**
- Validators produce issues with source and severity
- All issues collected before triage begins

**Learnings from Story 11.2:**
- ValidationIssue has triage_decision and triage_reason fields
- Issues have severity: ERROR, WARNING, INFO
- Issues have unique IDs for tracking

---

## Git Intelligence

**Recent Relevant Commits:**
- Epic 3: LLM executor integration patterns
- Epic 7: Console output and Rich formatting

**Established Patterns:**
- LLM calls use async with timeout handling
- Console prompts use Rich Prompt class
- Configuration loaded from YAML

---

## Latest Technical Information

**LLM Triage Prompts (2025):**
- Provide severity context in prompt
- Include code snippet if available
- Ask for structured response (JSON)
- Request reasoning with decision

**Interactive CLI Best Practices:**
- Use Rich's Confirm and Prompt classes
- Support keyboard shortcuts for speed
- Show progress for batch operations

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Async by default**: Triage operations should be async
- **Configuration-driven**: All behavior configurable
- **Structured logging**: Log triage decisions for audit
- **Rich console**: Use Rich for all user interaction

---

## Dev Notes

### Auto Triage Prompt Template

```
You are triaging a validation issue. Based on the severity and context,
decide whether to FIX, DISMISS, or DEFER this issue.

Issue:
- Source: {source}
- Severity: {severity}
- Description: {description}
- Location: {location}
- Context: {context}

Guidelines:
- FIX: Issues that block functionality or indicate bugs
- DISMISS: Issues that are false positives or not relevant
- DEFER: Issues that are valid but can be addressed later

Respond with JSON:
{
  "decision": "FIX|DISMISS|DEFER",
  "reason": "Brief explanation"
}
```

### Implementation Approach

1. Create TriageDecision enum and TriageResult model
2. Implement TriageSystem skeleton
3. Add auto triage with LLM integration
4. Add manual triage with Rich prompts
5. Add hybrid mode combining both
6. Add rules engine for customization
7. Write comprehensive tests

### References

- [Source: _bmad-output/epics/epic-11-validation-loop.md#Story 11.3]
- [Source: _bmad-output/architecture.md#LLM Integration]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 11: Validation Loop - Story 11.3

### Agent Model Used

<!-- To be filled during implementation -->

### Debug Log References

### Completion Notes List

### File List
