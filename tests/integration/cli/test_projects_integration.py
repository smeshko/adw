"""Integration tests for project registry CLI commands (Story 16-1).

These tests verify the register, unregister, and projects commands work
correctly with real file system operations and the global registry.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


@pytest.fixture
def temp_registry(tmp_path: Path):
    """Create a temporary registry file for testing."""
    registry_path = tmp_path / "projects.yaml"
    # Override the registry path via environment variable
    with patch.dict("os.environ", {"ADW_TEST_REGISTRY_PATH": str(registry_path)}):
        yield registry_path


@pytest.fixture
def project_dir(tmp_path: Path):
    """Create a project directory with .adw folder."""
    project = tmp_path / "my-project"
    project.mkdir()
    adw_dir = project / ".adw"
    adw_dir.mkdir()
    return project


@pytest.fixture
def mock_cwd(project_dir: Path):
    """Mock current working directory to project_dir."""
    with (
        patch("adw.cli.register.Path.cwd", return_value=project_dir),
        patch("adw.cli.unregister.Path.cwd", return_value=project_dir),
    ):
        yield project_dir


class TestRegisterUnregisterFlow:
    """Tests for register -> projects -> unregister flow."""

    def test_register_shows_project_in_list(
        self, temp_registry: Path, mock_cwd: Path
    ) -> None:
        """Registering a project makes it appear in projects list."""
        # Register the project
        result = runner.invoke(app, ["register", "--name", "Test Project"])
        assert result.exit_code == 0
        assert "registered" in result.output.lower()

        # Verify project appears in list (table output is easier to parse)
        result = runner.invoke(app, ["projects"])
        assert result.exit_code == 0
        assert "Test Project" in result.output

    def test_unregister_removes_project_from_list(
        self, temp_registry: Path, mock_cwd: Path
    ) -> None:
        """Unregistering a project removes it from projects list."""
        # Register first
        runner.invoke(app, ["register", "--name", "Test Project"])

        # Then unregister
        result = runner.invoke(app, ["unregister"])
        assert result.exit_code == 0
        assert "unregistered" in result.output.lower()

        # Verify project no longer in list
        result = runner.invoke(app, ["projects"])
        assert result.exit_code == 0
        assert "Test Project" not in result.output

    def test_register_without_adw_dir_fails(
        self, temp_registry: Path, tmp_path: Path
    ) -> None:
        """Register fails if .adw directory doesn't exist."""
        project = tmp_path / "no-adw-project"
        project.mkdir()

        with patch("adw.cli.register.Path.cwd", return_value=project):
            result = runner.invoke(app, ["register"])

        assert result.exit_code != 0
        assert ".adw" in result.output or "init" in result.output.lower()


class TestProjectsCommand:
    """Tests for projects command output."""

    def test_projects_table_output(self, temp_registry: Path, mock_cwd: Path) -> None:
        """Table output includes expected columns."""
        runner.invoke(app, ["register", "--name", "Test Project"])

        result = runner.invoke(app, ["projects"])
        assert result.exit_code == 0

        # Table should have headers
        assert "Name" in result.output
        assert "Path" in result.output
        assert "Runs" in result.output
        assert "Since" in result.output

        # Should show the project
        assert "Test Project" in result.output

    def test_projects_empty_list(self, temp_registry: Path) -> None:
        """Empty registry shows appropriate message."""
        result = runner.invoke(app, ["projects"])
        assert result.exit_code == 0
        assert "No projects registered" in result.output

    def test_projects_shows_run_count(
        self, temp_registry: Path, mock_cwd: Path
    ) -> None:
        """Projects command shows run count for each project."""
        runner.invoke(app, ["register", "--name", "Test Project"])

        result = runner.invoke(app, ["projects"])
        assert result.exit_code == 0
        # Should show "0" for run count since no runs exist
        assert "0" in result.output


class TestMultipleProjects:
    """Tests for managing multiple projects."""

    def test_register_multiple_projects(
        self, temp_registry: Path, tmp_path: Path
    ) -> None:
        """Multiple projects can be registered."""
        projects = []
        for i in range(3):
            project = tmp_path / f"project-{i}"
            project.mkdir()
            (project / ".adw").mkdir()
            projects.append(project)

        # Register each project
        for i, project in enumerate(projects):
            with patch("adw.cli.register.Path.cwd", return_value=project):
                result = runner.invoke(app, ["register", "--name", f"Project {i}"])
                assert result.exit_code == 0

        # Verify all projects listed
        result = runner.invoke(app, ["projects"])
        assert result.exit_code == 0

        assert "Project 0" in result.output
        assert "Project 1" in result.output
        assert "Project 2" in result.output

    def test_register_same_project_twice_updates(
        self, temp_registry: Path, mock_cwd: Path
    ) -> None:
        """Registering same project twice updates the name."""
        runner.invoke(app, ["register", "--name", "Original Name"])
        runner.invoke(app, ["register", "--name", "Updated Name"])

        result = runner.invoke(app, ["projects"])

        # Should only have one entry with updated name
        assert "Updated Name" in result.output
        # Original name should be replaced
        assert "Original Name" not in result.output


class TestRegisterWithDefaultName:
    """Tests for register command default naming."""

    def test_register_uses_directory_name_as_default(
        self, temp_registry: Path, mock_cwd: Path
    ) -> None:
        """Register uses directory name when no name provided."""
        result = runner.invoke(app, ["register"])
        assert result.exit_code == 0

        # Should use directory name "my-project" from the fixture
        result = runner.invoke(app, ["projects"])
        assert "my-project" in result.output
