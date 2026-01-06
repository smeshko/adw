"""Command-related Pydantic models.

This module defines models for command resolution, representation, and configuration.
"""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PhaseLLMConfig(BaseModel):
    """Phase-specific LLM configuration for config.yaml.

    Unlike the global LLMConfig in config.py which configures the executor path
    and timeouts, this model configures LLM behavior for a specific phase command.

    Attributes:
        model: Model identifier to use for this phase (e.g., "claude-3-opus").
        temperature: Sampling temperature (0.0-1.0). Lower values are more deterministic.

    Example:
        >>> llm_config = PhaseLLMConfig(model="claude-3-opus", temperature=0.7)
        >>> llm_config.model
        'claude-3-opus'
    """

    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(
        default=None,
        description="Model identifier to use for this phase",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (0.0-1.0)",
    )


class ArtifactConfig(BaseModel):
    """Configuration for capturing artifacts from a phase.

    Defines rules for capturing files produced by a phase command,
    enabling config-driven artifact capture (unifies with ISS-012).

    Attributes:
        name: Unique identifier for the artifact (used in templates as {{ artifacts.name }}).
        pattern: Glob pattern or path to capture (e.g., "output/*.json", "plan.md").
        required: Whether the artifact must exist after phase completion.
        description: Human-readable description of the artifact purpose.

    Example:
        >>> artifact = ArtifactConfig(
        ...     name="plan",
        ...     pattern="output/plan.md",
        ...     required=True,
        ...     description="Generated implementation plan"
        ... )
        >>> artifact.name
        'plan'

    YAML example in config.yaml:
        artifacts:
          - name: plan
            pattern: output/plan.md
            required: true
            description: Generated implementation plan
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the artifact",
    )
    pattern: str = Field(
        ...,
        min_length=1,
        description="Glob pattern or path to capture",
    )
    required: bool = Field(
        default=False,
        description="Whether the artifact must exist after phase completion",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of the artifact purpose",
    )


class CommandConfig(BaseModel):
    """Phase command configuration loaded from config.yaml.

    Each phase command folder can have an optional config.yaml that defines
    defaults for that command. These defaults are merged with project-level
    PhaseConfig from adw.yaml, where project settings take precedence.

    Attributes:
        timeout_seconds: Default timeout for this command in seconds.
        input_files: Mapping of variable names to file paths for template injection.
            Files are loaded at phase start and available as {{ inputs.name }}.
        llm: Phase-specific LLM settings (model, temperature).
        artifacts: List of artifact capture rules for this phase.
        pre_hook: Default pre-execution shell command.
        post_hook: Default post-execution shell command.

    Example:
        >>> config = CommandConfig(
        ...     timeout_seconds=600,
        ...     input_files={"prd": "docs/prd.md"},
        ...     llm=PhaseLLMConfig(model="claude-3-opus"),
        ... )
        >>> config.timeout_seconds
        600

    YAML example (in command folder's config.yaml):
        timeout_seconds: 600
        input_files:
          prd: docs/prd.md
          architecture: docs/architecture.md
        llm:
          model: claude-3-opus
          temperature: 0.7
        artifacts:
          - name: plan
            pattern: output/plan.md
            required: true
        pre_hook: echo "Starting plan phase"
        post_hook: echo "Plan phase complete"

    Merging behavior:
        When merged with project's PhaseConfig, project settings override command
        defaults. For dictionaries (input_files), values are merged with project
        values taking precedence for duplicate keys.
    """

    model_config = ConfigDict(extra="forbid")

    timeout_seconds: int | None = Field(
        default=None,
        gt=0,
        description="Default timeout for this command in seconds",
    )
    input_files: dict[str, str] | None = Field(
        default=None,
        description="Mapping of variable names to file paths for template injection",
    )
    llm: PhaseLLMConfig | None = Field(
        default=None,
        description="Phase-specific LLM settings",
    )
    artifacts: list[ArtifactConfig] | None = Field(
        default=None,
        description="List of artifact capture rules for this phase",
    )
    pre_hook: str | None = Field(
        default=None,
        description="Default pre-execution shell command",
    )
    post_hook: str | None = Field(
        default=None,
        description="Default post-execution shell command",
    )

    @model_validator(mode="after")
    def validate_artifact_names_unique(self) -> "CommandConfig":
        """Validate that artifact names are unique within the configuration.

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If duplicate artifact names are found.
        """
        if self.artifacts is None:
            return self

        names = [artifact.name for artifact in self.artifacts]
        duplicates = [name for name in names if names.count(name) > 1]

        if duplicates:
            unique_duplicates = sorted(set(duplicates))
            raise ValueError(
                f"Duplicate artifact names found: {', '.join(unique_duplicates)}"
            )

        return self


class ResolvedCommand(BaseModel):
    """A resolved command from the three-tier hierarchy.

    Represents a command that has been located in one of:
    - Project level: .adw/commands/{name}/
    - User level: ~/.adw/commands/{name}/
    - Bundled level: Package defaults

    Attributes:
        name: The command name (e.g., "plan", "build").
        path: The resolved directory path containing command files.
        tier: Which tier the command was resolved from.
        has_schema: Whether schema.json exists in the command directory.
        has_pre_hook: Whether pre.sh or pre-hook.sh exists.
        has_post_hook: Whether post.sh or post-hook.sh exists.
        has_config: Whether config.yaml exists in the command directory.

    Example:
        >>> cmd = ResolvedCommand(
        ...     name="plan",
        ...     path=Path(".adw/commands/plan"),
        ...     tier="project",
        ...     has_schema=True,
        ... )
        >>> print(cmd.tier)
        "project"
    """

    model_config = ConfigDict(frozen=True)

    name: str
    path: Path
    tier: Literal["project", "user", "bundled"]
    has_schema: bool = False
    has_pre_hook: bool = False
    has_post_hook: bool = False
    has_config: bool = False


class LoadedCommand(BaseModel):
    """A fully loaded command ready for execution.

    Represents a command that has been resolved and loaded, including
    the rendered prompt content and optional schema.

    Attributes:
        name: The command name (e.g., "plan", "build").
        resolved: The ResolvedCommand with path and tier information.
        prompt_content: The fully rendered prompt content.
        output_schema: Optional JSON Schema for output validation.
        has_pre_hook: Whether this command has a pre-execution hook.
        has_post_hook: Whether this command has a post-execution hook.

    Example:
        >>> loaded = LoadedCommand(
        ...     name="plan",
        ...     resolved=resolved_cmd,
        ...     prompt_content="Create a plan for...",
        ...     output_schema={"type": "object"},
        ... )
        >>> print(loaded.prompt_content)
        "Create a plan for..."
    """

    model_config = ConfigDict(frozen=True)

    name: str
    resolved: ResolvedCommand
    prompt_content: str
    output_schema: dict[str, Any] | None = None
    has_pre_hook: bool = False
    has_post_hook: bool = False
