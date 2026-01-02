"""Unit tests for CLI run command.

Tests for the `adw run FEATURE_DESCRIPTION` command including:
- Argument parsing
- Flag handling (--verbose, --dry-run)
- Empty feature description validation
"""

from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


class TestRunCommand:
    """Tests for the run command."""

    def test_run_requires_feature_description(self) -> None:
        """Test that run command requires feature description argument."""
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "FEATURE_DESCRIPTION" in result.output

    def test_run_accepts_feature_description(self) -> None:
        """Test that run command accepts feature description with --dry-run."""
        result = runner.invoke(app, ["run", "Add user auth", "--dry-run"])
        assert result.exit_code == 0
        assert "Add user auth" in result.output

    def test_run_rejects_empty_description(self) -> None:
        """Test that empty feature description is rejected."""
        result = runner.invoke(app, ["run", "   ", "--dry-run"])
        assert result.exit_code == 1
        assert "empty" in result.output.lower()

    def test_run_accepts_verbose_flag(self) -> None:
        """Test that --verbose/-v flag is accepted."""
        result = runner.invoke(app, ["run", "Add feature", "--verbose", "--dry-run"])
        assert result.exit_code == 0

        # Also test short form
        result = runner.invoke(app, ["run", "Add feature", "-v", "--dry-run"])
        assert result.exit_code == 0

    def test_run_dry_run_shows_message(self) -> None:
        """Test that --dry-run shows appropriate message."""
        result = runner.invoke(app, ["run", "Add feature", "--dry-run"])
        assert result.exit_code == 0
        assert "dry run" in result.output.lower() or "Dry run" in result.output

    def test_run_displays_run_header(self) -> None:
        """Test that run command displays run header with run ID."""
        result = runner.invoke(app, ["run", "Add user authentication", "--dry-run"])
        assert result.exit_code == 0
        # Header should contain key elements (UX-12)
        assert "Run ID" in result.output or "run_id" in result.output.lower()

    def test_run_with_special_characters(self) -> None:
        """Test that feature description with special characters is handled."""
        result = runner.invoke(app, ["run", 'Add "quoted" feature', "--dry-run"])
        assert result.exit_code == 0
        # The special characters should be present in output
        assert "quoted" in result.output
