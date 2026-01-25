"""Tests for CLI register command.

Tests for the `adw register [--name NAME]` command including:
- Registering current directory
- Custom name via --name option
- Validation that directory is an ADW project
- Update existing registration
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestRegisterCommand:
    """Tests for the register command."""

    def test_register_current_directory(self, tmp_path: Path) -> None:
        """Test registering the current directory."""
        # Create an ADW project directory
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / ".adw").mkdir()

        with (
            patch("adw.cli.register.Path.cwd", return_value=project_dir),
            patch("adw.cli.register.ProjectRegistryManager") as mock_manager_class,
        ):
            mock_manager = mock_manager_class.return_value
            mock_manager.register.return_value = _create_mock_project(
                str(project_dir), "my-project"
            )

            result = runner.invoke(app, ["register"])

        assert result.exit_code == 0
        assert "my-project" in result.output or "registered" in result.output.lower()

    def test_register_with_custom_name(self, tmp_path: Path) -> None:
        """Test registering with custom name via --name option."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / ".adw").mkdir()

        with (
            patch("adw.cli.register.Path.cwd", return_value=project_dir),
            patch("adw.cli.register.ProjectRegistryManager") as mock_manager_class,
        ):
            mock_manager = mock_manager_class.return_value
            mock_manager.register.return_value = _create_mock_project(
                str(project_dir), "My Awesome API"
            )

            result = runner.invoke(app, ["register", "--name", "My Awesome API"])

        assert result.exit_code == 0
        mock_manager.register.assert_called_once()
        # Verify name was passed
        call_args = mock_manager.register.call_args
        assert call_args[1].get("name") == "My Awesome API" or (
            len(call_args[0]) >= 2 and call_args[0][1] == "My Awesome API"
        )

    def test_register_requires_adw_project(self, tmp_path: Path) -> None:
        """Test that register requires .adw/ directory."""
        # Create a non-ADW directory
        project_dir = tmp_path / "not-adw-project"
        project_dir.mkdir()
        # Note: no .adw/ subdirectory

        with patch("adw.cli.register.Path.cwd", return_value=project_dir):
            result = runner.invoke(app, ["register"])

        # Should fail because it's not an ADW project
        assert result.exit_code != 0
        assert (
            "not an ADW project" in result.output.lower()
            or "adw init" in result.output.lower()
        )

    def test_register_updates_existing(self, tmp_path: Path) -> None:
        """Test that registering an already-registered project updates it."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / ".adw").mkdir()

        with (
            patch("adw.cli.register.Path.cwd", return_value=project_dir),
            patch("adw.cli.register.ProjectRegistryManager") as mock_manager_class,
        ):
            mock_manager = mock_manager_class.return_value
            # First call returns existing project
            mock_manager.get_by_path.return_value = _create_mock_project(
                str(project_dir), "old-name"
            )
            # register() updates and returns new project
            mock_manager.register.return_value = _create_mock_project(
                str(project_dir), "new-name"
            )

            result = runner.invoke(app, ["register", "--name", "new-name"])

        assert result.exit_code == 0
        # Should indicate update (not a failure)
        assert (
            "updated" in result.output.lower() or "registered" in result.output.lower()
        )


def _create_mock_project(path: str, name: str):
    """Create a mock RegisteredProject."""
    from datetime import UTC, datetime

    from adw.models.registry import RegisteredProject

    return RegisteredProject(
        path=path,
        name=name,
        registered_at=datetime.now(UTC),
    )
