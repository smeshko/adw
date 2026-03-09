"""Phase runner for single phase execution.

This module provides the PhaseRunner class that coordinates all aspects
of executing a single phase: pre-hook → prompt loading → LLM execution →
post-hook → artifact capture.
"""

import json
import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import ValidationError

from adw.commands.loader import get_config_class
from adw.commands.template import (
    build_task_context,
    validate_artifact_references,
)
from adw.core.constants import PHASE_SEQUENCE
from adw.core.extensions import ExtensionRegistry
from adw.exceptions import ADWError, ConfigError, HookError, LLMError
from adw.hooks.git_commit import create_commit, stage_changes

# Note: git_diff imports removed - BuildExtension now handles diff capture
from adw.models import (
    LLMResult,
    PhaseResult,
    PhaseStatus,
    ResolvedCommand,
    RunContext,
)
from adw.models.command import (
    CommandConfig,
    DocumentCommandConfig,
    PhaseLLMConfig,
    ShipCommandConfig,
    ValidateCommandConfig,
)
from adw.models.config import GitConfig, PhaseConfig, ProjectConfig

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
        *,
        progress_display: "ProgressDisplay | None" = None,
        project_config: ProjectConfig | None = None,
        extension_registry: ExtensionRegistry | None = None,
        git_config: GitConfig | None = None,
    ) -> None:
        """Initialize the PhaseRunner.

        Args:
            command_resolver: Resolves phase commands from config.
            template_engine: Renders prompt templates.
            hook_runner: Executes pre/post hooks.
            executor: LLM executor (Claude Code or Mock).
            artifact_manager: Stores phase artifacts.
            progress_display: Display for LLM progress (optional, Story 5.5).
            project_config: Project configuration containing phase-specific
                settings like input_files. Optional for backward compatibility.
            extension_registry: Registry for phase extensions. If None, creates
                an empty registry (no extensions). (Phase Extensions)
            git_config: Git configuration for skip_hooks, branch_prefix, etc.
                Optional for backward compatibility.
        """
        self.command_resolver = command_resolver
        self.template_engine = template_engine
        self.hook_runner = hook_runner
        self.executor = executor
        self.artifact_manager = artifact_manager
        self.progress_display = progress_display
        self.project_config = project_config
        self.extension_registry = extension_registry or ExtensionRegistry()
        self.git_config = git_config

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
        # Phase start already shown in progress panel - no duplicate log needed

        # Resolve command once for all steps
        command = self.command_resolver.resolve(phase)

        # Load and merge configs for this phase (ISS-029)
        merged_config = self._get_merged_config(phase, command)

        try:
            # Compute artifacts_dir for pre-hook file-based variable passing
            artifacts_dir = (
                self.artifact_manager.runs_dir / context.run_id / "artifacts" / phase
            )
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            # Step 1: Run pre-hook (with artifacts_dir for file-based variable passing)
            pre_hook_output = self._run_pre_hook(
                phase, context, command, artifacts_dir=artifacts_dir
            )

            # Step 2: Load and render prompt
            rendered_prompt = self._load_and_render_prompt(
                phase,
                context,
                pre_hook_output,
                command,
                merged_config=merged_config,
                artifacts_override=artifacts_override,
                artifacts_dir=artifacts_dir,
            )

            # Step 3: Execute LLM
            llm_result = self._execute_llm(
                phase,
                context,
                rendered_prompt,
                model=merged_config.llm.model if merged_config.llm else None,
            )

            # Step 4: Capture artifacts
            model = merged_config.llm.model if merged_config.llm else None
            artifacts = self._capture_artifacts(
                phase,
                context,
                llm_result,
                model=model,
            )

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
                input_tokens=llm_result.input_tokens,
                output_tokens=llm_result.output_tokens,
                cache_creation_input_tokens=llm_result.cache_creation_input_tokens,
                cache_read_input_tokens=llm_result.cache_read_input_tokens,
                total_cost_usd=llm_result.total_cost_usd,
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
        self,
        phase: str,
        context: RunContext,
        command: ResolvedCommand,
        *,
        artifacts_dir: Path | None = None,
    ) -> str:
        """Execute pre-hook and capture stdout.

        Args:
            phase: Phase name.
            context: Run context.
            command: Resolved command configuration.
            artifacts_dir: Artifacts directory for file-based variable passing.

        Returns:
            Pre-hook stdout (empty string if no hook).

        Raises:
            HookError: If hook execution fails.
        """
        logger.debug("Running pre-hook", extra={"phase": phase})

        if not command.pre_hook_paths:
            logger.debug("No pre-hook for phase", extra={"phase": phase})
            return ""

        all_stdout = []
        for hook_path in command.pre_hook_paths:
            try:
                result = self.hook_runner.run_hook(
                    hook_path=hook_path,
                    context=context,
                    phase=phase,
                    hook_type="pre",
                    artifacts_dir=artifacts_dir,
                    working_dir=context.worktree_path,
                )
                logger.debug(
                    "Pre-hook completed",
                    extra={"phase": phase, "hook": str(hook_path), "stdout_len": len(result.stdout)},
                )
                all_stdout.append(result.stdout)
            except HookError:
                logger.error("Pre-hook failed", extra={"phase": phase, "hook": str(hook_path)})
                raise

        return "\n".join(all_stdout)

    def _load_and_render_prompt(
        self,
        phase: str,
        context: RunContext,
        pre_hook_output: str,
        command: ResolvedCommand,
        *,
        merged_config: PhaseConfig | None = None,
        artifacts_override: dict[str, dict[str, str]] | None = None,
        artifacts_dir: Path | None = None,
    ) -> str:
        """Load prompt template and render with variables.

        Includes artifact content from previous phases for template access.
        Validates artifact references before rendering.

        Template Artifact Access:
            - {{artifacts.phase.name}} - Access specific artifact content
            - {{artifacts.phase.*}} - List all artifacts in a phase
            - {{artifacts.*}} - List all phases with artifacts

        Args:
            phase: Phase name.
            context: Run context.
            pre_hook_output: Output from pre-hook.
            command: Resolved command configuration.
            merged_config: Pre-merged configuration from _get_merged_config.
                If None, falls back to empty PhaseConfig (backward compatibility).
            artifacts_override: Pre-loaded artifacts to use instead of loading
                from the current run. Used for single-phase execution.
            artifacts_dir: Artifacts directory for reading pre-hook variables.

        Returns:
            Rendered prompt string.

        Raises:
            CommandError: If resolution or rendering fails.
            ConfigError: If strict mode enabled and artifact not found.
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

        # Validate artifact references in template (ISS-017)
        # Lenient mode - missing refs replaced with empty
        validate_artifact_references(
            prompt_template,
            artifacts_map,
            strict=False,
            template_path=str(prompt_path),
        )

        # ISS-029: Use pre-merged config if provided, else create empty
        # Config loading moved to _get_merged_config for timeout access in run()
        effective_config = merged_config if merged_config is not None else PhaseConfig()

        # Load input files from merged config (ISS-015 + ISS-016)
        input_files_map: dict[str, str] = {}
        if effective_config.input_files:
            # Determine project root for file resolution
            project_root = context.worktree_path or Path.cwd()
            input_files_map = self._load_input_files(
                effective_config.input_files,
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
            # Project configuration for templates
            "project_config": (
                self.project_config.model_dump() if self.project_config else {}
            ),
        }

        # Load pre-hook variables from file (if pre-hook wrote them)
        if artifacts_dir:
            pre_hook_vars_file = artifacts_dir / "pre_hook_vars.json"
            if pre_hook_vars_file.exists():
                try:
                    pre_hook_vars = json.loads(
                        pre_hook_vars_file.read_text(encoding="utf-8")
                    )
                    variables.update(pre_hook_vars)
                except (json.JSONDecodeError, OSError):
                    pass  # Graceful fallback - pre-hook vars are informational

        # Load phase-specific typed config for templates (ISS-031)
        # This provides {{ship_config.*}} access
        typed_config = self._load_project_config(phase)

        # Build ship_config — filter to relevant fields and render as YAML string
        if isinstance(typed_config, ShipCommandConfig):
            ship_dict: dict = {
                "commands": typed_config.commands.model_dump(exclude_none=True),
                "bypass_ci": typed_config.bypass_ci,
            }
            if self.project_config and self.project_config.build_command:
                ship_dict["commands"]["build"] = self.project_config.build_command
            variables["ship_config"] = yaml.dump(
                ship_dict, default_flow_style=False
            )
        else:
            variables["ship_config"] = ""

        # Inject flat template variables expected by ship instructions.xml
        # Always set regardless of truthiness so Jinja `default` filter works
        # (Jinja treats None as undefined, triggering the default)
        if isinstance(typed_config, ShipCommandConfig):
            variables["version_bump_command"] = typed_config.commands.version_bump
            variables["publish_command"] = typed_config.commands.publish
        # build_command and test_command as flat variables for template access
        variables["build_command"] = (
            self.project_config.build_command if self.project_config else None
        )
        variables["test_command"] = (
            self.project_config.test_command if self.project_config else None
        )
        variables["lint_command"] = (
            typed_config.lint_command
            if isinstance(typed_config, ValidateCommandConfig)
            else None
        )

        variables["doc_mappings"] = (
            [m.model_dump() for m in typed_config.doc_mappings]
            if isinstance(typed_config, DocumentCommandConfig)
            and typed_config.doc_mappings
            else []
        )

        # Load schema from command directory if exists (for validate phase)
        schema_path = command.path / "schema.json"
        if schema_path.exists():
            variables["schema"] = schema_path.read_text(encoding="utf-8")
        else:
            variables["schema"] = ""  # Empty string if no schema defined

        # ISS-017: Pass command_root and shared_root as params, not state
        # Render template in lenient mode - allow missing refs to pass through
        rendered = self.template_engine.render(
            prompt_template,
            variables,
            strict=False,
            command_root=command.path,
            shared_root=command.path.parent,
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
    ) -> PhaseConfig:
        """Convert command config to PhaseConfig.

        Extracts settings from command's config.yaml and returns a PhaseConfig.
        Phase configuration is now delegated entirely to command configs (ISS-029).

        Args:
            command_config: Configuration from command's config.yaml.
                May be None if no config.yaml exists.

        Returns:
            PhaseConfig with command settings.
            Returns empty PhaseConfig if command_config is None.

        Example:
            >>> command_config = CommandConfig(
            ...     input_files={"prd": "defaults/prd.md"},
            ... )
            >>> merged = runner._merge_configs(command_config)
        """
        # Start with empty config
        merged_data: dict[str, Any] = {}

        # Apply command settings (if any)
        if command_config:
            if command_config.input_files is not None:
                merged_data["input_files"] = dict(command_config.input_files)
            if command_config.llm is not None:
                merged_data["llm"] = command_config.llm

        # Return PhaseConfig
        return PhaseConfig(**merged_data) if merged_data else PhaseConfig()

    def _merge_configs_with_project(
        self,
        command_config: CommandConfig | None,
        project_config: CommandConfig | None,
    ) -> PhaseConfig:
        """Merge command config with project config overlay (ISS-030).

        Project config values override command config values when set.
        This enables projects to customize phase settings without duplicating
        the command prompt.

        Merge strategy:
        - Start with command config values
        - Override with project config values (when explicitly set)
        - For dict fields (input_files), merge with project values taking precedence

        Args:
            command_config: Configuration from the resolved command's config.yaml.
            project_config: Configuration from project's
                .adw/commands/{phase}/config.yaml.

        Returns:
            PhaseConfig with merged settings.

        Example:
            >>> # Command config: enabled=True
            >>> # Project config: enabled=False
            >>> # Result: enabled=False (project overrides)
        """
        merged_data: dict[str, Any] = {}

        # Start with command config values
        if command_config:
            if command_config.input_files is not None:
                merged_data["input_files"] = dict(command_config.input_files)
            if command_config.llm is not None:
                merged_data["llm"] = command_config.llm

        # Override with project config values (when set)
        if project_config:
            # Merge input_files dicts: project values override command values
            if project_config.input_files is not None:
                existing_inputs = merged_data.get("input_files", {})
                merged_data["input_files"] = {
                    **existing_inputs,
                    **project_config.input_files,
                }

            # Merge LLM config: project fields override command fields
            if project_config.llm is not None:
                existing_llm = merged_data.get("llm")
                if existing_llm is not None:
                    # Merge: project values override command values
                    existing_dict = existing_llm.model_dump(exclude_none=True)
                    project_dict = project_config.llm.model_dump(exclude_none=True)
                    merged_data["llm"] = PhaseLLMConfig(
                        **{**existing_dict, **project_dict}
                    )
                else:
                    merged_data["llm"] = project_config.llm

        return PhaseConfig(**merged_data) if merged_data else PhaseConfig()

    def _load_command_config(
        self, command: ResolvedCommand, phase: str
    ) -> CommandConfig | None:
        """Load optional config.yaml from command directory.

        Uses the phase-specific config class (e.g., ValidateCommandConfig for
        validate phase) to load and validate the configuration.

        Args:
            command: The resolved command with path information.
            phase: The phase name for selecting the appropriate config class.

        Returns:
            Parsed CommandConfig (or subclass) if config.yaml exists, None otherwise.

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

            # Use phase-specific config class
            config_class = get_config_class(phase)
            return config_class.model_validate(data)
        except yaml.YAMLError as e:
            raise ConfigError(
                code="INVALID_CONFIG",
                message=f"Invalid YAML in config.yaml at {config_path}: {e}",
            ) from e
        except ValidationError as e:
            # Catch Pydantic validation errors and re-raise as ConfigError
            raise ConfigError(
                code="INVALID_CONFIG",
                message=f"Invalid config in config.yaml at {config_path}: {e}",
            ) from e

    def _load_project_config(self, phase: str) -> CommandConfig | None:
        """Load project-level config.yaml for a phase (ISS-030).

        This method loads config.yaml from the project's .adw/commands/{phase}/
        directory, bypassing the command resolver. This enables project-level
        configuration overrides even when no prompt.md exists in the project.

        The project config is loaded separately from command resolution to support
        cases where only config.yaml exists in the project directory (no prompt.md).

        Uses the phase-specific config class (e.g., ValidateCommandConfig for
        validate phase) to load and validate the configuration.

        Args:
            phase: Phase name (e.g., "plan", "build", "ship").

        Returns:
            Parsed CommandConfig (or subclass) if project config.yaml exists,
            None otherwise.

        Raises:
            ConfigError: If config.yaml exists but contains invalid YAML or
                        fails Pydantic validation.

        Example:
            >>> project_config = runner._load_project_config("ship")
            >>> if project_config and not project_config.enabled:
            ...     print("Ship phase disabled at project level")
        """
        # Use command resolver's project root to ensure consistent config resolution
        # regardless of current working directory (fixes issue when invoked from
        # different cwd or during worktree runs)
        project_root = self.command_resolver.project_root

        config_path = project_root / ".adw" / "commands" / phase / "config.yaml"

        if not config_path.exists():
            return None

        logger.debug(
            "Loading project config",
            extra={"phase": phase, "config_path": str(config_path)},
        )

        try:
            config_content = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(config_content)

            # Handle empty config file
            if data is None:
                data = {}

            # Use phase-specific config class
            config_class = get_config_class(phase)
            return config_class.model_validate(data)
        except yaml.YAMLError as e:
            raise ConfigError(
                code="INVALID_PROJECT_CONFIG",
                message=f"Invalid YAML in project config at {config_path}: {e}",
                suggestion="Check the YAML syntax in your project's config.yaml file.",
            ) from e
        except ValidationError as e:
            # Provide helpful suggestions for common config errors
            suggestion = "Ensure your config.yaml follows the CommandConfig schema."

            # Check for doc_mappings errors (common misconfiguration)
            error_str = str(e)
            if "doc_mappings" in error_str or (
                phase == "document" and "source_pattern" in error_str
            ):
                suggestion = (
                    "doc_mappings must be a list of objects with 'source_pattern' "
                    "and 'docs_dir' fields. Example:\n"
                    "  doc_mappings:\n"
                    "    - source_pattern: 'src/**/*.py'\n"
                    "      docs_dir: 'docs/api'"
                )

            raise ConfigError(
                code="INVALID_PROJECT_CONFIG",
                message=f"Invalid config in project config at {config_path}: {e}",
                suggestion=suggestion,
            ) from e

    def _get_merged_config(self, phase: str, command: ResolvedCommand) -> PhaseConfig:
        """Get configuration for a phase by merging command and project configs.

        Loads config from the resolved command's config.yaml and also checks
        for project-level config.yaml in .adw/commands/{phase}/. Project config
        values override command config values (ISS-030).

        Config resolution order (later overrides earlier):
        1. Command config (from resolved command tier: bundled/user)
        2. Project config (from .adw/commands/{phase}/config.yaml)

        This enables projects to customize phase settings (timeout, enabled,
        input_files) without duplicating the entire command prompt.

        Args:
            phase: Phase name (e.g., "plan", "build", "ship").
            command: Resolved command with path information.

        Returns:
            PhaseConfig with merged settings from command and project configs.
        """
        # Load command config from resolved tier (if exists)
        command_config = (
            self._load_command_config(command, phase) if command.has_config else None
        )

        # ISS-030: Load project-level config (separate from command resolution)
        project_config = self._load_project_config(phase)

        # Merge configs: project overrides command
        return self._merge_configs_with_project(command_config, project_config)

    def is_phase_enabled(self, phase: str) -> bool:
        """Check if a phase is enabled in command and project configs (ISS-030).

        Resolves the command for the phase and checks the `enabled` field
        in both the command's config.yaml and the project's config.yaml.
        Project config takes precedence over command config.

        Config resolution order (later overrides earlier):
        1. Command config `enabled` (from resolved tier)
        2. Project config `enabled` (from .adw/commands/{phase}/config.yaml)

        If neither config exists or `enabled` is not set, defaults to True.

        Args:
            phase: Phase name to check.

        Returns:
            True if the phase is enabled (default), False if disabled by
            either command or project config.
        """
        try:
            # Start with default enabled
            enabled = True

            # Check command config (from resolved tier)
            command = self.command_resolver.resolve(phase)
            if command.has_config:
                config = self._load_command_config(command, phase)
                if config is not None:
                    enabled = config.enabled

            # ISS-030: Check project config (overrides command config)
            # Only override enabled if the project config EXPLICITLY sets it
            # (not just using Pydantic's default=True)
            project_config = self._load_project_config(phase)
            if (
                project_config is not None
                and "enabled" in project_config.model_fields_set
            ):
                # Project config explicitly set enabled - use its value
                enabled = project_config.enabled

            return enabled
        except Exception:
            # If command resolution fails, consider phase enabled
            # (actual error will be raised during execution)
            return True

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
        model: str | None = None,
    ) -> LLMResult:
        """Execute LLM with rendered prompt.

        Args:
            phase: Phase name.
            context: Run context.
            prompt: Rendered prompt.
            model: Optional model identifier from phase config.

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
                "model": model,
            },
        )

        # Start LLM progress display (Story 5.5)
        if self.progress_display:
            self.progress_display.on_llm_start()

        try:
            # Pass worktree_path for isolated execution (Story 10.5)
            # Pass model from phase LLM config
            result = self.executor.execute(
                prompt,
                phase=phase,
                cwd=context.worktree_path,
                model=model,
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

        if not command.post_hook_paths:
            logger.debug("No post-hook for phase", extra={"phase": phase})
            return

        # Set LLM output in environment for post-hook
        original_env = os.environ.get("ADW_LLM_OUTPUT")
        # Get artifacts dir for this run/phase (already exists from capture)
        artifacts_dir = (
            self.artifact_manager.runs_dir / context.run_id / "artifacts" / phase
        )

        # Get extension-provided environment variables for this phase
        extension_env = self.extension_registry.get_hook_env(phase, context)
        extension_env_keys: list[str] = []

        try:
            os.environ["ADW_LLM_OUTPUT"] = llm_output

            # Set extension environment variables
            for key, value in extension_env.items():
                os.environ[key] = value
                extension_env_keys.append(key)

            if extension_env_keys:
                logger.debug(
                    "Set extension environment variables for hook",
                    extra={"phase": phase, "vars": extension_env_keys},
                )

            for hook_path in command.post_hook_paths:
                result = self.hook_runner.run_hook(
                    hook_path=hook_path,
                    context=context,
                    phase=phase,
                    hook_type="post",
                    artifacts_dir=artifacts_dir,
                    working_dir=context.worktree_path,
                )
                logger.debug(
                    "Post-hook completed",
                    extra={"phase": phase, "hook": str(hook_path), "stdout_len": len(result.stdout)},
                )

        except HookError as e:
            # Log hook output at ERROR level so it shows at normal verbosity
            if e.stderr:
                logger.error(f"Post-hook stderr: {e.stderr[:1000]}")
            if e.stdout:
                logger.error(f"Post-hook stdout: {e.stdout[:1000]}")

            # Persist hook output as artifact for post-mortem debugging
            if artifacts_dir.exists() and (e.stdout or e.stderr):
                try:
                    hook_debug_path = artifacts_dir / f"{phase}_hook_debug.txt"
                    with open(hook_debug_path, "w", encoding="utf-8") as f:
                        f.write("=== HOOK FAILURE DEBUG ===\n")
                        f.write(f"Phase: {phase}\n")
                        f.write(f"Exit code: {e.exit_code}\n")
                        f.write(f"Duration: {e.duration_ms}ms\n\n")
                        f.write(f"=== STDOUT ===\n{e.stdout or '(empty)'}\n\n")
                        f.write(f"=== STDERR ===\n{e.stderr or '(empty)'}\n")
                    logger.debug(f"Hook debug output saved to: {hook_debug_path}")
                except OSError as write_err:
                    logger.warning(f"Failed to save hook debug output: {write_err}")

            logger.error("Post-hook failed", extra={"phase": phase})
            raise
        finally:
            # Restore original env value
            if original_env is None:
                os.environ.pop("ADW_LLM_OUTPUT", None)
            else:
                os.environ["ADW_LLM_OUTPUT"] = original_env

            # Clean up extension environment variables
            for key in extension_env_keys:
                os.environ.pop(key, None)

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

        Raises:
            HookError: If branch validation fails (GIT_BRANCH_MISMATCH).
                ISS-025: Branch mismatch is fatal to prevent commits to wrong branch.

        Note:
            Most git errors are logged but do not raise exceptions.
            However, branch validation failures (ISS-025) are fatal.
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
            # ISS-025: Pass branch_name for validation before commit
            sha = create_commit(
                phase=phase,
                feature=context.feature_description,
                run_id=context.run_id,
                skip_hooks=self.git_config.skip_hooks if self.git_config else False,
                working_dir=context.worktree_path,
                expected_branch=context.branch_name,
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
            # ISS-025: Branch mismatch errors are fatal - must not commit to
            # wrong branch
            if e.code == "GIT_BRANCH_MISMATCH":
                logger.error(
                    "Branch validation failed - aborting commit",
                    extra={
                        "phase": phase,
                        "run_id": context.run_id,
                        "error_code": e.code,
                        "error": str(e),
                    },
                )
                raise

            # Other hook errors are best-effort (e.g., pre-commit hook failures)
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
        *,
        model: str | None = None,
    ) -> list[str]:
        """Capture and store phase artifacts.

        Args:
            phase: Phase name.
            context: Run context.
            llm_result: Result from LLM execution.
            model: Optional model identifier for LLM response tracking.

        Returns:
            List of artifact filenames.
        """
        import json

        artifacts: list[str] = []

        # ISS-023: Use final_output (last message only) for artifacts
        # This gives downstream phases clean output without intermediate reasoning
        # Falls back to full content if final_output is empty (backward compat)
        artifact_content = llm_result.final_output or llm_result.content

        # Store LLM output as artifact
        output_name = f"{phase}_output.md"
        self.artifact_manager.store(
            context.run_id,
            phase,
            output_name,
            artifact_content,
        )
        artifacts.append(output_name)

        # Note: Document phase pr_description.md is now handled by DocumentExtension

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

        # Note: Build phase git diff capture is now handled by BuildExtension

        # Store LLM response stats to llm/ directory for token tracking
        # This is used by StatsAggregator for dashboard token display
        try:
            phase_index = PHASE_SEQUENCE.index(phase) + 1
        except ValueError:
            phase_index = 99  # Unknown phase gets high index

        response_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "phase": phase,
            "model": model or "default",
            "stats": {
                "input_tokens": llm_result.input_tokens,
                "cache_creation_input_tokens": llm_result.cache_creation_input_tokens,
                "cache_read_input_tokens": llm_result.cache_read_input_tokens,
                "output_tokens": llm_result.output_tokens,
                "total_cost_usd": llm_result.total_cost_usd,
                "duration_ms": llm_result.duration_ms,
            },
        }

        llm_dir = self.artifact_manager.runs_dir / context.run_id / "llm"
        llm_dir.mkdir(parents=True, exist_ok=True)
        response_file = llm_dir / f"{phase_index:03d}_{phase}_response.json"
        response_file.write_text(json.dumps(response_data, indent=2))

        # Call extension extra_artifacts hooks (Phase Extensions)
        extra_artifacts = self.extension_registry.call_extra_artifacts(
            phase, context, llm_result
        )
        for artifact_name, content in extra_artifacts:
            self.artifact_manager.store(
                context.run_id,
                phase,
                artifact_name,
                content,
            )
            artifacts.append(artifact_name)

        logger.debug(
            "Artifacts captured", extra={"phase": phase, "count": len(artifacts)}
        )
        return artifacts

    # Note: _capture_git_diff_artifacts method removed - now handled by BuildExtension
