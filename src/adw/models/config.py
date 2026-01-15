"""Configuration models for ADW project settings.

This module contains models for project configuration, LLM settings,
and phase-specific configuration loaded from YAML files.
"""

from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, Field, model_validator

from adw.models.security import SecurityConfig
from adw.models.webhook import WebhookConfig
from adw.validation.config import ValidationConfig


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
        input_files: Optional mapping of variable names to file paths for template
            injection. Files are loaded at phase start and made available as
            {{ inputs.name }} in prompt templates.

    Example:
        >>> config = PhaseConfig(
        ...     input_files={"prd": "docs/prd.md", "arch": "docs/architecture.md"}
        ... )
        >>> config.input_files
        {'prd': 'docs/prd.md', 'arch': 'docs/architecture.md'}

    YAML example:
        phases:
          plan:
            enabled: true
            input_files:
              prd: docs/prd.md
              architecture: docs/architecture.md
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
    input_files: dict[str, str] | None = Field(
        default=None,
        description="Mapping of variable names to file paths for template injection",
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


class PortRangeConfig(BaseModel):
    """Configuration for port ranges used in concurrent run isolation.

    Defines the starting port numbers for backend and frontend services
    in each concurrent run. Ports are allocated as base + slot_number.

    Attributes:
        backend_start: Starting port for backend services (default: 9100)
        frontend_start: Starting port for frontend services (default: 9200)

    Example:
        >>> config = PortRangeConfig(backend_start=8000, frontend_start=8100)
        >>> config.backend_start
        8000
    """

    backend_start: int = Field(
        default=9100,
        gt=0,
        lt=65536,
        description="Starting port for backend services",
    )
    frontend_start: int = Field(
        default=9200,
        gt=0,
        lt=65536,
        description="Starting port for frontend services",
    )


class WorktreeConfig(BaseModel):
    """Configuration for git worktree isolation.

    Controls how ADW manages git worktrees for isolated concurrent
    run execution. When enabled, each run executes in its own worktree,
    preventing concurrent runs from interfering with each other.

    Attributes:
        enabled: Whether worktree isolation is enabled (default: True)
        base_dir: Directory for storing worktrees, relative to project root
        preserve_on_failure: DEPRECATED (ISS-020). Worktrees are now always
            preserved. Use 'adw cleanup <run_id>' to remove worktrees.
        cleanup_branch_on_remove: Delete the adw/<run_id> branch when removing
            the worktree (default: False)
        preserve_artifacts: List of artifact names to preserve when cleaning up
            worktrees (default: ["context.json", "logs", "artifacts", "llm"])
        artifact_manifest_file: Name of manifest file created during preservation
            (default: "worktree-artifacts.json")
        port_range: Configuration for port allocation ranges
        max_concurrent: Maximum number of concurrent runs (determines slot count)

    Example:
        >>> config = WorktreeConfig(enabled=True, base_dir=".worktrees")
        >>> config.enabled
        True
        >>> config.base_dir
        '.worktrees'
        >>> config.preserve_artifacts
        ['context.json', 'logs', 'artifacts', 'llm']

    YAML example:
        worktree:
          enabled: true
          base_dir: "trees"
          # preserve_on_failure is deprecated - worktrees are always preserved
          cleanup_branch_on_remove: false
          preserve_artifacts:
            - context.json
            - logs
            - artifacts
            - llm
            - custom-output.json
          artifact_manifest_file: "worktree-artifacts.json"
          port_range:
            backend_start: 9100
            frontend_start: 9200
          max_concurrent: 15
    """

    enabled: bool = Field(
        default=True,
        description="Whether worktree isolation is enabled",
    )
    base_dir: str = Field(
        default="trees",
        description="Directory for storing worktrees (relative to project root)",
    )
    preserve_on_failure: bool = Field(
        default=True,
        description="DEPRECATED (ISS-020): This option is ignored. Worktrees are "
        "now always preserved. Use 'adw cleanup <run_id>' to remove worktrees.",
    )
    cleanup_branch_on_remove: bool = Field(
        default=False,
        description="Delete the adw/<run_id> branch when removing worktree",
    )
    preserve_artifacts: list[str] = Field(
        default=["context.json", "logs", "artifacts", "llm"],
        description="List of artifact names to preserve when cleaning up worktrees",
    )
    artifact_manifest_file: str = Field(
        default="worktree-artifacts.json",
        description="Name of manifest file created during artifact preservation",
    )
    port_range: PortRangeConfig = Field(
        default_factory=PortRangeConfig,
        description="Port range configuration for concurrent runs",
    )
    max_concurrent: int = Field(
        default=15,
        gt=0,
        le=100,
        description="Maximum number of concurrent runs (slot count)",
    )

    @model_validator(mode="after")
    def validate_port_ranges(self) -> Self:
        """Validate that port ranges don't exceed valid port numbers.

        Ensures that backend_start + max_concurrent - 1 and
        frontend_start + max_concurrent - 1 don't exceed 65535.

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If port range would exceed valid port numbers.
        """
        max_backend = self.port_range.backend_start + self.max_concurrent - 1
        max_frontend = self.port_range.frontend_start + self.max_concurrent - 1

        if max_backend > 65535:
            msg = (
                f"Backend port range exceeds valid ports: "
                f"{self.port_range.backend_start} + {self.max_concurrent} - 1 "
                f"= {max_backend} > 65535"
            )
            raise ValueError(msg)

        if max_frontend > 65535:
            msg = (
                f"Frontend port range exceeds valid ports: "
                f"{self.port_range.frontend_start} + {self.max_concurrent} - 1 "
                f"= {max_frontend} > 65535"
            )
            raise ValueError(msg)

        return self


class TaskManagerLabelsConfig(BaseModel):
    """Configuration for label management in task managers.

    Controls how ADW manages labels on tasks in external task management
    systems like Linear, Jira, or GitHub Issues.

    Attributes:
        enabled: Whether label management is enabled (default: True)
        prefix: Prefix for ADW-managed labels (default: "adw:")

    Example:
        >>> config = TaskManagerLabelsConfig(enabled=True, prefix="ci:")
        >>> config.enabled
        True
        >>> config.prefix
        'ci:'

    YAML example:
        task_manager:
          labels:
            enabled: true
            prefix: "adw:"
    """

    enabled: bool = Field(
        default=True,
        description="Whether label management is enabled",
    )
    prefix: str = Field(
        default="adw:",
        description="Prefix for ADW-managed labels",
    )


class TaskManagerConfig(BaseModel):
    """Configuration for external task management integration.

    Controls how ADW integrates with external task management systems
    like Linear, Jira, or GitHub Issues. This includes fetching task
    information, updating status, and syncing comments.

    Attributes:
        type: Task manager type ("none", "linear")
        team_key: Team prefix for ID detection (e.g., "RULE" for RULE-123)
        state_mapping: Phase-based mapping from ADW phases to external system states
        sync_comments: Whether to post comments on status transitions
        comment_on_failure_only: Only post comments when runs fail
        pr_title_format: Format for PR titles when task ID is present
        labels: Label management configuration
        auto_close: Whether to close task when PR is merged (default: false)
        include_labels: Include task labels in context
        include_parent: Include parent task info in context

    Example:
        >>> config = TaskManagerConfig(
        ...     type="linear",
        ...     team_key="RULE",
        ...     sync_comments=True,
        ... )
        >>> config.type
        'linear'

    YAML example:
        task_manager:
          type: linear
          team_key: RULE
          state_mapping:
            plan: "In Progress"
            build: "In Progress"
            validate: "In Review"
            document: "In Review"
            failed: "In Progress"
          sync_comments: true
          pr_title_format: "{task_id}: {description}"
          labels:
            enabled: true
            prefix: "adw:"
          auto_close: false
    """

    type: Literal["none", "linear"] = Field(
        default="none",
        description="Task manager type (none, linear)",
    )
    team_key: str | None = Field(
        default=None,
        description="Team prefix for ID detection (e.g., 'RULE' for RULE-123)",
    )
    state_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "plan": "In Progress",
            "build": "In Progress",
            "validate": "In Review",
            "document": "In Review",
            "failed": "In Progress",
        },
        description="Phase-based mapping from ADW phases to external system states",
    )
    sync_comments: bool = Field(
        default=False,
        description="Whether to post comments on status transitions",
    )
    comment_on_failure_only: bool = Field(
        default=False,
        description="Only post comments when runs fail",
    )
    pr_title_format: str = Field(
        default="{task_id}: {description}",
        description="Format for PR titles when task ID is present",
    )
    labels: TaskManagerLabelsConfig = Field(
        default_factory=TaskManagerLabelsConfig,
        description="Label management configuration",
    )
    auto_close: bool = Field(
        default=False,
        description="Whether to close task when PR is merged",
    )
    include_labels: bool = Field(
        default=True,
        description="Include task labels in context",
    )
    include_parent: bool = Field(
        default=True,
        description="Include parent task info in context",
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
        skip_hooks: Skip pre-commit hooks with --no-verify (default: False)
        auto_create_pr: Whether to auto-create PR after successful run (default: True)

    Example:
        >>> config = GitConfig(enabled=True, branch_prefix="feat/")
        >>> config.branch_prefix
        'feat/'
        >>> config.auto_commit
        True
        >>> config.auto_create_pr
        True

    YAML example:
        git:
          enabled: true
          branch_prefix: "feature/"
          auto_commit: true
          commit_template: "{phase}: {feature}"
          skip_hooks: false
          auto_create_pr: true
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
    skip_hooks: bool = Field(
        default=False,
        description="Skip pre-commit hooks with --no-verify (use with caution)",
    )
    auto_create_pr: bool = Field(
        default=True,
        description="Whether to auto-create PR after successful run (requires gh CLI)",
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
        task_manager: Task manager integration configuration (Linear, Jira, etc.)

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
    worktree: WorktreeConfig = Field(
        default_factory=WorktreeConfig, description="Worktree isolation configuration"
    )
    validation: ValidationConfig = Field(
        default_factory=ValidationConfig,
        description="Validation phase configuration (validators, settings)",
    )
    task_manager: TaskManagerConfig = Field(
        default_factory=TaskManagerConfig,
        description="Task manager integration configuration",
    )
    webhook: WebhookConfig = Field(
        default_factory=WebhookConfig,
        description="Webhook server configuration",
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
                    "skip_hooks": False,
                    "auto_create_pr": True,
                },
            }
        },
    }
