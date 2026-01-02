"""Phase runner for single phase execution.

This module provides the PhaseRunner class that coordinates all aspects
of executing a single phase: pre-hook → prompt loading → LLM execution →
post-hook → artifact capture.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from adw.exceptions import ADWError, CommandError, HookError, LLMError
from adw.hooks.runner import find_hook
from adw.models import (
    HookResult,
    LLMResult,
    PhaseResult,
    PhaseStatus,
    RunContext,
)

if TYPE_CHECKING:
    from adw.commands.resolver import CommandResolver
    from adw.commands.template import TemplateEngine
    from adw.core.artifact_manager import ArtifactManager
    from adw.executors.base import LLMExecutor
    from adw.hooks.runner import HookRunner

logger = logging.getLogger(__name__)


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

    Example:
        >>> runner = PhaseRunner(
        ...     command_resolver=resolver,
        ...     template_engine=engine,
        ...     hook_runner=hook_runner,
        ...     executor=executor,
        ...     artifact_manager=artifact_manager,
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
    ) -> None:
        """Initialize the PhaseRunner.

        Args:
            command_resolver: Resolves phase commands from config.
            template_engine: Renders prompt templates.
            hook_runner: Executes pre/post hooks.
            executor: LLM executor (Claude Code or Mock).
            artifact_manager: Stores phase artifacts.
        """
        self.command_resolver = command_resolver
        self.template_engine = template_engine
        self.hook_runner = hook_runner
        self.executor = executor
        self.artifact_manager = artifact_manager

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
            self._run_post_hook(phase, context, llm_result.content)

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
            PhaseResult(
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
                },
            )

            # Re-raise with phase context if applicable
            if hasattr(e, "phase") and e.phase is None:
                e.phase = phase
            raise

    def _run_pre_hook(self, phase: str, context: RunContext) -> str:
        """Execute pre-hook and capture stdout.

        Args:
            phase: Phase name.
            context: Run context.

        Returns:
            Pre-hook stdout (empty string if no hook).

        Raises:
            HookError: If hook execution fails.
        """
        logger.debug("Running pre-hook", extra={"phase": phase})

        # Resolve command to find hook path
        command = self.command_resolver.resolve(phase)

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
    ) -> str:
        """Load prompt template and render with variables.

        Args:
            phase: Phase name.
            context: Run context.
            pre_hook_output: Output from pre-hook.

        Returns:
            Rendered prompt string.

        Raises:
            CommandError: If resolution or rendering fails.
        """
        logger.debug("Loading prompt", extra={"phase": phase})

        # Resolve command config
        command = self.command_resolver.resolve(phase)

        # Read the prompt template
        prompt_path = command.path / "prompt.md"
        prompt_template = prompt_path.read_text(encoding="utf-8")

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
        rendered = self.template_engine.render(prompt_template, variables)

        logger.debug(
            "Prompt rendered", extra={"phase": phase, "prompt_len": len(rendered)}
        )
        return rendered

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
            return result

        except LLMError:
            logger.error("LLM execution failed", extra={"phase": phase})
            raise

    def _run_post_hook(
        self,
        phase: str,
        context: RunContext,
        llm_output: str,
    ) -> None:
        """Execute post-hook with LLM output available.

        Args:
            phase: Phase name.
            context: Run context.
            llm_output: Output from LLM execution.

        Raises:
            HookError: If hook execution fails.
        """
        logger.debug("Running post-hook", extra={"phase": phase})

        # Resolve command to find hook path
        command = self.command_resolver.resolve(phase)

        if not command.has_post_hook:
            logger.debug("No post-hook for phase", extra={"phase": phase})
            return

        # Find hook
        hook_path = find_hook(command.path, "post")
        if hook_path is None:
            return

        # Set LLM output in environment for post-hook
        original_env = os.environ.get("ADW_LLM_OUTPUT")
        try:
            os.environ["ADW_LLM_OUTPUT"] = llm_output

            result = self.hook_runner.run_hook(
                hook_path=hook_path,
                context=context,
                phase=phase,
                hook_type="post",
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
