# Story: Config-Driven Artifact Capture

<!-- TEMPLATE SECTION: story_header -->
Status: ready-for-dev
Linear Issue: not-configured
Epic: Tech Debt - PhaseRunner Refactoring
Created: 2026-01-05

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a developer extending ADW,
I want artifact capture to be config-driven rather than hardcoded,
so that I can define custom artifact capture rules without modifying PhaseRunner core code.

## Acceptance Criteria

- [ ] Artifact capture configuration is defined in `command.yaml` files
- [ ] PhaseRunner reads artifact capture rules from command config
- [ ] Default artifacts (`{phase}_output.md`) are captured for all phases
- [ ] Phase-specific artifacts (pr_description, evidence_manifest, git_diff) are defined in respective command.yaml files
- [ ] Custom commands can define their own artifact capture rules
- [ ] Existing functionality is preserved (backward compatible)
- [ ] All existing tests pass
- [ ] New tests cover config-driven artifact capture

## Tasks / Subtasks

### Task 1: Design Artifact Configuration Schema
- [ ] Define artifact capture schema in command.yaml format
- [ ] Support artifact types: file, manifest, generated
- [ ] Support capture timing: post-llm, post-hook

### Task 2: Implement Configuration Parsing
- [ ] Add `artifacts` field to CommandConfig model
- [ ] Parse artifact capture rules from command.yaml
- [ ] Provide defaults for commands without explicit artifact config

### Task 3: Refactor PhaseRunner._capture_artifacts()
- [ ] Remove hardcoded `if phase == "..."` checks
- [ ] Implement config-driven artifact capture loop
- [ ] Preserve existing helper methods (_capture_evidence_manifest, _capture_git_diff_artifacts)

### Task 4: Update Command YAML Files
- [ ] Add artifact configuration to `commands/document/command.yaml`
- [ ] Add artifact configuration to `commands/verify/command.yaml`
- [ ] Add artifact configuration to `commands/build/command.yaml`

### Task 5: Testing
- [ ] Unit tests for config parsing
- [ ] Integration tests for artifact capture
- [ ] Regression tests for existing behavior

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->
**Source:** `docs/development/tech-debt/orchestrator-phase-runner.md`

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->
- Python 3.13+
- Pydantic 2.12+ for config validation
- Maintain backward compatibility with existing commands
- Follow Open/Closed Principle - new artifacts without code changes

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->
**Location:** `src/adw/core/phase_runner.py:652-719`

**Current Implementation:**
```python
def _capture_artifacts(self, phase, context, llm_result):
    # Generic artifacts for all phases
    artifacts.append(f"{phase}_output.md")

    # Hardcoded special cases - TO BE REMOVED
    if phase == "document":
        artifacts.append("pr_description.md")
    if phase == "verify":
        self._capture_evidence_manifest(context)
    if phase == "build":
        self._capture_git_diff_artifacts(context)
```

**Target Pattern:**
```python
def _capture_artifacts(self, phase, context, llm_result, command: CommandConfig):
    # Generic artifacts for all phases
    artifacts.append(f"{phase}_output.md")

    # Config-driven artifact capture
    for artifact_config in command.artifacts:
        self._capture_artifact(artifact_config, context)
```

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->
- **Pydantic**: Use for artifact config model validation
- **PyYAML**: Already used for command.yaml parsing
- **No new dependencies required**

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->
**Files to Modify:**
- `src/adw/core/phase_runner.py` - Refactor `_capture_artifacts()` method
- `src/adw/models/command.py` - Add `ArtifactConfig` model (or extend existing)
- `src/adw/commands/resolution.py` - Parse artifact config from YAML

**Files to Create/Update:**
- `commands/document/command.yaml` - Add `artifacts:` section
- `commands/verify/command.yaml` - Add `artifacts:` section
- `commands/build/command.yaml` - Add `artifacts:` section

**Test Files:**
- `tests/unit/core/test_phase_runner.py` - Add artifact capture tests
- `tests/unit/models/test_command.py` - Add artifact config tests

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->
- Unit tests for `ArtifactConfig` model validation
- Unit tests for artifact config parsing from YAML
- Integration tests for config-driven artifact capture
- Regression tests ensuring existing artifact behavior unchanged
- Coverage requirement: >80%

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->
N/A - This is a standalone refactoring story.

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->
Recent commits show:
- `b7141c0` - Refactoring patterns: constructor injection over setters
- `59c6f05` - Feature implementation patterns in validation system
- `5b48dd1` - Bug fix patterns with issue references

**Patterns to follow:**
- Use constructor injection for dependencies
- Reference issue IDs in commit messages
- Include tests with implementation

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->
- Pydantic 2.12+ supports discriminated unions for polymorphic config
- YAML anchors can reduce duplication in command configs

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models MUST be in `src/adw/models/`
- Full type annotations required
- Use Pydantic for all structured data
- Follow exception hierarchy

---

## Dev Notes

- Effort: Medium
- This refactoring enables extensibility without modifying core code
- Consider plugin system for future if more complex artifact capture needed
- Hooks already receive `artifacts_dir` - could be alternative approach

### Project Structure Notes

- Models go in `src/adw/models/`
- Keep PhaseRunner focused on orchestration
- Command config parsing belongs in `commands/` module

### References

- [Source: docs/development/tech-debt/orchestrator-phase-runner.md]
- [Source: ISS-012-hardcoded-artifact-capture-per-phase.md]

---

## Dev Agent Record

<!-- TEMPLATE SECTION: story_completion_status -->

### Context Reference

Story created from ISS-012 tech debt documentation.

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

- Story created: 2026-01-05
- Ultimate context engine analysis completed - comprehensive developer guide created

### File List

Files to touch:
- `src/adw/core/phase_runner.py`
- `src/adw/models/command.py`
- `commands/document/command.yaml`
- `commands/verify/command.yaml`
- `commands/build/command.yaml`
- `tests/unit/core/test_phase_runner.py`
