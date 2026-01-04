"""Tests for config models (ProjectConfig, LLMConfig, PhaseConfig)."""

import pytest
from pydantic import ValidationError

from adw.models import (
    HookConfig,
    LLMConfig,
    PhaseConfig,
    ProjectConfig,
)


class TestLLMConfig:
    """Tests for LLMConfig model."""

    def test_defaults(self) -> None:
        """LLMConfig has sensible defaults."""
        config = LLMConfig()
        assert config.path == "claude"
        assert config.timeout_seconds == 300
        assert config.max_retries == 3
        assert config.model is None

    def test_custom_values(self) -> None:
        """LLMConfig accepts custom values."""
        config = LLMConfig(
            path="/usr/local/bin/claude",
            timeout_seconds=600,
            max_retries=5,
            model="claude-3-opus",
        )
        assert config.path == "/usr/local/bin/claude"
        assert config.timeout_seconds == 600
        assert config.max_retries == 5
        assert config.model == "claude-3-opus"


class TestPhaseConfig:
    """Tests for PhaseConfig model."""

    def test_defaults(self) -> None:
        """PhaseConfig has sensible defaults."""
        config = PhaseConfig()
        assert config.enabled is True
        assert config.timeout_seconds is None
        assert config.pre_hook is None
        assert config.post_hook is None

    def test_with_hooks(self) -> None:
        """PhaseConfig with hooks configured."""
        config = PhaseConfig(
            enabled=True,
            timeout_seconds=120,
            pre_hook="npm run lint",
            post_hook="npm run format",
        )
        assert config.timeout_seconds == 120
        assert config.pre_hook == "npm run lint"
        assert config.post_hook == "npm run format"

    def test_disabled_phase(self) -> None:
        """PhaseConfig can disable a phase."""
        config = PhaseConfig(enabled=False)
        assert config.enabled is False


class TestHookConfig:
    """Tests for HookConfig model."""

    def test_defaults(self) -> None:
        """HookConfig has sensible defaults."""
        config = HookConfig()
        assert config.shell == "/bin/bash"
        assert config.timeout_seconds == 60

    def test_custom_shell(self) -> None:
        """HookConfig accepts custom shell."""
        config = HookConfig(
            shell="/bin/zsh",
            timeout_seconds=120,
        )
        assert config.shell == "/bin/zsh"
        assert config.timeout_seconds == 120


class TestProjectConfig:
    """Tests for ProjectConfig model."""

    def test_from_yaml_minimal(self) -> None:
        """ProjectConfig loads from minimal YAML."""
        yaml_content = """
name: my-project
language: python
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.name == "my-project"
        assert config.language == "python"
        assert config.framework is None
        assert config.platform == "cli"

    def test_from_yaml_complete(self) -> None:
        """ProjectConfig loads from complete YAML."""
        yaml_content = """
name: my-api
language: python
framework: fastapi
platform: api
test_command: pytest
build_command: python -m build
llm:
  path: /usr/local/bin/claude
  timeout_seconds: 600
  max_retries: 5
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.name == "my-api"
        assert config.language == "python"
        assert config.framework == "fastapi"
        assert config.platform == "api"
        assert config.test_command == "pytest"
        assert config.build_command == "python -m build"
        assert config.llm.path == "/usr/local/bin/claude"
        assert config.llm.timeout_seconds == 600
        assert config.llm.max_retries == 5

    def test_from_yaml_missing_name(self) -> None:
        """ProjectConfig validates required name field."""
        yaml_content = """
language: python
framework: fastapi
"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig.from_yaml(yaml_content)
        assert "Missing required fields: name" in str(exc_info.value)

    def test_from_yaml_missing_language(self) -> None:
        """ProjectConfig validates required language field."""
        yaml_content = """
name: my-project
framework: fastapi
"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig.from_yaml(yaml_content)
        assert "Missing required fields: language" in str(exc_info.value)

    def test_from_yaml_missing_both_required(self) -> None:
        """ProjectConfig validates both required fields."""
        yaml_content = """
framework: fastapi
platform: api
"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig.from_yaml(yaml_content)
        error_str = str(exc_info.value)
        assert "name" in error_str
        assert "language" in error_str

    def test_defaults_for_optional_fields(self) -> None:
        """ProjectConfig uses defaults for optional fields."""
        yaml_content = """
name: minimal
language: python
"""
        config = ProjectConfig.from_yaml(yaml_content)

        # Check defaults
        assert config.platform == "cli"
        assert config.test_command is None
        assert config.build_command is None
        assert config.framework is None

        # Check nested defaults
        assert config.llm.path == "claude"
        assert config.llm.timeout_seconds == 300
        assert config.hooks.shell == "/bin/bash"

    def test_with_phase_config(self) -> None:
        """ProjectConfig with phase-specific configuration."""
        yaml_content = """
name: phased
language: python
phases:
  plan:
    enabled: true
    timeout_seconds: 120
  code:
    enabled: true
    pre_hook: npm run lint
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert "plan" in config.phases
        assert config.phases["plan"].timeout_seconds == 120
        assert config.phases["code"].pre_hook == "npm run lint"

    def test_empty_yaml_fails(self) -> None:
        """Empty YAML raises ValidationError."""
        with pytest.raises(ValidationError):
            ProjectConfig.from_yaml("")

    def test_validation_error_messages_clear(self) -> None:
        """Validation errors have clear field-level messages."""
        yaml_content = """
framework: fastapi
"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig.from_yaml(yaml_content)

        # Check that the error message mentions the missing fields
        error_str = str(exc_info.value)
        assert "name" in error_str
        assert "language" in error_str
