"""Phase runner for single phase execution.

This module provides the PhaseRunner class that coordinates all aspects
of executing a single phase: pre-hook → prompt loading → LLM execution →
post-hook → artifact capture.
"""

import logging
import os
import re
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from adw.core.constants import PHASE_SEQUENCE
from adw.exceptions import ADWError, ConfigError, HookError, LLMError
from adw.hooks.git_commit import create_commit, stage_changes
from adw.models.command import CommandConfig
from adw.models.config import PhaseConfig, ProjectConfig
from adw.hooks.git_diff import (
    capture_diff,
    capture_staged_diff,
    get_diff_stats,
    has_commits,
    truncate_diff,
)
from adw.commands.template import build_task_context
from adw.models import (
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
        project_config: ProjectConfig | None = None,
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
            project_config: Project configuration containing phase-specific
                settings like input_files. Optional for backward compatibility.
        """
        self.command_resolver = command_resolver
        self.template_engine = template_engine
        self.hook_runner = hook_runner
        self.executor = executor
        self.artifact_manager = artifact_manager
        self.strict_artifacts = strict_artifacts
        self.progress_display = progress_display
        self.project_config = project_config

    def run(
        self,
        phase: str,
        context: RunContext,
        *,
        artifacts_override: dict[str, dict[str, str]] | None = None,
    ) -> PhaseResult:
        """Execute a single phase.

        Args:
            phase: Phase name (plan, build, validate, document).
            context: Current run context.
            artifacts_override: Pre-loaded artifacts to use instead of loading
                from the current run. Used for single-phase execution with
                --from-run to load artifacts from a source run.

        Returns:
            PhaseResult with status, timing, and artifacts.

        Raises:
            HookError: If pre/post hook fails.
            CommandError: If command resolution/template fails.
            LLMError: If LLM execution fails.
        """
        started_at = datetime.now(UTC)
        logger.info("Phase starting", extra={"phase": phase, "run_id": context.run_id})

        # Resolve command once for all steps
        command = self.command_resolver.resolve(phase)

        try:
            # Step 1: Run pre-hook
            pre_hook_output = self._run_pre_hook(phase, context, command)

            # Step 2: Load and render prompt
            rendered_prompt = self._load_and_render_prompt(
                phase,
                context,
                pre_hook_output,
                command,
                artifacts_override=artifacts_override,
            )

            # Step 3: Execute LLM
            llm_result = self._execute_llm(phase, context, rendered_prompt)

            # Step 4: Capture artifacts
            artifacts = self._capture_artifacts(phase, context, llm_result)

            # Step 5: Run post-hook (after artifacts exist)
            self._run_post_hook(phase, context, llm_result.content, command)

            # Step 6: Auto-commit changes (after post-hook modifications)
            self._auto_commit_changes(phase, context)

            # Build successful result
            completed_at = datetime.now(UTC)
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
            completed_at = datetime.now(UTC)
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

        if command.pre_hook_path is None:
            logger.debug("No pre-hook for phase", extra={"phase": phase})
            return ""

        try:
            result = self.hook_runner.run_hook(
                hook_path=command.pre_hook_path,
                context=context,
                phase=phase,
                hook_type="pre",
                working_dir=context.worktree_path,
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
        *,
        artifacts_override: dict[str, dict[str, str]] | None = None,
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
            artifacts_override: Pre-loaded artifacts to use instead of loading
                from the current run. Used for single-phase execution.

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

        # Use override if provided, otherwise build from current run (FR11)
        if artifacts_override is not None:
            artifacts_map = artifacts_override
            logger.debug(
                "Using artifacts override",
                extra={"phase": phase, "phases_available": list(artifacts_map.keys())},
            )
        else:
            artifacts_map = self._build_artifacts_map(context.run_id, phase)

        # Validate artifact references in template
        # Raises ConfigError if strict_artifacts=True and artifact missing
        self._validate_artifact_references(prompt_template, artifacts_map)

        # Load and merge configs (ISS-016: per-phase config.yaml)
        # 1. Load command config from config.yaml (if exists)
        command_config = self._load_command_config(command) if command.has_config else None

        # 2. Get project phase config (if exists)
        project_phase_config = None
        if self.project_config and phase in self.project_config.phases:
            project_phase_config = self.project_config.phases[phase]

        # 3. Merge configs (project overrides command defaults)
        merged_config = self._merge_configs(command_config, project_phase_config)

        # Load input files from merged config (ISS-015 + ISS-016)
        input_files_map: dict[str, str] = {}
        if merged_config.input_files:
            # Determine project root for file resolution
            project_root = context.worktree_path or Path.cwd()
            input_files_map = self._load_input_files(
                merged_config.input_files,
                project_root=project_root,
                worktree_path=context.worktree_path,
            )
            logger.debug(
                "Loaded input files from merged config",
                extra={"phase": phase, "inputs": list(input_files_map.keys())},
            )

        # Build template variables
        variables = {
            "context": context,  # Pass the model directly for nested access
            "pre_hook_output": pre_hook_output,
            "artifacts": artifacts_map,  # Nested: {phase: {name: content}}
            "inputs": input_files_map,  # ISS-015: {name: content} from input_files
            "run_id": context.run_id,
            "phase": phase,
            "feature": context.feature_description,
            "feature_description": context.feature_description,  # Alias for templates
            # Story 10.5: worktree path for templates (empty if None)
            "worktree_path": (
                str(context.worktree_path) if context.worktree_path else ""
            ),
            # Story 12.5: task context for templates ({{task.*}} variables)
            "task": build_task_context(context.task_info),
        }

        # Add convenience aliases for common artifact references
        # e.g., {{plan}} instead of {{artifacts.plan.plan_output}}

        if "plan" in artifacts_map and "plan_output" in artifacts_map["plan"]:
            variables["plan"] = artifacts_map["plan"]["plan_output"]
        if "build" in artifacts_map and "build_output" in artifacts_map["build"]:
            variables["implementation"] = artifacts_map["build"]["build_output"]
        if "validate" in artifacts_map and "validate_output" in artifacts_map["validate"]:
            variables["output"] = artifacts_map["validate"]["validate_output"]

        # Load schema from command directory if exists (for validate phase)
        schema_path = command.path / "schema.json"
        if schema_path.exists():
            variables["schema"] = schema_path.read_text(encoding="utf-8")
        else:
            variables["schema"] = ""  # Empty string if no schema defined

        # Set command_root and shared_root for {{include:...}} and {{shared:...}} resolution
        self.template_engine.command_root = command.path
        self.template_engine.shared_root = command.path.parent

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

    def _load_input_files(
        self,
        input_files: dict[str, str] | None,
        project_root: Path,
        worktree_path: Path | None = None,
    ) -> dict[str, str]:
        """Load input files specified in PhaseConfig.input_files.

        Reads files from the project root (or worktree if specified) and
        returns their contents mapped by variable name.

        Args:
            input_files: Mapping of variable names to relative file paths.
                None or empty dict is allowed and returns empty dict.
            project_root: Base path for resolving relative file paths.
            worktree_path: If provided, use this instead of project_root
                for file resolution (for worktree-isolated runs).

        Returns:
            Dict mapping variable names to file contents.

        Raises:
            ConfigError: If a specified file does not exist.

        Example:
            >>> files = runner._load_input_files(
            ...     {"prd": "docs/prd.md"},
            ...     project_root=Path("/project"),
            ... )
            >>> files["prd"]
            '# Product Requirements...'
        """
        if not input_files:
            return {}

        # Determine base path for resolution
        base_path = worktree_path if worktree_path else project_root

        loaded: dict[str, str] = {}
        for name, relative_path in input_files.items():
            file_path = base_path / relative_path

            if not file_path.exists():
                raise ConfigError(
                    code="INPUT_FILE_NOT_FOUND",
                    message=f"Input file not found: {relative_path}",
                    suggestion=(
                        f"Ensure the file '{relative_path}' exists relative to "
                        f"'{base_path}'. Check the path in your phase configuration."
                    ),
                )

            try:
                content = file_path.read_text(encoding="utf-8")
                loaded[name] = content
                logger.debug(
                    "Loaded input file",
                    extra={
                        "input_name": name,
                        "input_path": str(file_path),
                        "input_size": len(content),
                    },
                )
            except UnicodeDecodeError as e:
                raise ConfigError(
                    code="INPUT_FILE_ENCODING_ERROR",
                    message=f"Failed to decode input file '{relative_path}': {e}",
                    suggestion="Ensure the file is UTF-8 encoded.",
                ) from e

        return loaded

    def _merge_configs(
        self,
        command_config: CommandConfig | None,
        project_phase_config: PhaseConfig | None,
    ) -> PhaseConfig:
        """Merge command config with project phase config.

        Combines defaults from command's config.yaml with project-level
        PhaseConfig from adw.yaml. Project settings take precedence
        (override command defaults).

        Args:
            command_config: Configuration from command's config.yaml.
                May be None if no config.yaml exists.
            project_phase_config: Phase configuration from project's adw.yaml.
                May be None if phase not configured in project.

        Returns:
            Merged PhaseConfig with combined settings.
            Returns empty PhaseConfig if both inputs are None.

        Merge Rules:
            - Scalar values (timeout_seconds, pre_hook, post_hook): project wins
            - input_files: merged dict, project values override command values
            - llm settings: project values override command values

        Example:
            >>> command_config = CommandConfig(
            ...     timeout_seconds=600,
            ...     input_files={"prd": "defaults/prd.md"},
            ... )
            >>> project_config = PhaseConfig(
            ...     input_files={"prd": "docs/prd.md", "arch": "docs/arch.md"},
            ... )
            >>> merged = runner._merge_configs(command_config, project_config)
            >>> merged.timeout_seconds  # From command (project didn't override)
            600
            >>> merged.input_files["prd"]  # Project overrides command
            'docs/prd.md'
        """
        # Start with empty config
        merged_data: dict = {}

        # First, apply command defaults (if any)
        if command_config:
            if command_config.timeout_seconds is not None:
                merged_data["timeout_seconds"] = command_config.timeout_seconds
            if command_config.input_files is not None:
                merged_data["input_files"] = dict(command_config.input_files)
            if command_config.pre_hook is not None:
                merged_data["pre_hook"] = command_config.pre_hook
            if command_config.post_hook is not None:
                merged_data["post_hook"] = command_config.post_hook
            # Note: llm settings from command config would go here when supported

        # Then, apply project settings (override command defaults)
        if project_phase_config:
            if project_phase_config.timeout_seconds is not None:
                merged_data["timeout_seconds"] = project_phase_config.timeout_seconds
            if project_phase_config.input_files is not None:
                # Merge input_files: project values override command values
                if "input_files" not in merged_data:
                    merged_data["input_files"] = {}
                merged_data["input_files"].update(project_phase_config.input_files)
            if project_phase_config.pre_hook is not None:
                merged_data["pre_hook"] = project_phase_config.pre_hook
            if project_phase_config.post_hook is not None:
                merged_data["post_hook"] = project_phase_config.post_hook

        # Return merged PhaseConfig
        return PhaseConfig(**merged_data) if merged_data else PhaseConfig()

    def _load_command_config(self, command: ResolvedCommand) -> CommandConfig | None:
        """Load optional config.yaml from command directory.

        Args:
            command: The resolved command with path information.

        Returns:
            Parsed CommandConfig if config.yaml exists, None otherwise.

        Raises:
            ConfigError: If config.yaml exists but contains invalid YAML or
                        fails Pydantic validation.
        """
        config_path = command.path / "config.yaml"

        if not config_path.exists():
            return None

        try:
            config_content = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(config_content)

            # Handle empty config file
            if data is None:
                data = {}

            return CommandConfig.model_validate(data)
        except yaml.YAMLError as e:
            raise ConfigError(
                code="INVALID_CONFIG",
                message=f"Invalid YAML in config.yaml at {config_path}: {e}",
            ) from e
        except Exception as e:
            # Catch Pydantic validation errors and re-raise as ConfigError
            if "ValidationError" in type(e).__name__:
                raise ConfigError(
                    code="INVALID_CONFIG",
                    message=f"Invalid config in config.yaml at {config_path}: {e}",
                ) from e
            raise

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
                # Single part like "plan" - accesses phase dict, not artifact
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
            if content and isinstance(content, str):
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
        logger.debug(
            "Executing LLM",
            extra={
                "phase": phase,
                "worktree_path": (
                    str(context.worktree_path) if context.worktree_path else None
                ),
            },
        )

        # Start LLM progress display (Story 5.5)
        if self.progress_display:
            self.progress_display.on_llm_start()

        try:
            # Pass worktree_path for isolated execution (Story 10.5)
            result = self.executor.execute(
                prompt, phase=phase, cwd=context.worktree_path
            )

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

        if command.post_hook_path is None:
            logger.debug("No post-hook for phase", extra={"phase": phase})
            return

        # Set LLM output in environment for post-hook
        original_env = os.environ.get("ADW_LLM_OUTPUT")
        # Get artifacts directory for this run/phase (already exists from artifact capture)
        artifacts_dir = (
            self.artifact_manager.runs_dir / context.run_id / "artifacts" / phase
        )
        try:
            os.environ["ADW_LLM_OUTPUT"] = llm_output

            result = self.hook_runner.run_hook(
                hook_path=command.post_hook_path,
                context=context,
                phase=phase,
                hook_type="post",
                artifacts_dir=artifacts_dir,
                working_dir=context.worktree_path,
            )
            logger.debug(
                "Post-hook completed",
                extra={"phase": phase, "stdout_len": len(result.stdout)},
            )

        except HookError as e:
            # Log hook output for debugging
            if e.stderr:
                logger.error(f"Post-hook stderr: {e.stderr[:1000]}")
            if e.stdout:
                logger.debug(f"Post-hook stdout: {e.stdout[:1000]}")
            logger.error("Post-hook failed", extra={"phase": phase})
            raise
        finally:
            # Restore original env value
            if original_env is None:
                os.environ.pop("ADW_LLM_OUTPUT", None)
            else:
                os.environ["ADW_LLM_OUTPUT"] = original_env

    def _auto_commit_changes(
        self,
        phase: str,
        context: RunContext,
    ) -> str | None:
        """Automatically stage and commit changes after phase execution.

        Stages all changes (including untracked files) and creates a commit
        with a descriptive message. This ensures git diff capture can work
        properly by having a commit to diff against.

        The commit is created in the worktree context if applicable.

        Args:
            phase: Current phase name (e.g., "build", "validate").
            context: Run context with run_id and feature_description.

        Returns:
            Commit SHA if commit was created, None if no changes to commit.

        Note:
            This method logs errors but does not raise exceptions to avoid
            failing the phase due to git issues. Commits are best-effort.
        """
        logger.debug("Auto-committing changes", extra={"phase": phase})

        try:
            # Stage all changes including untracked files
            # Use worktree path for worktree-isolated runs
            staged_files = stage_changes(working_dir=context.worktree_path)

            if not staged_files:
                logger.debug(
                    "No changes to commit",
                    extra={"phase": phase, "run_id": context.run_id},
                )
                return None

            logger.info(
                "Staged changes",
                extra={
                    "phase": phase,
                    "run_id": context.run_id,
                    "file_count": len(staged_files),
                    "files": staged_files[:10],  # Log first 10 files
                },
            )

            # Create commit with descriptive message
            # Use worktree path for worktree-isolated runs
            sha = create_commit(
                phase=phase,
                feature=context.feature_description,
                run_id=context.run_id,
                working_dir=context.worktree_path,
            )

            if sha:
                logger.info(
                    "Committed changes",
                    extra={
                        "phase": phase,
                        "run_id": context.run_id,
                        "sha": sha,
                        "file_count": len(staged_files),
                    },
                )

            return sha

        except HookError as e:
            # Log but don't fail - commits are best-effort
            logger.warning(
                "Failed to auto-commit changes",
                extra={
                    "phase": phase,
                    "run_id": context.run_id,
                    "error_code": e.code,
                    "error": str(e),
                },
            )
            return None

        except Exception as e:
            # Catch-all for unexpected errors
            logger.warning(
                "Unexpected error during auto-commit",
                extra={
                    "phase": phase,
                    "run_id": context.run_id,
                    "error": str(e),
                },
            )
            return None

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

        # Document phase: also save as pr_description.md (Story 9.4)
        if phase == "document":
            pr_desc_name = "pr_description.md"
            self.artifact_manager.store(
                context.run_id,
                phase,
                pr_desc_name,
                llm_result.content,
            )
            artifacts.append(pr_desc_name)
            logger.info(
                "PR description artifact saved",
                extra={"run_id": context.run_id, "artifact": pr_desc_name},
            )

        # Validate phase: copy evidence manifest to artifacts (Story 9.4, ISS-019)
        if phase == "validate":
            evidence_artifacts = self._capture_evidence_manifest(context)
            artifacts.extend(evidence_artifacts)

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

        # Capture git diff for build phase (Story 9.3)
        if phase == "build":
            diff_artifacts = self._capture_git_diff_artifacts(context)
            artifacts.extend(diff_artifacts)

        logger.debug(
            "Artifacts captured", extra={"phase": phase, "count": len(artifacts)}
        )
        return artifacts

    def _capture_evidence_manifest(
        self,
        context: RunContext,
    ) -> list[str]:
        """Copy evidence manifest to validate artifacts (Story 9.4, ISS-019).

        Makes the evidence manifest available to the document phase template
        via {{artifacts.validate.evidence_manifest}}.

        Args:
            context: Run context.

        Returns:
            List of artifact filenames created (evidence_manifest.json if exists).
        """
        artifacts: list[str] = []

        # Evidence manifest location: .adw/runs/<run_id>/evidence/manifest.json
        evidence_manifest_path = (
            self.artifact_manager.runs_dir
            / context.run_id
            / "evidence"
            / "manifest.json"
        )

        if not evidence_manifest_path.exists():
            logger.debug(
                "No evidence manifest found to copy",
                extra={"run_id": context.run_id, "path": str(evidence_manifest_path)},
            )
            return artifacts

        try:
            manifest_content = evidence_manifest_path.read_text(encoding="utf-8")

            self.artifact_manager.store(
                context.run_id,
                "validate",
                "evidence_manifest.json",
                manifest_content,
            )
            artifacts.append("evidence_manifest.json")

            logger.info(
                "Evidence manifest copied to validate artifacts",
                extra={"run_id": context.run_id},
            )
        except OSError as e:
            logger.warning(
                "Failed to copy evidence manifest",
                extra={"run_id": context.run_id, "error": str(e)},
            )

        return artifacts

    def _capture_git_diff_artifacts(
        self,
        context: RunContext,
    ) -> list[str]:
        """Capture git diff as build phase artifact (Story 9.3).

        Captures the git diff since the last commit and stores it as an artifact.
        If no commits were made during build, captures staged changes instead.
        Large diffs (>100KB) are truncated with a summary.
        Handles initial commit edge case where HEAD~1 doesn't exist.

        Args:
            context: Run context.

        Returns:
            List of artifact filenames created (diff.txt, diff_stats.json).
        """
        artifacts: list[str] = []
        diff_reference = "HEAD~1"

        try:
            # Check if repository has commits (handles initial commit edge case)
            # Pass worktree_path to git operations (Story 10.5)
            if not has_commits(working_dir=context.worktree_path):
                logger.debug(
                    "No commits in repository, trying staged changes",
                    extra={"run_id": context.run_id},
                )
                diff_content = capture_staged_diff(working_dir=context.worktree_path)
                diff_reference = "--cached"
            else:
                # Try to capture diff since last commit
                diff_content = capture_diff(
                    since="HEAD~1", working_dir=context.worktree_path
                )

                # If no diff found, try staged changes
                if not diff_content.strip():
                    logger.debug(
                        "No commit diff found, trying staged changes",
                        extra={"run_id": context.run_id},
                    )
                    diff_content = capture_staged_diff(
                        working_dir=context.worktree_path
                    )
                    diff_reference = "--cached"

            # Handle empty diff case
            if not diff_content.strip():
                logger.debug(
                    "No git changes to capture",
                    extra={"run_id": context.run_id},
                )
                return artifacts

            # Store raw diff content for binary file detection
            raw_diff_content = diff_content

            # Truncate if too large (>100KB)
            original_size = len(diff_content.encode("utf-8"))
            diff_content = truncate_diff(diff_content, max_bytes=102400)

            # Store diff content
            self.artifact_manager.store_text(
                context.run_id,
                "build",
                "diff.txt",
                diff_content,
            )
            artifacts.append("diff.txt")

            # Capture and store diff statistics
            # Run git diff --stat to get stats summary
            try:
                stat_cmd = ["git", "diff", "--stat", "--no-color"]
                if diff_reference == "--cached":
                    stat_cmd.append("--cached")
                else:
                    stat_cmd.append(diff_reference)

                stat_result = subprocess.run(
                    stat_cmd,
                    capture_output=True,
                    text=True,
                    cwd=context.worktree_path if context.worktree_path else None,
                )
                if stat_result.returncode == 0:
                    # Pass raw diff for binary file detection
                    stats = get_diff_stats(stat_result.stdout, raw_diff_content)
                    self.artifact_manager.store_json(
                        context.run_id,
                        "build",
                        "diff_stats.json",
                        stats.model_dump(),
                    )
                    artifacts.append("diff_stats.json")

                    # Count lines in diff (insertions + deletions)
                    lines = stats.insertions + stats.deletions
                    logger.info(
                        "Captured diff",
                        extra={
                            "run_id": context.run_id,
                            "lines": lines,
                            "original_bytes": original_size,
                            "files_changed": stats.files_changed,
                            "insertions": stats.insertions,
                            "deletions": stats.deletions,
                            "binary_files": stats.binary_files,
                        },
                    )
            except Exception as stat_error:
                # Stats are optional - log and continue
                logger.debug(
                    "Could not capture diff stats",
                    extra={"error": str(stat_error)},
                )

        except HookError as e:
            # Git diff errors are non-fatal - log and continue
            logger.warning(
                "Could not capture git diff",
                extra={
                    "run_id": context.run_id,
                    "error_code": e.code,
                    "error": str(e),
                },
            )

        return artifacts
