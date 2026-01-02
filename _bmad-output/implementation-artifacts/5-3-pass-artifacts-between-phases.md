# Story 5.3: Pass Artifacts Between Phases

Status: code-review
Linear Issue: not-configured
Epic: 5 - Pipeline Orchestration
Created: 2026-01-02

---

## Story

As a developer,
I want artifacts from earlier phases available to later phases,
so that the pipeline builds on previous outputs.

## Acceptance Criteria

**Given** the Plan phase produces `plan.md` artifact
**When** the Build phase template references `{{artifacts.plan.plan}}`
**Then** the content of plan.md is included

**Given** the Build phase produces `diff.txt` artifact
**When** the Verify phase executes
**Then** the diff is available for evidence gathering

**Given** multiple artifacts from a phase
**When** template references `{{artifacts.build.*}}`
**Then** all artifacts are available by name

**Given** an artifact referenced that doesn't exist
**When** strict mode is enabled
**Then** ConfigError is raised with clear message

## Tasks / Subtasks

### Task 1: Extend Template Variables for Artifacts
- [x] Update `PhaseRunner._load_and_render_prompt()` to include artifacts
- [x] Build artifacts variable map: `{"phase": {"artifact_name": "content"}}`
- [x] Load artifact content from `artifact_manager.get()`
- [x] Handle missing artifacts gracefully (empty string or error based on mode)

### Task 2: Implement Artifact Content Loading
- [x] Add `_load_phase_artifacts(run_id, phase)` method to PhaseRunner
- [x] Load all artifact files for a given phase
- [x] Return dict: `{artifact_name: content}`
- [x] Strip file extensions from artifact names for template access

### Task 3: Implement Full Artifacts Map
- [x] Add `_build_artifacts_map(run_id)` method
- [x] Iterate all previous phases in PHASE_SEQUENCE
- [x] Load artifacts for each phase
- [x] Build nested structure: `{phase: {artifact: content}}`

### Task 4: Update Template Engine for Artifacts
- [x] Ensure template engine handles nested dict access: `{{artifacts.plan.plan}}`
- [x] Support wildcard pattern `{{artifacts.build.*}}` (list all)
- [x] Test template variable resolution

### Task 5: Implement Strict Mode for Missing Artifacts
- [x] Add `strict_artifacts` config option (default: False)
- [x] When True and artifact referenced but missing: raise ConfigError
- [x] When False: use empty string for missing artifacts
- [x] Log warning for missing artifacts regardless of mode

### Task 6: Add Named Artifact Support
- [x] Extend artifact storage to support named artifacts
- [x] Convention: `plan.md` accessible as `artifacts.plan.plan`
- [x] Convention: `build_output.md` accessible as `artifacts.build.build_output`
- [x] Document naming conventions

### Task 7: Implement Artifact Discovery in Template
- [x] Add `{{artifacts.plan}}` to list all plan artifacts
- [x] Add `{{artifacts.*}}` to list all artifacts across phases
- [x] Return formatted list or JSON for templates

### Task 8: Write Unit Tests
- [x] Create `tests/unit/core/test_artifact_passing.py`
- [x] Test artifact from previous phase accessible
- [x] Test artifact content correctly included in template
- [x] Test missing artifact behavior (strict vs lenient)
- [x] Test multiple artifacts from single phase
- [x] Test artifact naming conventions
- [x] Target: >90% coverage

### Task 9: Write Integration Tests
- [x] Test plan artifact flows to build phase
- [x] Test build artifact flows to verify phase
- [x] Test full pipeline artifact continuity
- [x] Test artifact content integrity

---

## Developer Context

### Technical Requirements

- **Artifact Access Pattern**: `{{artifacts.<phase>.<name>}}`
- **Content Loading**: Load full artifact content into template variables
- **Missing Handling**: Configurable strict mode
- **Naming Convention**: `<name>.md` → `artifacts.<phase>.<name>`

### Architecture Compliance

**From architecture.md - FR11:**
```
FR11: System makes previous phase artifacts available to subsequent phases
```

**From architecture.md - Template Engine:**
```python
# Variable patterns
VARIABLE_PATTERN = r'\{\{([a-z_][a-z0-9_.]*)\}\}'

# Nested access: artifacts.plan.plan resolves to artifacts["plan"]["plan"]
```

**From architecture.md - Artifact Storage:**
```
.adw/runs/<run_id>/
└── artifacts/
    ├── plan/
    │   └── plan.md
    ├── build/
    │   ├── diff.txt
    │   └── build_output.md
    └── verify/
        └── evidence.json
```

### Library & Framework Requirements

**Building Artifacts Map:**
```python
def _build_artifacts_map(self, run_id: str) -> dict[str, dict[str, str]]:
    """Build nested dict of all artifacts for template access.

    Returns:
        {
            "plan": {"plan": "plan content..."},
            "build": {"diff": "diff content...", "build_output": "output..."},
        }
    """
    artifacts_map: dict[str, dict[str, str]] = {}

    for phase in PHASE_SEQUENCE:
        phase_artifacts = self.artifact_manager.list_artifacts(run_id, phase)
        if not phase_artifacts:
            continue

        phase_map: dict[str, str] = {}
        for artifact in phase_artifacts:
            # Strip extension: plan.md -> plan
            name = Path(artifact["name"]).stem
            content = self.artifact_manager.get(run_id, phase, artifact["name"])
            if content:
                phase_map[name] = content

        if phase_map:
            artifacts_map[phase] = phase_map

    return artifacts_map
```

**Template Variable Resolution:**
```python
# In template_engine.py
def _resolve_variable(self, path: str, context: dict) -> str:
    """Resolve dotted path like 'artifacts.plan.plan'.

    Args:
        path: Dotted path string
        context: Variables dict

    Returns:
        Resolved value as string
    """
    parts = path.split(".")
    value = context

    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return ""  # Or raise if strict mode

    return str(value) if value is not None else ""
```

**Strict Mode Error:**
```python
if strict_artifacts and content is None:
    raise ConfigError(
        code="ARTIFACT_NOT_FOUND",
        message=f"Artifact '{phase}/{name}' not found",
        suggestion=f"Ensure {phase} phase completed and produced {name}",
        recoverable=False,
    )
```

### File Structure Requirements

**Files to modify:**
```
src/adw/
├── core/
│   └── phase_runner.py       # MODIFY - add artifact loading
├── commands/
│   └── template.py           # MODIFY - ensure nested dict resolution
tests/
├── unit/
│   └── core/
│       └── test_artifact_passing.py  # NEW
└── integration/
    └── core/
        └── test_artifact_flow_integration.py  # NEW
```

**Updated PhaseRunner._load_and_render_prompt:**
```python
def _load_and_render_prompt(
    self,
    phase: str,
    context: RunContext,
    pre_hook_output: str,
) -> str:
    """Load prompt template and render with variables.

    Includes artifact content from previous phases for template access.
    """
    logger.debug("Loading prompt", phase=phase)

    # Resolve command config
    command = self.command_resolver.resolve(phase)

    # Build artifacts map from previous phases
    artifacts_map = self._build_artifacts_map(context.run_id, phase)

    # Build template variables
    variables = {
        "context": context.model_dump(),
        "pre_hook_output": pre_hook_output,
        "artifacts": artifacts_map,  # Nested: {phase: {name: content}}
        "run_id": context.run_id,
        "phase": phase,
        "feature": context.feature_description,
    }

    # Render template
    rendered = self.template_engine.render(command.prompt_template, variables)

    logger.debug("Prompt rendered", phase=phase, prompt_len=len(rendered))
    return rendered


def _build_artifacts_map(
    self,
    run_id: str,
    current_phase: str,
) -> dict[str, dict[str, str]]:
    """Build map of artifacts from previous phases.

    Only includes phases that completed before current_phase.

    Args:
        run_id: Current run ID
        current_phase: Phase about to execute

    Returns:
        Nested dict: {phase: {artifact_name: content}}
    """
    artifacts_map: dict[str, dict[str, str]] = {}

    # Only load artifacts from phases before current
    current_idx = PHASE_SEQUENCE.index(current_phase)
    previous_phases = PHASE_SEQUENCE[:current_idx]

    for phase in previous_phases:
        phase_artifacts = self.artifact_manager.list_artifacts(run_id, phase)
        if not phase_artifacts:
            continue

        phase_map: dict[str, str] = {}
        for artifact in phase_artifacts:
            name = Path(artifact["name"]).stem  # plan.md -> plan
            content = self.artifact_manager.get(run_id, phase, artifact["name"])
            if content:
                phase_map[name] = content

        if phase_map:
            artifacts_map[phase] = phase_map

    return artifacts_map
```

### Testing Requirements

**Test Framework:** pytest

**Test artifact from previous phase:**
```python
def test_plan_artifact_available_in_build(phase_runner, artifact_manager, sample_context):
    """Test that plan.md artifact is accessible in build phase template."""
    # Store plan artifact
    artifact_manager.store(sample_context.run_id, "plan", "plan.md", "# Implementation Plan\n...")

    # Build artifacts map for build phase
    artifacts = phase_runner._build_artifacts_map(sample_context.run_id, "build")

    assert "plan" in artifacts
    assert "plan" in artifacts["plan"]
    assert "# Implementation Plan" in artifacts["plan"]["plan"]
```

**Test template resolution:**
```python
def test_template_resolves_artifact_reference(template_engine):
    """Test that {{artifacts.plan.plan}} resolves to artifact content."""
    template = "Use this plan:\n{{artifacts.plan.plan}}"
    variables = {
        "artifacts": {
            "plan": {"plan": "Step 1: Do X\nStep 2: Do Y"}
        }
    }

    result = template_engine.render(template, variables)

    assert "Step 1: Do X" in result
    assert "Step 2: Do Y" in result
```

**Test strict mode:**
```python
def test_strict_mode_raises_for_missing_artifact(phase_runner):
    """Test that strict mode raises ConfigError for missing artifact."""
    from adw.exceptions import ConfigError

    phase_runner.strict_artifacts = True

    with pytest.raises(ConfigError) as exc_info:
        phase_runner._get_artifact_content(run_id, "plan", "missing.md")

    assert exc_info.value.code == "ARTIFACT_NOT_FOUND"
```

**Test lenient mode:**
```python
def test_lenient_mode_returns_empty_for_missing(phase_runner):
    """Test that lenient mode returns empty string for missing artifact."""
    phase_runner.strict_artifacts = False

    result = phase_runner._get_artifact_content(run_id, "plan", "missing.md")

    assert result == ""
```

**Coverage Target:** >80% overall, >90% for artifact passing logic

---

## Previous Story Intelligence

**From Story 4.4 (Artifact Manager):**
- `ArtifactManager` provides `store()`, `get()`, `list_artifacts()`
- Artifacts stored at: `artifacts/<phase>/<name>`
- `get()` returns None if artifact doesn't exist

**From Story 5.2 (PhaseRunner):**
- PhaseRunner calls `_load_and_render_prompt()` for each phase
- Template variables include `artifacts` dict
- Need to extend with full artifact content

**From Story 2.2 (Template Engine):**
- Template engine handles `{{variable.path}}` syntax
- Need to verify nested dict resolution works

**Key patterns:**
- Artifact content loaded lazily
- Phase order determines available artifacts
- Naming convention: file extension stripped for access

---

## Git Intelligence

**From Epic 4:**
- ArtifactManager fully implemented
- `list_artifacts()` returns metadata with `name`, `phase`
- `get()` returns content or None

**Existing behavior:**
- Story 5.2 passes artifact paths, not content
- Need to extend to load and include content

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **Artifact Naming**: `plan.md` → `artifacts.plan.plan`
2. **Phase Order**: Only previous phases' artifacts available
3. **Strict Mode**: Configurable error vs silent on missing
4. **Template Syntax**: `{{artifacts.phase.name}}` for content

---

## Dev Notes

### Key Implementation Points

1. **Artifact Map Structure**:
   ```python
   {
       "plan": {"plan": "# Plan content..."},
       "build": {
           "diff": "git diff output...",
           "build_output": "# Build output..."
       }
   }
   ```

2. **Access in Templates**:
   ```
   {{artifacts.plan.plan}}         # Content of plan/plan.md
   {{artifacts.build.diff}}        # Content of build/diff.txt
   ```

3. **Only Previous Phases**:
   ```python
   current_idx = PHASE_SEQUENCE.index(current_phase)
   previous_phases = PHASE_SEQUENCE[:current_idx]
   ```

4. **Strict Mode Config**:
   ```yaml
   # In config.yaml
   pipeline:
     strict_artifacts: true  # Fail on missing artifact references
   ```

### Project Structure Notes

- Extends PhaseRunner from Story 5.2
- Uses ArtifactManager from Story 4.4
- Template engine may need updates for nested resolution

### References

- [Source: _bmad-output/architecture.md#FR11]
- [Source: _bmad-output/architecture.md#Template-Engine]
- [Source: src/adw/core/artifact_manager.py] - ArtifactManager
- [Source: src/adw/commands/template.py] - TemplateEngine

---

## Dev Agent Record

### Context Reference

Story 5.3 implements artifact passing between phases, enabling later phases to access outputs from earlier phases via template variables.

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Task 1: Extended `_load_and_render_prompt()` to include artifact content from previous phases. Added `_build_artifacts_map()` method that loads artifacts by phase, strips file extensions for clean template access (`plan.md` → `artifacts.plan.plan`).
- Task 2: Extracted `_load_phase_artifacts()` helper method for loading all artifacts from a single phase with extension stripping. Refactored `_build_artifacts_map()` to use this helper.
- Task 3: Verified `_build_artifacts_map()` correctly iterates PHASE_SEQUENCE and builds nested `{phase: {artifact: content}}` structure. Already implemented in Task 1.
- Task 4: Added wildcard pattern support (`{{artifacts.build.*}}`) to template engine via `_resolve_wildcard()` method. Lists all artifacts in a phase with content previews.
- Task 5: Verified strict mode already works via template engine's `strict` parameter. Added comprehensive tests for strict/lenient behavior with missing artifacts.
- Task 6: Verified naming conventions already implemented (extension stripping). Added tests confirming `plan.md` → `artifacts.plan.plan` and similar patterns.
- Task 7: Verified wildcard patterns from Task 4 already support discovery: `{{artifacts.plan.*}}` lists plan artifacts, `{{artifacts.*}}` lists all phases.
- Task 8: All unit tests written throughout tasks 1-7. 28 tests covering all requirements. Project coverage: 93.25%.
- Task 9: Created 11 integration tests in `test_artifact_flow_integration.py`. Tests cover plan→build, build→verify, full pipeline continuity, and content integrity.

### File List

- src/adw/core/phase_runner.py (MODIFIED)
- src/adw/commands/template.py (MODIFIED)
- tests/unit/core/test_artifact_passing.py (NEW)
- tests/integration/core/test_artifact_flow_integration.py (NEW)

---

## Dependencies

- **Depends On:** Story 5.2 (PhaseRunner provides the integration point), Story 4.4 (ArtifactManager)
- **Blocks:** Story 5.4 (single phase needs artifact loading from --from-run)
- **Can Parallel With:** Story 5.5 (progress display is independent)

### Dependency Rationale
- Story 5.2: Artifact loading happens in PhaseRunner
- Story 4.4: ArtifactManager provides storage/retrieval
- Story 5.4: --from-run flag needs to load artifacts from previous run

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-02 | BMAD Create-Story | Initial story creation with comprehensive context |
