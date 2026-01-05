# Test Reduction Notes:
# This file has been reduced to focus only on YAML parsing and validation tests.
# Removed trivial tests including:
#   - test_defaults() methods (Pydantic handles defaults; no business logic to test)
#   - Simple assignment verification tests (test_custom_values, test_disabled, etc.)
#   - Redundant nested config tests covered by test_from_yaml_complete
# Kept: YAML parsing tests and validation error tests that verify actual business logic.

"""Tests for config models (ProjectConfig, LLMConfig, PhaseConfig)."""

import pytest
from pydantic import ValidationError

from adw.models import ProjectConfig


class TestProjectConfig:
    """Tests for ProjectConfig YAML parsing and validation."""

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

    def test_empty_yaml_fails(self) -> None:
        """Empty YAML raises ValidationError."""
        with pytest.raises(ValidationError):
            ProjectConfig.from_yaml("")

    def test_with_git_config(self) -> None:
        """ProjectConfig with git integration enabled."""
        yaml_content = """
name: git-enabled
language: python
git:
  enabled: true
  branch_prefix: "feat/"
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.git.enabled is True
        assert config.git.branch_prefix == "feat/"

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
