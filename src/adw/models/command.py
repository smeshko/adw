"""Command-related Pydantic models.

This module defines models for command resolution, representation, and configuration.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

if TYPE_CHECKING:
    pass


class PhaseLLMConfig(BaseModel):
    """Phase-specific LLM configuration for config.yaml.

    Unlike the global LLMConfig in config.py which configures the executor path
    and timeouts, this model configures LLM behavior for a specific phase command.

    Attributes:
        model: Model identifier to use for this phase (e.g., "claude-3-opus").

    Example:
        >>> llm_config = PhaseLLMConfig(model="claude-3-opus")
        >>> llm_config.model
        'claude-3-opus'
    """

    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(
        default=None,
        description="Model identifier to use for this phase",
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str | None) -> str | None:
        """Validate and normalize model identifier.

        Normalizes common model names to lowercase while allowing
        full model IDs for backwards compatibility.

        Args:
            v: Model identifier string or None.

        Returns:
            Normalized model identifier or None.
        """
        if v is None:
            return v

        valid_models = {"opus", "sonnet", "haiku"}
        if v.lower() in valid_models:
            return v.lower()

        # Allow full model IDs for backwards compatibility
        return v


class CommandConfig(BaseModel):
    """Phase command configuration loaded from config.yaml.

    Each phase command folder can have an optional config.yaml that defines
    defaults for that command. These defaults are merged with project-level
    PhaseConfig from project.yaml, where project settings take precedence.

    Attributes:
        enabled: Whether this phase is enabled. Disabled phases are skipped.
        timeout_seconds: Default timeout for this command in seconds.
        input_files: Mapping of variable names to file paths for template injection.
            Files are loaded at phase start and available as {{ inputs.name }}.
        llm: Phase-specific LLM settings (model).
    Example:
        >>> config = CommandConfig(
        ...     enabled=True,
        ...     timeout_seconds=600,
        ...     input_files={"prd": "docs/prd.md"},
        ...     llm=PhaseLLMConfig(model="claude-3-opus"),
        ... )
        >>> config.timeout_seconds
        600

    YAML example (in command folder's config.yaml):
        enabled: true
        timeout_seconds: 600
        input_files:
          prd: docs/prd.md
          architecture: docs/architecture.md
        llm:
          model: claude-3-opus
    Merging behavior:
        When merged with project's PhaseConfig, project settings override command
        defaults. For dictionaries (input_files), values are merged with project
        values taking precedence for duplicate keys.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Whether this phase is enabled. Disabled phases are skipped.",
    )
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


class ShipCommandsConfig(BaseModel):
    """Configuration for shell commands executed during ship phase.

    Defines optional shell commands for version bump and publish
    steps during deployment. Each command is executed in sequence if defined.

    Note: build_command is configured at the project level (ProjectConfig.build_command)
    and injected into the template context by PhaseRunner, not here.

    Attributes:
        version_bump: Command to bump version (e.g., "npm version patch")
        publish: Command to publish package (e.g., "npm publish")

    Example:
        >>> config = ShipCommandsConfig(
        ...     version_bump="npm version patch",
        ...     publish="npm publish"
        ... )
        >>> config.version_bump
        'npm version patch'

    YAML example:
        ship:
          commands:
            version_bump: npm version patch
            publish: npm publish
    """

    model_config = ConfigDict(extra="forbid")

    version_bump: str | None = Field(
        default=None,
        description="Command to bump version (e.g., 'npm version patch')",
    )
    publish: str | None = Field(
        default=None,
        description="Command to publish package or deploy",
    )


class ValidateCommandConfig(CommandConfig):
    """Validate phase configuration extending CommandConfig.

    Typed marker subclass for the validate phase. Preserves the per-phase
    config class pattern used by loader.py for config.yaml validation.

    Note: test_command is configured at the project level (ProjectConfig.test_command)
    and injected into the template context by PhaseRunner, not here.

    YAML example (in .adw/commands/validate/config.yaml):
        enabled: true
        timeout_seconds: 600
    """

    model_config = ConfigDict(extra="forbid")


class DocMappingConfig(BaseModel):
    """Configuration for mapping source files to documentation directories.

    Used by the document phase to identify which documentation files should
    be updated when specific source files change.

    Attributes:
        source_pattern: Glob pattern for source files (e.g., "src/core/**/*.py").
        docs_dir: Directory containing documentation files to update.

    Example:
        >>> mapping = DocMappingConfig(
        ...     source_pattern="src/adw/core/**/*.py",
        ...     docs_dir="docs/architecture/deep-dive"
        ... )
        >>> mapping.source_pattern
        'src/adw/core/**/*.py'

    YAML example:
        doc_mappings:
          - source_pattern: "src/adw/core/**/*.py"
            docs_dir: "docs/architecture/deep-dive"
    """

    model_config = ConfigDict(extra="forbid")

    source_pattern: str = Field(
        ...,
        min_length=1,
        description="Glob pattern for source files (e.g., 'src/core/**/*.py')",
    )
    docs_dir: str = Field(
        ...,
        min_length=1,
        description="Directory containing documentation files to update",
    )


class DocumentCommandConfig(CommandConfig):
    """Document phase configuration extending CommandConfig.

    Contains settings for the document phase including doc_mappings that
    map source file patterns to documentation directories for automatic
    surgical updates.

    Attributes:
        doc_mappings: List of source-to-docs directory mappings. When files
            matching source_pattern change, the document phase looks for
            corresponding docs in docs_dir (matched by filename stem).

    Example:
        >>> config = DocumentCommandConfig(
        ...     doc_mappings=[
        ...         DocMappingConfig(
        ...             source_pattern="src/core/**/*.py",
        ...             docs_dir="docs/architecture"
        ...         )
        ...     ]
        ... )
        >>> config.doc_mappings[0].source_pattern
        'src/core/**/*.py'

    YAML example (in .adw/commands/document/config.yaml):
        enabled: true
        timeout_seconds: 600
        doc_mappings:
          - source_pattern: "src/adw/core/**/*.py"
            docs_dir: "docs/architecture/deep-dive"
          - source_pattern: "src/adw/cli/**/*.py"
            docs_dir: "docs/cli"
    """

    model_config = ConfigDict(extra="forbid")

    doc_mappings: list[DocMappingConfig] | None = Field(
        default=None,
        description="List of source file to documentation directory mappings",
    )


class ShipCommandConfig(CommandConfig):
    """Ship phase configuration extending CommandConfig.

    Contains all settings for the ship phase including deployment commands
    and CI bypass settings.

    Attributes:
        commands: Shell commands for version bump, build, and publish steps.
        bypass_ci: Bypass CI checks using --admin flag (default: True).

    Example:
        >>> config = ShipCommandConfig(
        ...     commands=ShipCommandsConfig(version_bump="npm version patch"),
        ...     bypass_ci=True,
        ... )
        >>> config.commands.version_bump
        'npm version patch'

    YAML example (in .adw/commands/ship/config.yaml):
        enabled: true
        timeout_seconds: 900
        commands:
          version_bump: npm version patch
          publish: npm publish
        bypass_ci: true
    """

    model_config = ConfigDict(extra="forbid")

    commands: ShipCommandsConfig = Field(
        default_factory=ShipCommandsConfig,
        description="Shell commands for deployment steps",
    )
    bypass_ci: bool = Field(
        default=True,
        description="Bypass CI checks using --admin flag (requires admin access)",
    )


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
        pre_hook_path: Path to pre-hook script if found, None otherwise.
        post_hook_path: Path to post-hook script if found, None otherwise.
        has_pre_hook: Computed property - True if pre_hook_path is set.
        has_post_hook: Computed property - True if post_hook_path is set.
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
    pre_hook_path: Path | None = None
    post_hook_path: Path | None = None
    has_config: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_pre_hook(self) -> bool:
        """Whether a pre-hook script exists."""
        return self.pre_hook_path is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_post_hook(self) -> bool:
        """Whether a post-hook script exists."""
        return self.post_hook_path is not None


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
        config: Optional CommandConfig loaded from config.yaml.

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
    config: CommandConfig | None = None
