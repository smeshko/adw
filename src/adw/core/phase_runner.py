"""Phase runner for single phase execution.

This module provides the PhaseRunner class that coordinates all aspects
of executing a single phase: pre-hook → prompt loading → LLM execution →
post-hook → artifact capture.
"""

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable
from typing import TYPE_CHECKING

from adw.core.constants import PHASE_SEQUENCE
from adw.exceptions import ADWError, CommandError, ConfigError, HookError, LLMError
from adw.hooks.runner import find_hook
from adw.models import (
    HookResult,
    LLMResult,
    PhaseResult,
    PhaseStatus,
    ResolvedCommand,
    RunContext,
)

if TYPE_CHECKING:
    from adw.cli.progress import ProgressDisplay
    from adw.commands.resolver import CommandResolver
    from adw.commands.template import TemplateEngine
    from adw.core.artifact_manager import ArtifactManager
    from adw.executors.base import LLMExecutor
    from adw.hooks.runner import HookRunner

# Type alias for progress callbacks
ProgressCallback = Callable[[int], None]  # Callback receiving token count

logger = logging.getLogger(__name__)

# Pattern to match artifact references in templates: {{artifacts.phase.name}}
# Also matches wildcards like {{artifacts.phase.*}} and {{artifacts.*}}
ARTIFACT_REF_PATTERN = re.compile(r"\{\{artifacts\.([a-z_][a-z0-9_.]*(?:\.\*)?)\}\}")


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
        strict_artifacts: If True, raise ConfigError for missing artifact refs

    Example:
        >>> runner = PhaseRunner(
        ...     command_resolver=resolver,
        ...     template_engine=engine,
        ...     hook_runner=hook_runner,
        ...     executor=executor,
        ...     artifact_manager=artifact_manager,
        ...     strict_artifacts=True,
        ... )
        >>> result = runner.run("plan", context)
        >>> print(result.status)
        PhaseStatus.COMPLETED
    """

    def __init__(
        self,
        command_resolver: "CommandResolver",
        template_engine: "TemplateEngine",
        hook_runner: "HookRunner",
        executor: "LLMExecutor",
        artifact_manager: "ArtifactManager",
        *,
        strict_artifacts: bool = False,
        progress_display: "ProgressDisplay | None" = None,
    ) -> None:
        """Initialize the PhaseRunner.

        Args:
            command_resolver: Resolves phase commands from config.
            template_engine: Renders prompt templates.
            hook_runner: Executes pre/post hooks.
            executor: LLM executor (Claude Code or Mock).
            artifact_manager: Stores phase artifacts.
            strict_artifacts: If True, raise ConfigError when a template
                references a missing artifact. If False (default), missing
                artifacts are replaced with empty strings.
            progress_display: Display for LLM progress (optional, Story 5.5).
        """
        self.command_resolver = command_resolver
        self.template_engine = template_engine
        self.hook_runner = hook_runner
        self.executor = executor
        self.artifact_manager = artifact_manager
        self.strict_artifacts = strict_artifacts
        self.progress_display = progress_display

    def run(self, phase: str, context: RunContext) -> PhaseResult:
        """Execute a single phase.

        Args:
            phase: Phase name (plan, build, verify, validate, document).
            context: Current run context.

        Returns:
            PhaseResult with status, timing, and artifacts.

        Raises:
            HookError: If pre/post hook fails.
            CommandError: If command resolution/template fails.
            LLMError: If LLM execution fails.
        """
        started_at = datetime.now(timezone.utc)
        logger.info("Phase starting", extra={"phase": phase, "run_id": context.run_id})

        # Resolve command once for all steps
        command = self.command_resolver.resolve(phase)

        try:
            # Step 1: Run pre-hook
            pre_hook_output = self._run_pre_hook(phase, context, command)

            # Step 2: Load and render prompt
            rendered_prompt = self._load_and_render_prompt(
                phase, context, pre_hook_output, command
            )

            # Step 3: Execute LLM
            llm_result = self._execute_llm(phase, context, rendered_prompt)

            # Step 4: Run post-hook
            self._run_post_hook(phase, context, llm_result.content, command)

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
                extra={
                    "phase": phase,
                    "run_id": context.run_id,
                    "duration_ms": result.duration_ms,
                    "tokens": llm_result.tokens_used,
                },
            )

            return result

        except ADWError as e:
            # Capture partial state for debugging
            completed_at = datetime.now(timezone.utc)
            failed_result = PhaseResult(
                phase=phase,
                status=PhaseStatus.FAILED,
                started_at=started_at,
                completed_at=completed_at,
                error=str(e),
            )

            logger.error(
                "Phase failed",
                extra={
                    "phase": phase,
                    "run_id": context.run_id,
                    "error_code": e.code,
                    "error": str(e),
                    "duration_ms": failed_result.duration_ms,
                },
            )

            # Re-raise with phase context if applicable
            if hasattr(e, "phase") and e.phase is None:
                e.phase = phase
            raise

    def _run_pre_hook(
        self, phase: str, context: RunContext, command: ResolvedCommand
    ) -> str:
        """Execute pre-hook and capture stdout.

        Args:
            phase: Phase name.
            context: Run context.
            command: Resolved command configuration.

        Returns:
            Pre-hook stdout (empty string if no hook).

        Raises:
            HookError: If hook execution fails.
        """
        logger.debug("Running pre-hook", extra={"phase": phase})

        if not command.has_pre_hook:
            logger.debug("No pre-hook for phase", extra={"phase": phase})
            return ""

        # Find and run pre-hook
        hook_path = find_hook(command.path, "pre")
        if hook_path is None:
            return ""

        try:
            result = self.hook_runner.run_hook(
                hook_path=hook_path,
                context=context,
                phase=phase,
                hook_type="pre",
            )
            logger.debug(
                "Pre-hook completed",
                extra={"phase": phase, "stdout_len": len(result.stdout)},
            )
            return result.stdout
        except HookError:
            logger.error("Pre-hook failed", extra={"phase": phase})
            raise

    def _load_and_render_prompt(
        self,
        phase: str,
        context: RunContext,
        pre_hook_output: str,
        command: ResolvedCommand,
    ) -> str:
        """Load prompt template and render with variables.

        Includes artifact content from previous phases for template access.
        Validates artifact references before rendering and raises ARTIFACT_NOT_FOUND
        if strict_artifacts is enabled and an artifact is missing.

        Template Artifact Access:
            - {{artifacts.phase.name}} - Access specific artifact content
            - {{artifacts.phase.*}} - List all artifacts in a phase
            - {{artifacts.*}} - List all phases with artifacts

        Args:
            phase: Phase name.
            context: Run context.
            pre_hook_output: Output from pre-hook.
            command: Resolved command configuration.

        Returns:
            Rendered prompt string.

        Raises:
            CommandError: If resolution or rendering fails.
            ConfigError: If strict_artifacts=True and artifact not found.
        """
        logger.debug("Loading prompt", extra={"phase": phase})

        # Read the prompt template
        prompt_path = command.path / "prompt.md"
        prompt_template = prompt_path.read_text(encoding="utf-8")

        # Build artifacts map from previous phases (FR11)
        artifacts_map = self._build_artifacts_map(context.run_id, phase)

        # Validate artifact references in template
        # Raises ConfigError if strict_artifacts=True and artifact missing
        self._validate_artifact_references(prompt_template, artifacts_map)

        # Build template variables
        variables = {
            "context": context.model_dump(),
            "pre_hook_output": pre_hook_output,
            "artifacts": artifacts_map,  # Nested: {phase: {name: content}}
            "run_id": context.run_id,
            "phase": phase,
            "feature": context.feature_description,
        }

        # Render template with strict matching artifact mode:
        # - strict_artifacts=True: We validated artifacts, use strict=True for all vars
        # - strict_artifacts=False: Lenient mode, allow missing refs to pass through
        rendered = self.template_engine.render(
            prompt_template, variables, strict=self.strict_artifacts
        )

        logger.debug(
            "Prompt rendered", extra={"phase": phase, "prompt_len": len(rendered)}
        )
        return rendered

    def _validate_artifact_references(
        self,
        template: str,
        artifacts_map: dict[str, dict[str, str]],
    ) -> None:
        """Validate that all artifact references in template exist.

        Scans the template for {{artifacts.phase.name}} patterns and validates
        each reference exists in the artifacts map. Logs warnings for missing
        artifacts regardless of strict mode.

        Args:
            template: The prompt template string.
            artifacts_map: Available artifacts {phase: {name: content}}.

        Raises:
            ConfigError: If strict_artifacts=True and an artifact is missing.
        """
        # Find all artifact references in the template
        matches = ARTIFACT_REF_PATTERN.findall(template)
        if not matches:
            return

        missing_artifacts: list[str] = []

        for ref_path in matches:
            # Skip wildcard patterns - they don't require specific artifacts
            if ref_path.endswith(".*") or ref_path == "*":
                continue

            # Parse the reference path (e.g., "plan.plan" or "build.diff")
            parts = ref_path.split(".")
            if len(parts) < 2:
                # Single part like "plan" - this accesses the phase dict, not an artifact
                continue

            phase_name = parts[0]
            artifact_name = parts[1]

            # Check if artifact exists
            if phase_name not in artifacts_map:
                missing_artifacts.append(f"{phase_name}/{artifact_name}")
                logger.warning(
                    "Missing artifact reference in template",
                    extra={
                        "phase": phase_name,
                        "artifact": artifact_name,
                        "ref": f"artifacts.{ref_path}",
                    },
                )
            elif artifact_name not in artifacts_map[phase_name]:
                missing_artifacts.append(f"{phase_name}/{artifact_name}")
                logger.warning(
                    "Missing artifact reference in template",
                    extra={
                        "phase": phase_name,
                        "artifact": artifact_name,
                        "ref": f"artifacts.{ref_path}",
                        "available": list(artifacts_map[phase_name].keys()),
                    },
                )

        # Raise error if strict mode and artifacts missing
        if self.strict_artifacts and missing_artifacts:
            raise ConfigError(
                code="ARTIFACT_NOT_FOUND",
                message=f"Artifact(s) not found: {', '.join(missing_artifacts)}",
                suggestion=(
                    "Ensure the referenced phase(s) completed successfully and "
                    "produced the expected artifacts. Check artifact naming "
                    "(e.g., plan.md -> artifacts.plan.plan)."
                ),
            )

    def _load_phase_artifacts(
        self,
        run_id: str,
        phase: str,
    ) -> dict[str, str]:
        """Load all artifacts for a given phase.

        Retrieves all artifacts stored for the specified phase and returns
        their content. File extensions are stripped from artifact names for
        cleaner template access (e.g., plan.md -> plan).

        Args:
            run_id: The run ID.
            phase: Phase name to load artifacts from.

        Returns:
            Dict mapping artifact names (without extension) to content.
            Empty dict if no artifacts exist for the phase.

        Example:
            >>> artifacts = runner._load_phase_artifacts("run1", "plan")
            >>> plan_content = artifacts["plan"]  # Content of plan.md
        """
        phase_artifacts = self.artifact_manager.list_artifacts(run_id, phase)
        if not phase_artifacts:
            return {}

        phase_map: dict[str, str] = {}
        for artifact in phase_artifacts:
            # Strip extension: plan.md -> plan
            name = Path(artifact["name"]).stem
            content = self.artifact_manager.get(run_id, phase, artifact["name"])
            if content:
                phase_map[name] = content

        logger.debug(
            "Loaded phase artifacts",
            extra={
                "run_id": run_id,
                "phase": phase,
                "artifact_count": len(phase_map),
                "artifact_names": list(phase_map.keys()),
            },
        )

        return phase_map

    def _build_artifacts_map(
        self,
        run_id: str,
        current_phase: str,
    ) -> dict[str, dict[str, str]]:
        """Build map of artifacts from previous phases.

        Only includes phases that completed before current_phase.
        File extensions are stripped from artifact names for cleaner
        template access (e.g., plan.md -> artifacts.plan.plan).

        Args:
            run_id: Current run ID.
            current_phase: Phase about to execute.

        Returns:
            Nested dict: {phase: {artifact_name: content}}

        Example:
            >>> artifacts = runner._build_artifacts_map("run1", "build")
            >>> plan_content = artifacts["plan"]["plan"]  # plan.md content
        """
        artifacts_map: dict[str, dict[str, str]] = {}

        # Only load artifacts from phases before current
        try:
            current_idx = PHASE_SEQUENCE.index(current_phase)
        except ValueError:
            # Unknown phase - return empty map
            logger.warning(
                "Unknown phase in artifact map",
                extra={"phase": current_phase},
            )
            return artifacts_map

        previous_phases = PHASE_SEQUENCE[:current_idx]

        for phase in previous_phases:
            phase_map = self._load_phase_artifacts(run_id, phase)
            if phase_map:
                artifacts_map[phase] = phase_map

        logger.debug(
            "Built artifacts map",
            extra={
                "run_id": run_id,
                "current_phase": current_phase,
                "phases_with_artifacts": list(artifacts_map.keys()),
            },
        )

        return artifacts_map

    def _execute_llm(
        self,
        phase: str,
        context: RunContext,
        prompt: str,
    ) -> LLMResult:
        """Execute LLM with rendered prompt.

        Args:
            phase: Phase name.
            context: Run context.
            prompt: Rendered prompt.

        Returns:
            LLMResult with output, tokens, tool calls.

        Raises:
            LLMError: If execution fails.
        """
        logger.debug("Executing LLM", extra={"phase": phase})

        # Start LLM progress display (Story 5.5)
        if self.progress_display:
            self.progress_display.on_llm_start()

        try:
            result = self.executor.execute(prompt)

            logger.debug(
                "LLM execution completed",
                extra={
                    "phase": phase,
                    "tokens": result.tokens_used,
                    "tool_calls": len(result.tool_calls),
                },
            )

            # Update final token count before completing (Story 5.5)
            if self.progress_display:
                self.progress_display.on_llm_progress(result.tokens_used)
                self.progress_display.on_llm_complete()

            return result

        except LLMError:
            logger.error("LLM execution failed", extra={"phase": phase})
            # Stop progress display on error (Story 5.5)
            if self.progress_display:
                self.progress_display.on_llm_complete()
            raise

    def _run_post_hook(
        self,
        phase: str,
        context: RunContext,
        llm_output: str,
        command: ResolvedCommand,
    ) -> None:
        """Execute post-hook with LLM output available.

        Args:
            phase: Phase name.
            context: Run context.
            llm_output: Output from LLM execution.
            command: Resolved command configuration.

        Raises:
            HookError: If hook execution fails.
        """
        logger.debug("Running post-hook", extra={"phase": phase})

        if not command.has_post_hook:
            logger.debug("No post-hook for phase", extra={"phase": phase})
            return

        # Find hook
        hook_path = find_hook(command.path, "post")
        if hook_path is None:
            return

        # Set LLM output in environment for post-hook
        original_env = os.environ.get("ADW_LLM_OUTPUT")
        # Get artifacts directory for this run/phase
        artifacts_dir = (
            self.artifact_manager.runs_dir / context.run_id / "artifacts" / phase
        )
        try:
            os.environ["ADW_LLM_OUTPUT"] = llm_output

            result = self.hook_runner.run_hook(
                hook_path=hook_path,
                context=context,
                phase=phase,
                hook_type="post",
                artifacts_dir=artifacts_dir,
            )
            logger.debug(
                "Post-hook completed",
                extra={"phase": phase, "stdout_len": len(result.stdout)},
            )

        except HookError:
            logger.error("Post-hook failed", extra={"phase": phase})
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
        llm_result: LLMResult,
    ) -> list[str]:
        """Capture and store phase artifacts.

        Args:
            phase: Phase name.
            context: Run context.
            llm_result: Result from LLM execution.

        Returns:
            List of artifact filenames.
        """
        artifacts: list[str] = []

        # Store LLM output as artifact
        output_name = f"{phase}_output.md"
        self.artifact_manager.store(
            context.run_id,
            phase,
            output_name,
            llm_result.content,
        )
        artifacts.append(output_name)

        # Store tool calls if any
        if llm_result.tool_calls:
            tool_calls_name = f"{phase}_tool_calls.json"
            self.artifact_manager.store_json(
                context.run_id,
                phase,
                tool_calls_name,
                [tc.model_dump() for tc in llm_result.tool_calls],
            )
            artifacts.append(tool_calls_name)

        logger.debug(
            "Artifacts captured", extra={"phase": phase, "count": len(artifacts)}
        )
        return artifacts
