# Story 5.2: Implement PhaseRunner for Single Phase Execution

Status: ready-for-dev
Linear Issue: not-configured
Epic: 5 - Pipeline Orchestration
Created: 2026-01-02

---

## Story

As a developer,
I want a PhaseRunner that handles all aspects of executing a single phase,
so that phase logic is encapsulated and testable.

## Acceptance Criteria

**Given** a phase to execute
**When** `phase_runner.run(phase, context)` is called
**Then** it executes in order: pre-hook → load prompt → LLM execution → post-hook

**Given** a pre-hook produces output
**When** the prompt is loaded
**Then** pre-hook stdout is available as template variable

**Given** LLM execution completes
**When** post-hook runs
**Then** LLM output is available as environment variable

**Given** any step fails
**When** error is raised
**Then** partial state is captured for debugging

**Given** PhaseRunner
**When** I test with MockExecutor
**Then** the full flow can be exercised without Claude Code

## Tasks / Subtasks

### Task 1: Create PhaseRunner Class
- [x] Create `src/adw/core/phase_runner.py`
- [x] Implement `PhaseRunner` class with constructor
- [x] Accept dependencies: `command_resolver`, `hook_runner`, `executor`
- [x] Accept `artifact_manager` for artifact storage

### Task 2: Implement run() Method
- [x] Add `run(phase: str, context: RunContext) -> PhaseResult` method
- [x] Track phase start time
- [x] Execute steps in order: pre-hook, prompt, LLM, post-hook
- [x] Track phase end time and calculate duration
- [x] Return `PhaseResult` with status, timing, artifacts

### Task 3: Implement Pre-Hook Execution
- [x] Call `hook_runner.run_pre_hook(phase, context)`
- [x] Capture stdout from hook
- [x] Store stdout as `pre_hook_output` for template variable
- [x] Handle `HookError` with phase context
- [x] Log hook execution with structured fields

### Task 4: Implement Prompt Loading
- [x] Call `command_resolver.resolve(phase)` to get command config
- [x] Call `template_engine.render(prompt, variables)` with:
  - `context.*` fields
  - `pre_hook_output` from step 3
  - `artifacts.*` from previous phases
- [x] Handle `CommandError` with phase context

### Task 5: Implement LLM Execution
- [x] Call `executor.execute(prompt, config)`
- [x] Stream output to console (via executor)
- [x] Capture result: `LLMResult` with output, tokens, tool_calls
- [x] Store LLM output as `llm_output` for post-hook
- [x] Handle `LLMError` with phase context

### Task 6: Implement Post-Hook Execution
- [x] Set `ADW_LLM_OUTPUT` environment variable with LLM output
- [x] Call `hook_runner.run_post_hook(phase, context)`
- [x] Capture and log post-hook stdout
- [x] Handle `HookError` with phase context

### Task 7: Implement Artifact Capture
- [x] After successful execution, store phase artifacts
- [x] Store LLM output as artifact: `<phase>_output.md`
- [x] Store any files produced by post-hook
- [x] Return artifact paths in `PhaseResult`

### Task 8: Implement Error State Capture
- [x] On any error, capture partial state
- [x] Store partial `PhaseResult` with `status=FAILED`
- [x] Include error message and phase info
- [x] Log error with full context for debugging

### Task 9: Write Unit Tests
- [x] Create `tests/unit/core/test_phase_runner.py`
- [x] Test successful phase execution flow
- [x] Test pre-hook output available as template variable
- [x] Test LLM output available to post-hook
- [x] Test error state capture
- [x] Test with MockExecutor
- [x] Target: >90% coverage

### Task 10: Write Integration Tests
- [x] Test full phase with MockExecutor
- [x] Test hook → LLM → hook data flow
- [x] Test artifact storage after phase
- [x] Test error recovery and state capture

---

## Developer Context

### Technical Requirements

- **Execution Order**: pre-hook → load prompt → LLM → post-hook
- **Data Flow**: Hook output feeds template, LLM output feeds post-hook
- **Error Handling**: Capture partial state on any failure
- **Testability**: Works with MockExecutor for testing without Claude Code

### Architecture Compliance

**From architecture.md - Phase Runner:**
```
src/adw/
├── core/
│   └── phase_runner.py    # Single phase execution
```

**From architecture.md - FR8-FR9:**
```
FR8: System runs pre-hooks before LLM execution in each phase
FR9: System runs post-hooks after LLM execution in each phase
```

**From architecture.md - FR24:**
```
FR24: System executes pre-hooks and captures stdout for prompt context
```

**From architecture.md - Integration Flow:**
```
PhaseRunner
    │
    ├──▶ HookRunner (pre/post scripts)
    │
    ├──▶ LLMExecutor (Claude Code)
    │
    └──▶ LogManager (events, streaming)
```

**From architecture.md - Executor Protocol:**
```python
class LLMExecutor(Protocol):
    def execute(self, prompt: str, config: ExecutorConfig) -> LLMResult:
        """Execute LLM with prompt and return result."""
        ...
```

### Library & Framework Requirements

**Hook Environment Variables:**
```python
import os

# Set before post-hook
os.environ["ADW_LLM_OUTPUT"] = llm_result.output
os.environ["ADW_RUN_ID"] = context.run_id
os.environ["ADW_PHASE"] = phase
os.environ["ADW_ARTIFACTS_DIR"] = str(artifacts_dir)
```

**Template Variables:**
```python
variables = {
    "context": context.model_dump(),
    "pre_hook_output": pre_hook_result.stdout,
    "artifacts": artifact_manager.get_artifact_paths(context.run_id),
}
rendered_prompt = template_engine.render(prompt_template, variables)
```

**PhaseResult Construction:**
```python
from datetime import datetime, timezone

result = PhaseResult(
    phase=phase,
    status=PhaseStatus.COMPLETED,
    started_at=started_at,
    completed_at=datetime.now(timezone.utc),
    artifacts=[f"{phase}_output.md"],
    tokens_used=llm_result.tokens_used,
    tool_calls=llm_result.tool_calls,
)
```

### File Structure Requirements

**Files to create:**
```
src/adw/
├── core/
│   └── phase_runner.py       # NEW - PhaseRunner class
tests/
├── unit/
│   └── core/
│       └── test_phase_runner.py  # NEW
└── integration/
    └── core/
        └── test_phase_runner_integration.py  # NEW
```

**PhaseRunner Class:**
```python
# src/adw/core/phase_runner.py
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from adw.exceptions import ADWError, HookError, LLMError, CommandError
from adw.models import RunContext, PhaseResult, PhaseStatus

if TYPE_CHECKING:
    from adw.commands.resolver import CommandResolver
    from adw.commands.template import TemplateEngine
    from adw.hooks.runner import HookRunner
    from adw.executors.base import LLMExecutor
    from adw.core.artifact_manager import ArtifactManager

import structlog
logger = structlog.get_logger()


class PhaseRunner:
    """Executes a single phase of the ADW pipeline.

    Coordinates the execution order:
    1. Run pre-hook (capture stdout)
    2. Load and render prompt template
    3. Execute LLM (stream output)
    4. Run post-hook (with LLM output in env)
    5. Capture artifacts

    Attributes:
        command_resolver: Resolves phase commands from config
        template_engine: Renders prompt templates
        hook_runner: Executes pre/post hooks
        executor: LLM executor (Claude Code or Mock)
        artifact_manager: Stores phase artifacts
    """

    def __init__(
        self,
        command_resolver: "CommandResolver",
        template_engine: "TemplateEngine",
        hook_runner: "HookRunner",
        executor: "LLMExecutor",
        artifact_manager: "ArtifactManager",
    ) -> None:
        self.command_resolver = command_resolver
        self.template_engine = template_engine
        self.hook_runner = hook_runner
        self.executor = executor
        self.artifact_manager = artifact_manager

    def run(self, phase: str, context: RunContext) -> PhaseResult:
        """Execute a single phase.

        Args:
            phase: Phase name (plan, build, verify, validate, document)
            context: Current run context

        Returns:
            PhaseResult with status, timing, and artifacts

        Raises:
            HookError: If pre/post hook fails
            CommandError: If command resolution/template fails
            LLMError: If LLM execution fails
        """
        started_at = datetime.now(timezone.utc)
        logger.info("Phase starting", phase=phase, run_id=context.run_id)

        try:
            # Step 1: Run pre-hook
            pre_hook_output = self._run_pre_hook(phase, context)

            # Step 2: Load and render prompt
            rendered_prompt = self._load_and_render_prompt(
                phase, context, pre_hook_output
            )

            # Step 3: Execute LLM
            llm_result = self._execute_llm(phase, context, rendered_prompt)

            # Step 4: Run post-hook
            self._run_post_hook(phase, context, llm_result.output)

            # Step 5: Capture artifacts
            artifacts = self._capture_artifacts(phase, context, llm_result)

            # Build successful result
            completed_at = datetime.now(timezone.utc)
            result = PhaseResult(
                phase=phase,
                status=PhaseStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                artifacts=artifacts,
                tokens_used=llm_result.tokens_used,
                tool_calls=llm_result.tool_calls,
            )

            logger.info(
                "Phase completed",
                phase=phase,
                run_id=context.run_id,
                duration_ms=result.duration_ms,
                tokens=llm_result.tokens_used,
            )

            return result

        except ADWError as e:
            # Capture partial state for debugging
            completed_at = datetime.now(timezone.utc)
            result = PhaseResult(
                phase=phase,
                status=PhaseStatus.FAILED,
                started_at=started_at,
                completed_at=completed_at,
                error=str(e),
            )

            logger.error(
                "Phase failed",
                phase=phase,
                run_id=context.run_id,
                error_code=e.code,
                error=str(e),
            )

            # Re-raise with phase context
            e.phase = phase
            raise

    def _run_pre_hook(self, phase: str, context: RunContext) -> str:
        """Execute pre-hook and capture stdout.

        Args:
            phase: Phase name
            context: Run context

        Returns:
            Pre-hook stdout (empty string if no hook)

        Raises:
            HookError: If hook execution fails
        """
        logger.debug("Running pre-hook", phase=phase)

        try:
            result = self.hook_runner.run_pre_hook(phase, context)
            logger.debug("Pre-hook completed", phase=phase, stdout_len=len(result.stdout))
            return result.stdout
        except HookError as e:
            logger.error("Pre-hook failed", phase=phase, error=str(e))
            raise

    def _load_and_render_prompt(
        self,
        phase: str,
        context: RunContext,
        pre_hook_output: str,
    ) -> str:
        """Load prompt template and render with variables.

        Args:
            phase: Phase name
            context: Run context
            pre_hook_output: Output from pre-hook

        Returns:
            Rendered prompt string

        Raises:
            CommandError: If resolution or rendering fails
        """
        logger.debug("Loading prompt", phase=phase)

        # Resolve command config
        command = self.command_resolver.resolve(phase)

        # Build template variables
        variables = {
            "context": context.model_dump(),
            "pre_hook_output": pre_hook_output,
            "artifacts": self.artifact_manager.get_artifact_paths(context.run_id),
            "run_id": context.run_id,
            "phase": phase,
            "feature": context.feature_description,
        }

        # Render template
        rendered = self.template_engine.render(command.prompt_template, variables)

        logger.debug("Prompt rendered", phase=phase, prompt_len=len(rendered))
        return rendered

    def _execute_llm(
        self,
        phase: str,
        context: RunContext,
        prompt: str,
    ) -> "LLMResult":
        """Execute LLM with rendered prompt.

        Args:
            phase: Phase name
            context: Run context
            prompt: Rendered prompt

        Returns:
            LLMResult with output, tokens, tool calls

        Raises:
            LLMError: If execution fails
        """
        logger.debug("Executing LLM", phase=phase)

        try:
            result = self.executor.execute(prompt)

            logger.debug(
                "LLM execution completed",
                phase=phase,
                tokens=result.tokens_used,
                tool_calls=len(result.tool_calls),
            )
            return result

        except LLMError as e:
            logger.error("LLM execution failed", phase=phase, error=str(e))
            raise

    def _run_post_hook(
        self,
        phase: str,
        context: RunContext,
        llm_output: str,
    ) -> None:
        """Execute post-hook with LLM output available.

        Args:
            phase: Phase name
            context: Run context
            llm_output: Output from LLM execution

        Raises:
            HookError: If hook execution fails
        """
        logger.debug("Running post-hook", phase=phase)

        # Set LLM output in environment for post-hook
        original_env = os.environ.get("ADW_LLM_OUTPUT")
        try:
            os.environ["ADW_LLM_OUTPUT"] = llm_output

            result = self.hook_runner.run_post_hook(phase, context)
            logger.debug("Post-hook completed", phase=phase, stdout_len=len(result.stdout))

        except HookError as e:
            logger.error("Post-hook failed", phase=phase, error=str(e))
            raise
        finally:
            # Restore original env value
            if original_env is None:
                os.environ.pop("ADW_LLM_OUTPUT", None)
            else:
                os.environ["ADW_LLM_OUTPUT"] = original_env

    def _capture_artifacts(
        self,
        phase: str,
        context: RunContext,
        llm_result: "LLMResult",
    ) -> list[str]:
        """Capture and store phase artifacts.

        Args:
            phase: Phase name
            context: Run context
            llm_result: Result from LLM execution

        Returns:
            List of artifact paths
        """
        artifacts = []

        # Store LLM output as artifact
        output_name = f"{phase}_output.md"
        self.artifact_manager.store(
            context.run_id,
            phase,
            output_name,
            llm_result.output,
        )
        artifacts.append(output_name)

        # Store tool calls if any
        if llm_result.tool_calls:
            self.artifact_manager.store_json(
                context.run_id,
                phase,
                f"{phase}_tool_calls.json",
                [tc.model_dump() for tc in llm_result.tool_calls],
            )
            artifacts.append(f"{phase}_tool_calls.json")

        logger.debug("Artifacts captured", phase=phase, count=len(artifacts))
        return artifacts
```

### Testing Requirements

**Test Framework:** pytest

**Test execution flow:**
```python
def test_phase_runner_executes_in_order(phase_runner, mock_hook_runner, mock_executor):
    """Test that PhaseRunner executes steps in correct order."""
    call_order = []

    mock_hook_runner.run_pre_hook.side_effect = lambda *a: call_order.append("pre_hook") or MagicMock(stdout="pre output")
    mock_executor.execute.side_effect = lambda *a: call_order.append("llm") or MagicMock(output="llm output", tokens_used=100)
    mock_hook_runner.run_post_hook.side_effect = lambda *a: call_order.append("post_hook") or MagicMock()

    result = phase_runner.run("plan", sample_context)

    assert call_order == ["pre_hook", "llm", "post_hook"]
    assert result.status == PhaseStatus.COMPLETED
```

**Test pre-hook output in template:**
```python
def test_pre_hook_output_available_in_template(phase_runner, mock_hook_runner, mock_template_engine):
    """Test that pre-hook stdout is available as template variable."""
    mock_hook_runner.run_pre_hook.return_value = MagicMock(stdout="git status output")

    phase_runner.run("build", sample_context)

    # Verify template_engine.render was called with pre_hook_output
    call_args = mock_template_engine.render.call_args
    variables = call_args[0][1]  # Second argument
    assert variables["pre_hook_output"] == "git status output"
```

**Test LLM output to post-hook:**
```python
def test_llm_output_in_post_hook_env(phase_runner, mock_executor, mock_hook_runner):
    """Test that LLM output is available to post-hook via environment."""
    mock_executor.execute.return_value = MagicMock(output="Generated code here")

    captured_env = {}
    def capture_env(*args, **kwargs):
        captured_env["ADW_LLM_OUTPUT"] = os.environ.get("ADW_LLM_OUTPUT")
        return MagicMock()

    mock_hook_runner.run_post_hook.side_effect = capture_env

    phase_runner.run("build", sample_context)

    assert captured_env["ADW_LLM_OUTPUT"] == "Generated code here"
```

**Test error state capture:**
```python
def test_error_captures_partial_state(phase_runner, mock_executor):
    """Test that errors capture partial PhaseResult."""
    from adw.exceptions import LLMError

    mock_executor.execute.side_effect = LLMError(
        code="LLM_TIMEOUT",
        message="Request timed out",
        suggestion="Retry",
        recoverable=True,
    )

    with pytest.raises(LLMError):
        phase_runner.run("plan", sample_context)

    # Verify error was logged with phase context
    # (Check via caplog or mock logger)
```

**Test with MockExecutor:**
```python
def test_phase_runner_with_mock_executor(phase_runner_with_mock):
    """Test full flow with MockExecutor (no Claude Code needed)."""
    result = phase_runner_with_mock.run("plan", sample_context)

    assert result.status == PhaseStatus.COMPLETED
    assert result.tokens_used > 0
    assert len(result.artifacts) > 0
```

**Coverage Target:** >80% overall, >90% for `phase_runner.py`

---

## Previous Story Intelligence

**From Story 3.1 (Shell Hooks):**
- `HookRunner` exists at `src/adw/hooks/runner.py`
- Use `run_pre_hook(phase, context)` and `run_post_hook(phase, context)`
- Returns `HookResult` with `stdout`, `stderr`, `exit_code`

**From Story 3.2 (Claude Code Executor):**
- `ClaudeCodeExecutor` exists at `src/adw/executors/claude_code.py`
- Implements `LLMExecutor` protocol
- Returns `LLMResult` with `output`, `tokens_used`, `tool_calls`

**From Story 2.2 (Template Engine):**
- `TemplateEngine` exists at `src/adw/commands/template.py`
- Use `render(template, variables)` method
- Variables: `{{variable.path}}` and `{{file:path}}`

**From Story 2.1 (Command Resolution):**
- `CommandResolver` exists at `src/adw/commands/resolver.py`
- Use `resolve(phase)` to get command config
- Returns `ResolvedCommand` with `prompt_template`, `config`, `hooks`

**Key patterns:**
- Environment variables for hook context
- Structured logging with phase info
- Error codes from exception hierarchy

---

## Git Intelligence

**From Epic 3:**
- Hook execution returns `HookResult` with stdout
- LLM execution returns `LLMResult` with output and tokens
- Both raise typed exceptions with `recoverable` flag

**Existing modules:**
- `src/adw/hooks/runner.py` - HookRunner
- `src/adw/executors/claude_code.py` - ClaudeCodeExecutor
- `src/adw/executors/mock.py` - MockExecutor for testing
- `src/adw/commands/resolver.py` - CommandResolver
- `src/adw/commands/template.py` - TemplateEngine

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:

1. **Execution Order**: pre-hook → prompt → LLM → post-hook
2. **Environment Variables**: Set `ADW_*` vars before hooks
3. **Error Handling**: Capture partial state, add phase context
4. **Structured Logging**: Include phase, run_id in all logs
5. **Artifact Storage**: Store LLM output and tool calls

---

## Dev Notes

### Key Implementation Points

1. **Pre-hook Output to Template**:
   ```python
   pre_hook_output = self.hook_runner.run_pre_hook(phase, context).stdout
   variables = {"pre_hook_output": pre_hook_output, ...}
   rendered = self.template_engine.render(template, variables)
   ```

2. **LLM Output to Post-hook**:
   ```python
   os.environ["ADW_LLM_OUTPUT"] = llm_result.output
   self.hook_runner.run_post_hook(phase, context)
   ```

3. **Partial State on Error**:
   ```python
   except ADWError as e:
       result = PhaseResult(
           phase=phase,
           status=PhaseStatus.FAILED,
           error=str(e),
           ...
       )
       e.phase = phase
       raise
   ```

4. **Artifact Capture**:
   ```python
   self.artifact_manager.store(run_id, phase, f"{phase}_output.md", llm_output)
   ```

### Project Structure Notes

- PhaseRunner is called by Orchestrator (Story 5.1)
- Works with existing Hook, Executor, Command components
- Story 5.3 extends this for artifact passing

### References

- [Source: _bmad-output/architecture.md#Phase-Runner]
- [Source: _bmad-output/architecture.md#FR8-FR9]
- [Source: _bmad-output/architecture.md#FR24]
- [Source: src/adw/hooks/runner.py] - HookRunner
- [Source: src/adw/executors/claude_code.py] - ClaudeCodeExecutor
- [Source: src/adw/commands/resolver.py] - CommandResolver

---

## Dev Agent Record

### Context Reference

Story 5.2 implements PhaseRunner for single phase execution, coordinating hooks, prompt rendering, and LLM execution.

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** Story 5.1 (Orchestrator calls PhaseRunner), Epic 2 (Commands), Epic 3 (Hooks, Executor)
- **Blocks:** Story 5.3 (artifact passing uses PhaseRunner), Story 5.4 (single phase needs PhaseRunner)
- **Can Parallel With:** None - foundational for later 5.x stories

### Dependency Rationale
- Story 5.1: Orchestrator needs PhaseRunner for execution
- Epic 2: Command resolution and template engine needed
- Epic 3: Hook runner and LLM executor needed
- Story 5.3: Extends PhaseRunner with artifact passing
- Story 5.4: Uses PhaseRunner for isolated execution

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-01-02 | BMAD Create-Story | Initial story creation with comprehensive context |
