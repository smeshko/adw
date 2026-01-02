# Story 5.4: Execute Single Phase in Isolation

Status: ready-for-dev
Linear Issue: not-configured
Epic: 5 - Pipeline Orchestration
Created: 2026-01-02

---

## Story

As a developer,
I want to execute a single phase without running the full pipeline,
so that I can test or re-run specific phases.

## Acceptance Criteria

**Given** command `adw run --phase plan --feature "Add login"`
**When** executed
**Then** only the Plan phase runs

**Given** a single-phase run
**When** previous phase artifacts are needed
**Then** they're loaded from a specified run ID or error is raised

**Given** command `adw run --phase build --from-run <id>`
**When** executed
**Then** artifacts from run <id> are used as input

**Given** single-phase execution
**When** it completes
**Then** artifacts are stored in the current run, not the source run

## Tasks / Subtasks

### Task 1: Add --phase Flag to CLI
- [x] Update `src/adw/cli/run.py` to accept `--phase` option
- [x] Validate phase is one of PHASE_SEQUENCE
- [x] Pass phase to orchestrator

### Task 2: Add --from-run Flag to CLI
- [x] Add `--from-run` option for specifying source run ID
- [x] Validate run ID exists
- [x] Require `--from-run` if phase is not "plan"

### Task 3: Implement run_single_phase() in Orchestrator
- [x] Add `run_single_phase(phase, feature, from_run_id=None)` method
- [x] Generate new run ID for this execution
- [x] Create initial RunContext
- [x] Execute only the specified phase

### Task 4: Load Artifacts from Source Run
- [x] When `--from-run` is specified, load artifacts from source run
- [x] Copy artifact paths to new run's context
- [x] Do NOT modify source run's artifacts directory
- [x] Build artifacts map from source run for template access

### Task 5: Validate Phase Requirements
- [x] If phase > "plan" and no `--from-run`, check for needed artifacts
- [x] Raise ConfigError if required artifacts missing
- [x] Suggest using `--from-run` in error message

### Task 6: Store Artifacts in Current Run
- [ ] Create artifact directory for new run
- [ ] Store phase output in new run's artifacts
- [ ] Update new run's context with artifact paths
- [ ] Keep source run unchanged

### Task 7: Handle Phase Dependencies
- [ ] For "verify" phase: ensure build artifacts available
- [ ] For "validate" phase: ensure verify artifacts available
- [ ] For "document" phase: ensure all previous artifacts available
- [ ] Map phase to required previous phases

### Task 8: Write Unit Tests
- [ ] Create `tests/unit/cli/test_run_single_phase.py`
- [ ] Test --phase flag parsing
- [ ] Test --from-run validation
- [ ] Test single phase execution
- [ ] Test artifact loading from source run
- [ ] Test artifact storage in new run
- [ ] Target: >90% coverage

### Task 9: Write Integration Tests
- [ ] Test `adw run --phase plan --feature "X"`
- [ ] Test `adw run --phase build --from-run <id>`
- [ ] Test artifacts not copied to source run
- [ ] Test complete single-phase workflow

---

## Developer Context

### Technical Requirements

- **CLI Flags**: `--phase <name>` and `--from-run <id>`
- **New Run ID**: Single phase creates its own run, not modifying source
- **Artifact Source**: Load from specified run, store to current
- **Validation**: Check required artifacts before executing

### Architecture Compliance

**From architecture.md - FR12:**
```
FR12: User can execute a single phase in isolation
```

**From PRD - MVP Scope:**
```
- `adw run --phase <phase>` — Execute single phase
```

**From architecture.md - CLI Patterns:**
```
# Options: double-dash + kebab-case
--run-id, --from-phase, --verbose
```

### Library & Framework Requirements

**Typer CLI Options:**
```python
from typing import Optional
import typer

@app.command()
def run(
    feature: str = typer.Argument(..., help="Feature description"),
    phase: Optional[str] = typer.Option(
        None,
        "--phase",
        "-p",
        help="Execute single phase only",
    ),
    from_run: Optional[str] = typer.Option(
        None,
        "--from-run",
        "-f",
        help="Load artifacts from this run ID",
    ),
) -> None:
    """Execute ADW pipeline or single phase."""
    if phase:
        orchestrator.run_single_phase(phase, feature, from_run)
    else:
        orchestrator.run(feature)
```

**Phase Requirements Map:**
```python
PHASE_REQUIREMENTS: dict[str, list[str]] = {
    "plan": [],  # No requirements
    "build": ["plan"],  # Needs plan artifact
    "verify": ["plan", "build"],  # Needs plan and build
    "validate": ["plan", "build", "verify"],  # Needs all above
    "document": ["plan", "build", "verify", "validate"],  # Needs all
}
```

**Artifact Loading from Source Run:**
```python
def _load_artifacts_from_source(
    self,
    source_run_id: str,
    required_phases: list[str],
) -> dict[str, dict[str, str]]:
    """Load artifacts from a previous run.

    Args:
        source_run_id: Run ID to load from
        required_phases: Phases whose artifacts are needed

    Returns:
        Artifacts map for template access

    Raises:
        ConfigError: If source run not found or missing required artifacts
    """
    # Verify source run exists
    source_context = self.context_manager.load(source_run_id)
    if not source_context:
        raise ConfigError(
            code="RUN_NOT_FOUND",
            message=f"Source run '{source_run_id}' not found",
            suggestion="Check run ID with 'adw list-runs'",
            recoverable=False,
        )

    # Build artifacts map from source
    artifacts_map = {}
    for phase in required_phases:
        phase_artifacts = self.artifact_manager.list_artifacts(source_run_id, phase)
        if not phase_artifacts:
            raise ConfigError(
                code="MISSING_ARTIFACTS",
                message=f"Source run missing {phase} artifacts",
                suggestion=f"Run {phase} phase first",
                recoverable=False,
            )

        phase_map = {}
        for artifact in phase_artifacts:
            name = Path(artifact["name"]).stem
            content = self.artifact_manager.get(source_run_id, phase, artifact["name"])
            if content:
                phase_map[name] = content
        artifacts_map[phase] = phase_map

    return artifacts_map
```

### File Structure Requirements

**Files to modify:**
```
src/adw/
├── cli/
│   └── run.py                # MODIFY - add --phase, --from-run
├── core/
│   ├── orchestrator.py       # MODIFY - add run_single_phase()
│   └── constants.py          # MODIFY - add PHASE_REQUIREMENTS
tests/
├── unit/
│   └── cli/
│       └── test_run_single_phase.py  # NEW
└── integration/
    └── test_single_phase_integration.py  # NEW
```

**Updated Orchestrator:**
```python
# src/adw/core/orchestrator.py

PHASE_REQUIREMENTS: dict[str, list[str]] = {
    "plan": [],
    "build": ["plan"],
    "verify": ["plan", "build"],
    "validate": ["plan", "build", "verify"],
    "document": ["plan", "build", "verify", "validate"],
}


class Orchestrator:
    # ... existing code ...

    def run_single_phase(
        self,
        phase: str,
        feature_description: str,
        from_run_id: str | None = None,
    ) -> RunContext:
        """Execute a single phase in isolation.

        Args:
            phase: Phase to execute
            feature_description: Feature being developed
            from_run_id: Source run ID for artifacts (required if phase > plan)

        Returns:
            RunContext for this single-phase execution

        Raises:
            ConfigError: If validation fails or artifacts missing
            ADWError: If phase execution fails
        """
        # Validate phase
        if phase not in PHASE_SEQUENCE:
            raise ConfigError(
                code="INVALID_PHASE",
                message=f"Unknown phase: {phase}",
                suggestion=f"Valid phases: {', '.join(PHASE_SEQUENCE)}",
                recoverable=False,
            )

        # Check required artifacts
        required_phases = PHASE_REQUIREMENTS[phase]
        if required_phases and not from_run_id:
            raise ConfigError(
                code="MISSING_FROM_RUN",
                message=f"Phase '{phase}' requires artifacts from previous phases",
                suggestion=f"Use --from-run <run_id> to specify source run",
                recoverable=False,
            )

        # Generate new run ID
        run_id = str(ULID())

        # Load artifacts from source if specified
        source_artifacts = {}
        if from_run_id:
            source_artifacts = self._load_artifacts_from_source(
                from_run_id, required_phases
            )

        # Create context for this run
        context = RunContext(
            run_id=run_id,
            feature_description=feature_description,
            current_phase=phase,
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        # Create run directory
        self.run_directory.create(run_id)

        # Persist initial state
        self.context_manager.save(context)

        logger.info(
            "Starting single-phase run",
            run_id=run_id,
            phase=phase,
            from_run=from_run_id,
        )

        try:
            # Execute the single phase
            result = self._execute_phase_with_source_artifacts(
                context, phase, source_artifacts
            )

            # Mark as completed
            context = context.model_copy(update={
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
                "phase_history": [phase],
            })
            self.context_manager.save(context)

            logger.info("Single-phase run completed", run_id=run_id, phase=phase)

        except ADWError as e:
            context = context.model_copy(update={
                "status": "failed",
                "completed_at": datetime.now(timezone.utc),
            })
            self.context_manager.save(context)
            raise

        return context

    def _execute_phase_with_source_artifacts(
        self,
        context: RunContext,
        phase: str,
        source_artifacts: dict[str, dict[str, str]],
    ) -> PhaseResult:
        """Execute phase with pre-loaded artifacts from source run.

        Args:
            context: Current run context
            phase: Phase to execute
            source_artifacts: Artifacts loaded from source run

        Returns:
            PhaseResult from execution
        """
        # Create pre-phase snapshot
        self.snapshot_manager.create_pre_phase_snapshot(context, phase)

        # Execute phase (PhaseRunner will use source_artifacts)
        result = self._phase_runner.run(
            phase,
            context,
            artifacts_override=source_artifacts,
        )

        # Create post-phase snapshot
        self.snapshot_manager.create_post_phase_snapshot(context, phase, result)

        return result
```

**Updated CLI:**
```python
# src/adw/cli/run.py
from typing import Optional
import typer

from adw.core.constants import PHASE_SEQUENCE
from adw.core.orchestrator import Orchestrator
from adw.exceptions import ConfigError

app = typer.Typer()


@app.command()
def run(
    feature: str = typer.Argument(..., help="Feature description"),
    phase: Optional[str] = typer.Option(
        None,
        "--phase",
        "-p",
        help=f"Execute single phase only ({', '.join(PHASE_SEQUENCE)})",
    ),
    from_run: Optional[str] = typer.Option(
        None,
        "--from-run",
        "-f",
        help="Load artifacts from this run ID (required for phases after plan)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Execute ADW pipeline or single phase.

    Examples:
        # Full pipeline
        adw run "Add user authentication"

        # Single phase
        adw run --phase plan --feature "Add login"

        # Single phase with artifacts from previous run
        adw run --phase build --from-run 01HQXK5P3Z7V --feature "Add login"
    """
    orchestrator = get_orchestrator()  # Factory function

    try:
        if phase:
            # Validate phase
            if phase not in PHASE_SEQUENCE:
                raise typer.BadParameter(
                    f"Invalid phase: {phase}. Valid: {', '.join(PHASE_SEQUENCE)}"
                )

            context = orchestrator.run_single_phase(phase, feature, from_run)
        else:
            context = orchestrator.run(feature)

        # Display success
        console.print(f"[green]✓[/] Run completed: {context.run_id}")

    except ConfigError as e:
        console.print(f"[red]Error:[/] {e.message}")
        console.print(f"[dim]Suggestion:[/] {e.suggestion}")
        raise typer.Exit(1)
```

### Testing Requirements

**Test Framework:** pytest

**Test --phase flag:**
```python
def test_phase_flag_parsed(cli_runner):
    """Test that --phase flag is correctly parsed."""
    result = cli_runner.invoke(app, ["--phase", "plan", "Add feature"])

    assert result.exit_code == 0
    # Verify only plan phase executed
```

**Test --from-run required:**
```python
def test_from_run_required_for_build(cli_runner):
    """Test that --from-run is required for phases after plan."""
    result = cli_runner.invoke(app, ["--phase", "build", "Add feature"])

    assert result.exit_code == 1
    assert "requires artifacts" in result.output
    assert "--from-run" in result.output
```

**Test artifact loading:**
```python
def test_artifacts_loaded_from_source_run(orchestrator, artifact_manager):
    """Test that artifacts are loaded from source run."""
    # Create source run with artifacts
    source_run_id = "01HQTEST"
    artifact_manager.store(source_run_id, "plan", "plan.md", "# Plan")

    # Run build phase
    context = orchestrator.run_single_phase("build", "Feature", source_run_id)

    # Verify artifacts were used (check via mock)
    assert context.status == "completed"
```

**Test artifacts stored in new run:**
```python
def test_artifacts_stored_in_new_run(orchestrator, artifact_manager):
    """Test that artifacts go to new run, not source run."""
    source_run_id = "01HQSOURCE"
    artifact_manager.store(source_run_id, "plan", "plan.md", "# Plan")

    context = orchestrator.run_single_phase("build", "Feature", source_run_id)

    # New run has build artifact
    build_artifacts = artifact_manager.list_artifacts(context.run_id, "build")
    assert len(build_artifacts) > 0

    # Source run unchanged
    source_build = artifact_manager.list_artifacts(source_run_id, "build")
    assert len(source_build) == 0
```

**Coverage Target:** >80% overall, >90% for single phase logic

---

## Previous Story Intelligence

**From Story 5.1 (Orchestrator):**
- Orchestrator has `run()` method for full pipeline
- Need to add `run_single_phase()` method
- Same error handling and state management patterns

**From Story 5.3 (Artifact Passing):**
- `_build_artifacts_map()` builds artifacts for templates
- Need to support loading from different run ID
- Same artifact access pattern in templates

**Key patterns:**
- New run ID for each execution
- Source artifacts are read-only
- Validate requirements before executing

---

## Git Intelligence

**From Epic 5:**
- Orchestrator exists at `src/adw/core/orchestrator.py`
- PHASE_SEQUENCE defined in constants
- PhaseRunner available for single phase execution

**CLI patterns:**
- Typer app at `src/adw/cli/`
- Options use double-dash kebab-case
- Error handling with ConfigError

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **CLI Options**: `--phase`, `--from-run` with short forms `-p`, `-f`
2. **Validation**: Check requirements before execution
3. **Isolation**: New run ID, don't modify source run
4. **Error Messages**: Include suggestion for recovery

---

## Dev Notes

### Key Implementation Points

1. **Phase Requirements Map**:
   ```python
   PHASE_REQUIREMENTS = {
       "plan": [],
       "build": ["plan"],
       "verify": ["plan", "build"],
       ...
   }
   ```

2. **New Run for Single Phase**:
   ```python
   run_id = str(ULID())  # Always new run
   # Source run is read-only
   ```

3. **Artifact Override in PhaseRunner**:
   ```python
   result = self._phase_runner.run(
       phase, context,
       artifacts_override=source_artifacts,  # From --from-run
   )
   ```

4. **CLI Error Handling**:
   ```python
   except ConfigError as e:
       console.print(f"[red]Error:[/] {e.message}")
       console.print(f"[dim]Suggestion:[/] {e.suggestion}")
       raise typer.Exit(1)
   ```

### Project Structure Notes

- Extends Orchestrator from Story 5.1
- Uses artifact loading from Story 5.3
- CLI updates in cli/run.py

### References

- [Source: _bmad-output/architecture.md#FR12]
- [Source: _bmad-output/prd.md#MVP-Scope]
- [Source: src/adw/core/orchestrator.py] - Orchestrator
- [Source: src/adw/cli/] - CLI commands

---

## Dev Agent Record

### Context Reference

Story 5.4 implements single-phase execution mode, allowing developers to run individual phases with artifacts from previous runs.

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- **Task 1**: Added `--phase` and `-p` flags to CLI run command in `app.py`. Implemented `_validate_phase()` callback that validates phase against `PHASE_SEQUENCE`. Tests added in `test_run.py` covering flag acceptance, validation, and all valid phases. Implementation uses Typer callbacks for validation.
- **Task 2**: Added `--from-run` and `-f` flags to CLI. Implemented validation that non-plan phases require `--from-run` with helpful error messages. Added 6 tests in `TestFromRunFlag` class covering flag acceptance, requirement enforcement, and plan phase exemption.
- **Task 3**: Implemented `run_single_phase()` method in Orchestrator. Method generates new ULID, creates RunContext, executes only the specified phase using existing `_execute_phase_with_transitions()`, and handles completion/failure states. Added 8 tests in `TestRunSinglePhase` class.
- **Task 4**: Implemented `_load_artifacts_from_source()` method in Orchestrator to load artifacts from source run. Modified PhaseRunner.run() to accept `artifacts_override` parameter for pre-loaded artifacts. Updated PhaseRunnerProtocol and all execution methods to propagate artifacts_override. Added 3 tests in `TestLoadArtifactsFromSource` class.
- **Task 5**: Added `_validate_required_artifacts()` method in Orchestrator that checks source run has artifacts from all required previous phases. Raises ConfigError with helpful message if missing. Added 3 tests in `TestPhaseRequirementsValidation` class.

### File List

- `src/adw/cli/app.py` - Modified: Added --phase and --from-run flags with validation
- `src/adw/core/orchestrator.py` - Modified: Added run_single_phase(), _load_artifacts_from_source(), artifacts_override support
- `src/adw/core/phase_runner.py` - Modified: Added artifacts_override parameter to run() and _load_and_render_prompt()
- `tests/unit/cli/test_run.py` - Modified: Added TestFromRunFlag test class
- `tests/unit/core/test_orchestrator.py` - Modified: Added TestRunSinglePhase, TestLoadArtifactsFromSource test classes

---

## Dependencies

- **Depends On:** Story 5.1 (Orchestrator), Story 5.2 (PhaseRunner), Story 5.3 (artifact passing)
- **Blocks:** None - this is a feature extension
- **Can Parallel With:** Story 5.5 (progress display)

### Dependency Rationale
- Story 5.1: Orchestrator provides run infrastructure
- Story 5.2: PhaseRunner executes the single phase
- Story 5.3: Artifact loading mechanism needed for --from-run

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-02 | BMAD Create-Story | Initial story creation with comprehensive context |
