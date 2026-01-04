"""Configuration models for ADW project settings.

This module contains models for project configuration, LLM settings,
and phase-specific configuration loaded from YAML files.
"""

from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, Field, model_validator

from adw.models.security import SecurityConfig


class RetryConfig(BaseModel):
    """Configuration for retry logic with exponential backoff.

    Controls how transient LLM errors (timeouts, rate limits) are handled
    through automatic retries with increasing delays.

    Attributes:
        max_retries: Maximum number of retry attempts.
        base_delay_seconds: Initial delay before first retry.
        max_delay_seconds: Maximum delay cap.
        multiplier: Factor to multiply delay by after each attempt.

    Example:
        >>> config = RetryConfig(max_retries=5, base_delay_seconds=0.5)
        >>> config.multiplier
        2.0
    """

    max_retries: int = Field(
        default=3,
        gt=0,
        description="Maximum number of retry attempts",
    )
    base_delay_seconds: float = Field(
        default=1.0,
        gt=0,
        description="Initial delay before first retry in seconds",
    )
    max_delay_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Maximum delay cap in seconds",
    )
    multiplier: float = Field(
        default=2.0,
        gt=1.0,
        description="Factor to multiply delay by after each attempt",
    )

    @model_validator(mode="after")
    def validate_max_delay_gte_base_delay(self) -> Self:
        """Validate that max_delay_seconds >= base_delay_seconds.

        Returns:
            Self with validated configuration.

        Raises:
            ValueError: If max_delay_seconds < base_delay_seconds.
        """
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError(
                f"max_delay_seconds ({self.max_delay_seconds}) must be >= "
                f"base_delay_seconds ({self.base_delay_seconds})"
            )
        return self


class LLMConfig(BaseModel):
    """Configuration for LLM (Claude Code) settings.

    Attributes:
        path: Path to the Claude Code executable
        timeout_seconds: Maximum time for LLM calls
        max_retries: Number of retry attempts on failure
        model: Model identifier to use
    """

    path: str = Field(
        default="claude",
        description="Path to the Claude Code executable",
    )
    timeout_seconds: int = Field(
        default=300,
        description="Maximum time for LLM calls in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Number of retry attempts on failure",
    )
    model: str | None = Field(
        default=None,
        description="Model identifier to use (e.g., 'claude-3-opus')",
    )


class PhaseConfig(BaseModel):
    """Configuration for a specific phase.

    Attributes:
        enabled: Whether this phase is enabled
        timeout_seconds: Phase-specific timeout override
        pre_hook: Shell command to run before phase
        post_hook: Shell command to run after phase
    """

    enabled: bool = Field(default=True, description="Whether this phase is enabled")
    timeout_seconds: int | None = Field(
        default=None, description="Phase-specific timeout override"
    )
    pre_hook: str | None = Field(
        default=None, description="Shell command to run before phase"
    )
    post_hook: str | None = Field(
        default=None, description="Shell command to run after phase"
    )


class HookConfig(BaseModel):
    """Configuration for shell hooks.

    Attributes:
        shell: Shell to use for executing hooks
        timeout_seconds: Maximum time for hook execution
    """

    shell: str = Field(default="/bin/bash", description="Shell to use for hooks")
    timeout_seconds: int = Field(
        default=60, description="Maximum time for hook execution"
    )


class PipelineConfig(BaseModel):
    """Configuration for pipeline behavior.

    Attributes:
        strict_artifacts: If True, raise ConfigError when a template references
            a missing artifact. If False, use empty string for missing artifacts.
            Default is False for lenient behavior.
    """

    strict_artifacts: bool = Field(
        default=False,
        description="Raise error for missing artifact references in templates",
    )


class RedactionConfig(BaseModel):
    """Configuration for secret redaction in logs.

    Controls how sensitive data is redacted from log output to prevent
    accidental exposure of secrets, API keys, and other sensitive values.

    Attributes:
        enabled: Whether redaction is active (default: True)
        patterns: Additional custom regex patterns to redact
        disable_defaults: If True, only use custom patterns (default: False)

    Example:
        >>> config = RedactionConfig(
        ...     patterns=["ACME_[A-Z0-9]{20}", "my-custom-token-[A-Za-z0-9]+"]
        ... )
        >>> config.enabled
        True
    """

    enabled: bool = Field(
        default=True,
        description="Whether redaction is active",
    )
    patterns: list[str] = Field(
        default_factory=list,
        description="Additional custom regex patterns to redact",
    )
    disable_defaults: bool = Field(
        default=False,
        description="If True, use only custom patterns (skip defaults)",
    )


class LoggingConfig(BaseModel):
    """Configuration for logging behavior.

    Attributes:
        redaction: Secret redaction configuration
    """

    redaction: RedactionConfig = Field(
        default_factory=RedactionConfig,
        description="Secret redaction configuration",
    )


class GitConfig(BaseModel):
    """Configuration for git integration.

    Controls automatic git branch management and commit automation
    during workflow execution. When enabled, ADW will automatically
    create or switch to feature branches based on the feature description
    and optionally commit changes after each phase.

    Attributes:
        enabled: Whether git integration is enabled (default: False)
        branch_prefix: Prefix for auto-created branches (default: "feature/")
        auto_commit: Whether to auto-commit after phases (default: True)
        commit_template: Custom commit message template (optional)

    Example:
        >>> config = GitConfig(enabled=True, branch_prefix="feat/")
        >>> config.branch_prefix
        'feat/'
        >>> config.auto_commit
        True

    YAML example:
        git:
          enabled: true
          branch_prefix: "feature/"
          auto_commit: true
          commit_template: "{phase}: {feature}"
    """

    enabled: bool = Field(
        default=False,
        description="Whether git integration is enabled",
    )
    branch_prefix: str = Field(
        default="feature/",
        description="Prefix for auto-created branches",
    )
    auto_commit: bool = Field(
        default=True,
        description="Whether to auto-commit after phases",
    )
    commit_template: str | None = Field(
        default=None,
        description="Custom commit message template ({phase}, {feature}, {run_id})",
    )


class ProjectConfig(BaseModel):
    """Main project configuration loaded from adw.yaml.

    This model represents the complete project configuration including
    project metadata, LLM settings, and phase configurations.

    Attributes:
        name: Project name
        language: Programming language (e.g., "python", "typescript")
        framework: Framework being used (e.g., "fastapi", "react")
        platform: Target platform (e.g., "cli", "web", "api")
        test_command: Command to run tests
        build_command: Command to build the project
        llm: LLM configuration section
        phases: Phase-specific configuration
        hooks: Hook configuration
        pipeline: Pipeline behavior configuration
        logging: Logging configuration (includes redaction settings)
        security: Security configuration (blocked patterns, allow_dangerous)
        git: Git integration configuration (branch management)

    Example:
        >>> config = ProjectConfig.from_yaml('''
        ... name: my-project
        ... language: python
        ... framework: fastapi
        ... platform: api
        ... ''')
        >>> config.name
        'my-project'
    """

    name: str = Field(..., description="Project name")
    language: str = Field(..., description="Programming language")
    framework: str | None = Field(default=None, description="Framework being used")
    platform: str = Field(default="cli", description="Target platform")
    test_command: str | None = Field(default=None, description="Command to run tests")
    build_command: str | None = Field(
        default=None, description="Command to build the project"
    )
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM configuration")
    phases: dict[str, PhaseConfig] = Field(
        default_factory=dict, description="Phase-specific configuration"
    )
    hooks: HookConfig = Field(
        default_factory=HookConfig, description="Hook configuration"
    )
    pipeline: PipelineConfig = Field(
        default_factory=PipelineConfig, description="Pipeline behavior configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    security: SecurityConfig | None = Field(
        default=None, description="Security configuration"
    )
    git: GitConfig = Field(
        default_factory=GitConfig, description="Git integration configuration"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_required_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Validate that required fields are present.

        Args:
            data: Raw configuration data

        Returns:
            Validated data

        Raises:
            ValueError: If required fields are missing
        """
        if not isinstance(data, dict):
            return data

        required = ["name", "language"]
        missing = [field for field in required if not data.get(field)]

        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        return data

    @classmethod
    def from_yaml(cls, content: str) -> Self:
        """Load configuration from a YAML string.

        Args:
            content: YAML content as a string

        Returns:
            ProjectConfig instance

        Raises:
            ValidationError: If the YAML content is invalid
        """
        data = yaml.safe_load(content)
        return cls.model_validate(data)

    @classmethod
    def from_yaml_file(cls, path: Path | str) -> Self:
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML file

        Returns:
            ProjectConfig instance

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValidationError: If the file content is invalid
        """
        path = Path(path)
        content = path.read_text()
        return cls.from_yaml(content)

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "name": "my-project",
                "language": "python",
                "framework": "fastapi",
                "platform": "api",
                "test_command": "pytest",
                "build_command": "python -m build",
                "llm": {
                    "path": "/usr/bin/claude",
                    "timeout_seconds": 300,
                },
                "security": {
                    "allow_dangerous": False,
                    "blocked_patterns": [],
                },
                "git": {
                    "enabled": False,
                    "branch_prefix": "feature/",
                    "auto_commit": True,
                    "commit_template": None,
                },
            }
        },
    }
