# Test Reduction Notes:
# This file has been reduced to focus only on YAML parsing and validation tests.
# Removed trivial tests including:
#   - test_defaults() methods (Pydantic handles defaults; no business logic to test)
#   - Simple assignment verification tests (test_custom_values, test_disabled, etc.)
#   - Redundant nested config tests covered by test_yaml_complete
# Kept: YAML parsing tests and validation error tests that verify actual business logic.

"""Tests for config models (ProjectConfig, LLMConfig, PhaseConfig)."""

import pytest
import yaml
from pydantic import ValidationError

from adw.models import ProjectConfig
from adw.models.command import ShipCommandConfig
from adw.models.config import GitConfig, PhaseConfig


def _from_yaml(text: str) -> ProjectConfig:
    """Parse a project.yaml string into a ProjectConfig."""
    return ProjectConfig.model_validate(yaml.safe_load(text))


class TestPhaseConfigInputFiles:
    """Tests for PhaseConfig.input_files field."""

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


class TestWorktreeConfig:
    """Tests for loading the worktree section of project.yaml."""

    def test_legacy_port_range_is_ignored(self) -> None:
        """A pre-2.2 project.yaml with worktree.port_range still loads.

        Phase 2.2 removed port allocation. This file is the one intended
        match of that plan's port_range grep. The overlapping range below
        was rejected by the old validator, so loading it shows the key is
        ignored rather than still validated.
        """
        yaml_content = """
name: legacy
language: python
worktree:
  max_concurrent: 3
  port_range:
    backend_start: 9100
    frontend_start: 9100
"""
        config = _from_yaml(yaml_content)
        assert config.worktree.max_concurrent == 3


class TestGitConfig:
    """Tests for GitConfig.base_branch defaulting."""

    @pytest.mark.parametrize("kwargs", [{}, {"base_branch": None}, {"base_branch": ""}])
    def test_git_config_base_branch_defaults_to_main(
        self, kwargs: dict[str, str | None]
    ) -> None:
        """Unset, null and blank base_branch all resolve to 'main'."""
        assert GitConfig(**kwargs).base_branch == "main"

    def test_git_config_keeps_explicit_base_branch(self) -> None:
        """An explicit base_branch is kept as-is."""
        assert GitConfig(base_branch="develop").base_branch == "develop"

    def test_project_yaml_with_null_base_branch_loads_main(self) -> None:
        """A project.yaml with git.base_branch: null loads with 'main'."""
        yaml_content = """
name: my-project
language: python
git:
  base_branch: null
"""
        config = _from_yaml(yaml_content)
        assert config.git.base_branch == "main"


class TestShipCommandConfig:
    """Tests for ShipCommandConfig validation.

    Ship configuration lives in the phase-specific config at
    .adw/commands/ship/config.yaml, so these tests validate the
    ShipCommandConfig class directly.
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

    def test_yaml_minimal(self) -> None:
        """ProjectConfig loads from minimal YAML."""
        yaml_content = """
name: my-project
language: python
"""
        config = _from_yaml(yaml_content)
        assert config.name == "my-project"
        assert config.language == "python"
        assert config.framework is None
        assert config.platform == "cli"

    def test_yaml_complete(self) -> None:
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
        config = _from_yaml(yaml_content)
        assert config.name == "my-api"
        assert config.language == "python"
        assert config.framework == "fastapi"
        assert config.platform == "api"
        assert config.test_command == "pytest"
        assert config.build_command == "python -m build"
        assert config.llm.path == "/usr/local/bin/claude"

    def test_yaml_missing_name(self) -> None:
        """ProjectConfig validates required name field."""
        yaml_content = """
language: python
framework: fastapi
"""
        with pytest.raises(ValidationError) as exc_info:
            _from_yaml(yaml_content)
        assert "Missing required fields: name" in str(exc_info.value)

    def test_yaml_missing_language(self) -> None:
        """ProjectConfig validates required language field."""
        yaml_content = """
name: my-project
framework: fastapi
"""
        with pytest.raises(ValidationError) as exc_info:
            _from_yaml(yaml_content)
        assert "Missing required fields: language" in str(exc_info.value)

    def test_yaml_missing_both_required(self) -> None:
        """ProjectConfig validates both required fields."""
        yaml_content = """
framework: fastapi
platform: api
"""
        with pytest.raises(ValidationError) as exc_info:
            _from_yaml(yaml_content)
        error_str = str(exc_info.value)
        assert "name" in error_str
        assert "language" in error_str

    def test_empty_yaml_fails(self) -> None:
        """Empty YAML raises ValidationError."""
        with pytest.raises(ValidationError):
            _from_yaml("")

    def test_with_git_config(self) -> None:
        """ProjectConfig with git integration configured."""
        yaml_content = """
name: git-enabled
language: python
git:
  branch_prefix: "feat/"
"""
        config = _from_yaml(yaml_content)
        assert config.git.branch_prefix == "feat/"
