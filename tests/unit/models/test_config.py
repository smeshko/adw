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
from adw.models.config import PhaseConfig, ShipConfig, ShipPRConfig, WorktreeConfig


class TestPhaseConfigInputFiles:
    """Tests for PhaseConfig.input_files field (ISS-015)."""

    def test_input_files_none_by_default(self) -> None:
        """PhaseConfig.input_files should be None by default."""
        config = PhaseConfig()
        assert config.input_files is None

    def test_input_files_valid_mapping(self) -> None:
        """PhaseConfig accepts valid input_files mapping."""
        config = PhaseConfig(input_files={"prd": "docs/prd.md", "arch": "docs/arch.md"})
        assert config.input_files == {"prd": "docs/prd.md", "arch": "docs/arch.md"}

    def test_input_files_empty_dict(self) -> None:
        """PhaseConfig accepts empty input_files dict."""
        config = PhaseConfig(input_files={})
        assert config.input_files == {}

    def test_input_files_single_entry(self) -> None:
        """PhaseConfig accepts single-entry input_files."""
        config = PhaseConfig(input_files={"context": "README.md"})
        assert config.input_files == {"context": "README.md"}

    def test_input_files_with_nested_paths(self) -> None:
        """PhaseConfig accepts input_files with deeply nested paths."""
        config = PhaseConfig(input_files={"spec": "docs/specs/api/v2/openapi.yaml"})
        assert config.input_files["spec"] == "docs/specs/api/v2/openapi.yaml"

    # NOTE: test_input_files_in_yaml_parsing removed in ISS-029
    # phases field removed from ProjectConfig - use command configs instead


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


class TestShipConfig:
    """Tests for ShipConfig validation (Story 15.1)."""

    def test_merge_method_rejects_invalid(self) -> None:
        """ShipPRConfig rejects invalid merge_method values."""
        with pytest.raises(ValidationError) as exc_info:
            ShipPRConfig(merge_method="invalid")  # type: ignore[arg-type]
        assert "merge_method" in str(exc_info.value)

    def test_merge_method_accepts_valid_values(self) -> None:
        """ShipPRConfig accepts all valid merge_method values."""
        for method in ["merge", "squash", "rebase"]:
            config = ShipPRConfig(merge_method=method)  # type: ignore[arg-type]
            assert config.merge_method == method

    def test_ship_config_from_yaml(self) -> None:
        """ShipConfig loads correctly from project YAML."""
        yaml_content = """
name: ship-enabled
language: python
ship:
  enabled: true
  commands:
    version_bump: npm version patch
    build: npm run build
    publish: npm publish
  post_publish:
    - git push --tags
    - echo "Published!"
  pr:
    merge_on_success: true
    delete_branch_on_merge: true
    merge_method: squash
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.ship is not None
        assert config.ship.enabled is True
        assert config.ship.commands.version_bump == "npm version patch"
        assert config.ship.commands.build == "npm run build"
        assert config.ship.commands.publish == "npm publish"
        assert config.ship.post_publish == ["git push --tags", 'echo "Published!"']
        assert config.ship.pr.merge_on_success is True
        assert config.ship.pr.merge_method == "squash"

    def test_ship_config_post_publish_defaults_to_empty(self) -> None:
        """ShipConfig.post_publish defaults to empty list."""
        config = ShipConfig()
        assert config.post_publish == []

    def test_ship_config_defaults_to_none(self) -> None:
        """ProjectConfig.ship defaults to None when not specified."""
        yaml_content = """
name: no-ship
language: python
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.ship is None


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

    # NOTE: test_with_phase_config removed in ISS-029
    # phases field removed from ProjectConfig - use command configs instead
