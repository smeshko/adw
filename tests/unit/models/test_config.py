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
from adw.models.config import WorktreeConfig


class TestWorktreeConfig:
    """Tests for WorktreeConfig validation rules."""

    def test_preserve_artifacts_defaults(self) -> None:
        """WorktreeConfig has default preserve_artifacts list."""
        config = WorktreeConfig()
        assert config.preserve_artifacts == ["context.json", "logs", "artifacts", "llm"]

    def test_preserve_artifacts_custom(self) -> None:
        """WorktreeConfig accepts custom preserve_artifacts list."""
        config = WorktreeConfig(
            preserve_artifacts=["context.json", "logs", "custom.json"]
        )
        assert config.preserve_artifacts == ["context.json", "logs", "custom.json"]

    def test_artifact_manifest_file_default(self) -> None:
        """WorktreeConfig has default artifact_manifest_file."""
        config = WorktreeConfig()
        assert config.artifact_manifest_file == "worktree-artifacts.json"

    def test_artifact_manifest_file_custom(self) -> None:
        """WorktreeConfig accepts custom artifact_manifest_file."""
        config = WorktreeConfig(artifact_manifest_file="custom-manifest.json")
        assert config.artifact_manifest_file == "custom-manifest.json"

    def test_port_range_defaults(self) -> None:
        """WorktreeConfig has default port range settings."""
        config = WorktreeConfig()
        assert config.port_range.backend_start == 9100
        assert config.port_range.frontend_start == 9200
        assert config.max_concurrent == 15

    def test_custom_port_range(self) -> None:
        """WorktreeConfig accepts custom port range."""
        from adw.models.config import PortRangeConfig

        config = WorktreeConfig(
            port_range=PortRangeConfig(
                backend_start=8000,
                frontend_start=8100,
            ),
            max_concurrent=10,
        )
        assert config.port_range.backend_start == 8000
        assert config.port_range.frontend_start == 8100
        assert config.max_concurrent == 10

    def test_port_range_validation_backend_overflow(self) -> None:
        """WorktreeConfig rejects port ranges that would exceed 65535."""
        from adw.models.config import PortRangeConfig

        with pytest.raises(ValueError) as exc_info:
            WorktreeConfig(
                port_range=PortRangeConfig(backend_start=65530),
                max_concurrent=15,
            )
        assert "Backend port range exceeds valid ports" in str(exc_info.value)

    def test_port_range_validation_frontend_overflow(self) -> None:
        """WorktreeConfig rejects frontend port ranges that would exceed 65535."""
        from adw.models.config import PortRangeConfig

        with pytest.raises(ValueError) as exc_info:
            WorktreeConfig(
                port_range=PortRangeConfig(frontend_start=65530),
                max_concurrent=15,
            )
        assert "Frontend port range exceeds valid ports" in str(exc_info.value)

    def test_port_range_validation_edge_case_valid(self) -> None:
        """WorktreeConfig accepts port ranges at the edge of valid range."""
        from adw.models.config import PortRangeConfig

        # 65521 + 15 - 1 = 65535, which is the max valid port
        config = WorktreeConfig(
            port_range=PortRangeConfig(
                backend_start=65521,
                frontend_start=65521,
            ),
            max_concurrent=15,
        )
        assert config.port_range.backend_start == 65521


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
