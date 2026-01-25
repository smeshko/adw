"""Tests for CLI projects command.

Tests for the `adw projects` command including:
- Listing registered projects
- Empty registry handling
- --discover flag for auto-discovery
- --json flag for machine output
- Run count display
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestProjectsCommand:
    """Tests for the projects command."""

    def test_list_registered_projects(self, tmp_path: Path) -> None:
        """Test listing registered projects in a table."""
        with patch(
            "adw.cli.projects.ProjectRegistryManager"
        ) as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.get_all.return_value = [
                _create_mock_project("/Users/dev/project-a", "project-a"),
                _create_mock_project("/Users/dev/project-b", "My API"),
            ]

            # Mock IndexManager for run counts
            with patch("adw.cli.projects.IndexManager") as mock_index_class:
                mock_index = mock_index_class.return_value
                mock_index.get_recent_runs.return_value = []

                result = runner.invoke(app, ["projects"])

        assert result.exit_code == 0
        # Should show project names in output
        assert "project-a" in result.output or "My API" in result.output

    def test_list_empty_registry(self) -> None:
        """Test message when no projects are registered."""
        with patch(
            "adw.cli.projects.ProjectRegistryManager"
        ) as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.get_all.return_value = []

            result = runner.invoke(app, ["projects"])

        assert result.exit_code == 0
        assert "no projects registered" in result.output.lower() or "empty" in result.output.lower()

    def test_discover_flag(self) -> None:
        """Test --discover flag shows projects from index."""
        with patch(
            "adw.cli.projects.ProjectRegistryManager"
        ) as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.discover_from_index.return_value = [
                _create_mock_project("/Users/dev/discovered-1", "discovered-1"),
                _create_mock_project("/Users/dev/discovered-2", "discovered-2"),
            ]

            # Mock IndexManager for run counts
            with patch("adw.cli.projects.IndexManager") as mock_index_class:
                mock_index = mock_index_class.return_value
                mock_index.get_recent_runs.return_value = []

                result = runner.invoke(app, ["projects", "--discover"])

        assert result.exit_code == 0
        # Should show discovered in output
        assert "discovered" in result.output.lower()

    def test_json_output(self) -> None:
        """Test --json flag outputs JSON format."""
        import json

        with patch(
            "adw.cli.projects.ProjectRegistryManager"
        ) as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.get_all.return_value = [
                _create_mock_project("/Users/dev/project-a", "project-a"),
            ]

            # Mock IndexManager for run counts
            with patch("adw.cli.projects.IndexManager") as mock_index_class:
                mock_index = mock_index_class.return_value
                mock_index.get_recent_runs.return_value = []

                result = runner.invoke(app, ["projects", "--json"])

        assert result.exit_code == 0
        # Should be valid JSON
        try:
            data = json.loads(result.output)
            assert "projects" in data
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")


def _create_mock_project(path: str, name: str):
    """Create a mock RegisteredProject."""
    from datetime import UTC, datetime

    from adw.models.registry import RegisteredProject

    return RegisteredProject(
        path=path,
        name=name,
        registered_at=datetime.now(UTC),
    )
