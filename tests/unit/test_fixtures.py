"""Tests for shared pytest fixtures.

This module verifies that the fixtures defined in conftest.py work correctly.
"""

from pathlib import Path

from adw.executors.mock import MockExecutor
from adw.models import ProjectConfig, RunContext


def test_tmp_adw_dir_fixture(tmp_adw_dir: Path) -> None:
    """tmp_adw_dir creates proper directory structure."""
    assert tmp_adw_dir.exists()
    assert tmp_adw_dir.name == ".adw"
    assert (tmp_adw_dir / "runs").exists()
    assert (tmp_adw_dir / "commands").exists()


def test_mock_executor_fixture(mock_executor: MockExecutor) -> None:
    """mock_executor returns fresh MockExecutor instance."""
    assert isinstance(mock_executor, MockExecutor)
    assert mock_executor.call_count == 0
    assert mock_executor.last_prompt is None


def test_sample_run_context_fixture(sample_run_context: RunContext) -> None:
    """sample_run_context returns valid RunContext."""
    assert isinstance(sample_run_context, RunContext)
    assert len(sample_run_context.run_id) == 26  # ULID length
    assert sample_run_context.feature_description == "Add user authentication"
    assert sample_run_context.current_phase == "plan"
    assert sample_run_context.status == "running"


def test_sample_project_config_fixture(sample_project_config: ProjectConfig) -> None:
    """sample_project_config returns valid ProjectConfig."""
    assert isinstance(sample_project_config, ProjectConfig)
    assert sample_project_config.name == "test-project"
    assert sample_project_config.language == "python"
    assert sample_project_config.framework == "fastapi"
    assert sample_project_config.platform == "backend"


def test_fixtures_path_fixture(fixtures_path: Path) -> None:
    """fixtures_path returns path to test fixtures directory."""
    assert fixtures_path.exists()
    assert fixtures_path.name == "fixtures"
    assert (fixtures_path / "configs").exists()
    assert (fixtures_path / "runs").exists()
    assert (fixtures_path / "llm").exists()


def test_sample_config_yaml_fixture(sample_config_yaml: str) -> None:
    """sample_config_yaml loads valid YAML content."""
    assert isinstance(sample_config_yaml, str)
    assert "name: test-project" in sample_config_yaml
    assert "language: python" in sample_config_yaml

    # Verify it can be parsed into a ProjectConfig
    config = ProjectConfig.from_yaml(sample_config_yaml)
    assert config.name == "test-project"
    assert config.language == "python"
