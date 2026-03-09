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
from adw.models.command import ShipCommandConfig
from adw.models.config import PhaseConfig, WorktreeConfig


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
        # Use non-overlapping ranges (backend 65506-65520, frontend 65521-65535)
        config = WorktreeConfig(
            port_range=PortRangeConfig(
                backend_start=65506,
                frontend_start=65521,
            ),
            max_concurrent=15,
        )
        assert config.port_range.backend_start == 65506
        assert config.port_range.frontend_start == 65521

    def test_port_range_overlap_rejected(self) -> None:
        """WorktreeConfig rejects overlapping backend/frontend port ranges."""
        from adw.models.config import PortRangeConfig

        with pytest.raises(ValueError) as exc_info:
            WorktreeConfig(
                port_range=PortRangeConfig(
                    backend_start=9100,
                    frontend_start=9110,  # overlaps with 9100-9114
                ),
                max_concurrent=15,
            )
        assert "overlaps" in str(exc_info.value)

    def test_port_range_adjacent_valid(self) -> None:
        """WorktreeConfig accepts adjacent (non-overlapping) port ranges."""
        from adw.models.config import PortRangeConfig

        # Backend: 9100-9114, Frontend: 9115-9129 — adjacent, no overlap
        config = WorktreeConfig(
            port_range=PortRangeConfig(
                backend_start=9100,
                frontend_start=9115,
            ),
            max_concurrent=15,
        )
        assert config.port_range.backend_start == 9100
        assert config.port_range.frontend_start == 9115

    def test_port_range_overlap_same_start(self) -> None:
        """WorktreeConfig rejects identical backend/frontend start ports."""
        from adw.models.config import PortRangeConfig

        with pytest.raises(ValueError) as exc_info:
            WorktreeConfig(
                port_range=PortRangeConfig(
                    backend_start=9100,
                    frontend_start=9100,
                ),
                max_concurrent=15,
            )
        assert "overlaps" in str(exc_info.value)


class TestShipCommandConfig:
    """Tests for ShipCommandConfig validation (ISS-031 refactored from Story 15.1).

    Note: Ship configuration has been moved from ProjectConfig.ship to
    phase-specific config at .adw/commands/ship/config.yaml. These tests
    now validate the ShipCommandConfig class directly.
    """

    def test_ship_command_config_defaults(self) -> None:
        """ShipCommandConfig has expected defaults."""
        config = ShipCommandConfig()
        assert config.enabled is True
        assert config.commands.version_bump is None
        assert config.commands.publish is None
        assert config.bypass_ci is True
        assert config.wait_for_merge is False

    def test_ship_command_config_with_values(self) -> None:
        """ShipCommandConfig accepts all ship-specific fields."""
        config = ShipCommandConfig(
            enabled=True,
            commands={
                "version_bump": "npm version patch",
                "publish": "npm publish",
            },
            bypass_ci=False,
            wait_for_merge=True,
        )
        assert config.commands.version_bump == "npm version patch"
        assert config.commands.publish == "npm publish"
        assert config.bypass_ci is False
        assert config.wait_for_merge is True


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
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.name == "my-api"
        assert config.language == "python"
        assert config.framework == "fastapi"
        assert config.platform == "api"
        assert config.test_command == "pytest"
        assert config.build_command == "python -m build"
        assert config.llm.path == "/usr/local/bin/claude"

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
        """ProjectConfig with git integration configured."""
        yaml_content = """
name: git-enabled
language: python
git:
  branch_prefix: "feat/"
"""
        config = ProjectConfig.from_yaml(yaml_content)
        assert config.git.branch_prefix == "feat/"

    # NOTE: test_with_phase_config removed in ISS-029
    # phases field removed from ProjectConfig - use command configs instead
