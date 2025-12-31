"""Configuration models for ADW project settings.

This module contains models for project configuration, LLM settings,
and phase-specific configuration loaded from YAML files.
"""

from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, Field, model_validator


class LLMConfig(BaseModel):
    """Configuration for LLM (Claude Code) settings.

    Attributes:
        path: Path to the Claude Code executable
        timeout_seconds: Maximum time for LLM calls
        max_retries: Number of retry attempts on failure
        model: Model identifier to use
    """

    path: str = Field(
        default="/usr/bin/claude",
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
            }
        },
    }
