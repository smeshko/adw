"""Unit tests for global commands CLI.

Tests for the `adw global` command group which provides cross-project
run listing, filtering, and statistics.
"""

from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


class TestGlobalCommandGroup:
    """Tests for the global command group registration."""

    def test_global_help_shows_command_group(self) -> None:
        """The global command group should be registered and show help."""
        result = runner.invoke(app, ["global", "--help"])
        assert result.exit_code == 0
        assert "Cross-project commands" in result.output

    def test_global_list_command_exists(self) -> None:
        """The global list command should be registered."""
        result = runner.invoke(app, ["global", "list", "--help"])
        assert result.exit_code == 0
        assert "List runs across all projects" in result.output
