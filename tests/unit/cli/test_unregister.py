"""Tests for CLI unregister command.

Tests for the `adw unregister` command including:
- Unregistering current directory
- Not registered case
- Success message display
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


class TestUnregisterCommand:
    """Tests for the unregister command."""

    def test_unregister_current_directory(self, tmp_path: Path) -> None:
        """Test unregistering the current directory."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / ".adw").mkdir()

        with (
            patch("adw.cli.unregister.Path.cwd", return_value=project_dir),
            patch("adw.cli.unregister.ProjectRegistryManager") as mock_manager_class,
        ):
            mock_manager = mock_manager_class.return_value
            mock_manager.unregister.return_value = True

            result = runner.invoke(app, ["unregister"])

        assert result.exit_code == 0
        assert (
            "unregistered" in result.output.lower()
            or "removed" in result.output.lower()
        )

    def test_unregister_not_registered(self, tmp_path: Path) -> None:
        """Test unregistering a project that isn't registered."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / ".adw").mkdir()

        with (
            patch("adw.cli.unregister.Path.cwd", return_value=project_dir),
            patch("adw.cli.unregister.ProjectRegistryManager") as mock_manager_class,
        ):
            mock_manager = mock_manager_class.return_value
            mock_manager.unregister.return_value = False

            result = runner.invoke(app, ["unregister"])

        # Should succeed but show "not registered" message
        assert result.exit_code == 0
        assert "not registered" in result.output.lower()

    def test_unregister_requires_adw_project(self, tmp_path: Path) -> None:
        """Test that unregister requires .adw/ directory."""
        project_dir = tmp_path / "not-adw-project"
        project_dir.mkdir()
        # Note: no .adw/ subdirectory

        with patch("adw.cli.unregister.Path.cwd", return_value=project_dir):
            result = runner.invoke(app, ["unregister"])

        # Should fail because it's not an ADW project
        assert result.exit_code != 0
        assert (
            "not an ADW project" in result.output.lower()
            or "adw init" in result.output.lower()
        )
