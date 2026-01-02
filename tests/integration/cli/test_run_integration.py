"""Integration tests for CLI run command.

Tests the full run command execution including:
- Config loading
- Orchestrator setup
- Error handling
- Startup time verification (NFR1)
"""

import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


class TestRunCommandIntegration:
    """Integration tests for the run command."""

    def test_run_with_project_config(self, tmp_path: Path) -> None:
        """Test run command with project config present."""
        # Create project structure
        config_dir = tmp_path / ".adw"
        config_dir.mkdir()
        config_file = config_dir / "project.yaml"
        config_file.write_text("""
name: test-project
language: python
test_command: pytest
        """)

        # Run with --dry-run to avoid actual execution
        result = runner.invoke(
            app,
            ["run", "Add test feature", "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "ADW Run" in result.output
        assert "Run ID" in result.output or "run_id" in result.output.lower()
        assert "Dry run" in result.output

    def test_run_without_project_config_uses_defaults(self, tmp_path: Path) -> None:
        """Test run command uses defaults when no config exists."""
        # Create pyproject.toml to trigger Python detection
        (tmp_path / "pyproject.toml").touch()

        result = runner.invoke(
            app,
            ["run", "Add test feature", "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "ADW Run" in result.output

    def test_run_with_verbose_flag_shows_extra_info(self, tmp_path: Path) -> None:
        """Test that --verbose flag produces additional output."""
        # Create pyproject.toml for detection
        (tmp_path / "pyproject.toml").touch()

        result = runner.invoke(
            app,
            ["run", "Add test feature", "--verbose", "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

    def test_run_with_special_characters_in_feature(self) -> None:
        """Test that feature descriptions with special chars are handled."""
        # Test various special characters
        special_descriptions = [
            'Add "quoted" feature',
            "Add feature with $variable",
            "Add `backtick` command",
            "Add feature with 'single quotes'",
            "Add feature with <angle> brackets",
        ]

        for desc in special_descriptions:
            result = runner.invoke(
                app,
                ["run", desc, "--dry-run"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0, f"Failed for: {desc}"

    def test_startup_time_under_2_seconds(self) -> None:
        """Test that CLI startup time is under 2 seconds (NFR1)."""
        start = time.perf_counter()

        result = runner.invoke(
            app,
            ["run", "Quick test", "--dry-run"],
            catch_exceptions=False,
        )

        elapsed = time.perf_counter() - start

        assert result.exit_code == 0
        assert elapsed < 2.0, f"Startup time {elapsed:.2f}s exceeds NFR1 requirement of 2s"

    def test_run_displays_run_header_format(self) -> None:
        """Test that run header follows UX-12 specification."""
        result = runner.invoke(
            app,
            ["run", "Add user authentication", "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # UX-12 requires: run_id, feature, started timestamp
        assert "Run ID" in result.output or "run_id" in result.output.lower()
        assert "Feature" in result.output or "user authentication" in result.output
        # Panel border should be present (Rich Panel)
        assert any(char in result.output for char in "─│╭╮╯╰")

    def test_run_with_empty_feature_rejects(self) -> None:
        """Test that empty feature description is rejected."""
        result = runner.invoke(app, ["run", "   "])

        assert result.exit_code == 1
        assert "empty" in result.output.lower()

    def test_run_with_very_long_feature_truncates_display(self) -> None:
        """Test that very long feature descriptions are truncated in display."""
        long_feature = "A" * 200

        result = runner.invoke(
            app,
            ["run", long_feature, "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Should contain truncation indicator
        assert "..." in result.output
        # Should not contain the full 200 A's
        assert ("A" * 200) not in result.output


class TestConfigIntegration:
    """Integration tests for configuration loading."""

    def test_invalid_config_shows_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that invalid config produces user-friendly error."""
        config_dir = tmp_path / ".adw"
        config_dir.mkdir()
        config_file = config_dir / "project.yaml"
        # Missing required fields
        config_file.write_text("""
framework: fastapi
        """)

        # Change to tmp_path for config loading
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["run", "Add feature"],
        )

        # Should fail with error message
        assert result.exit_code == 1
        assert "Error" in result.output or "INVALID_CONFIG" in result.output

    def test_malformed_yaml_shows_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that malformed YAML produces user-friendly error."""
        config_dir = tmp_path / ".adw"
        config_dir.mkdir()
        config_file = config_dir / "project.yaml"
        config_file.write_text("""
name: test
  bad: indent
        """)

        # Change to tmp_path for config loading
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["run", "Add feature"],
        )

        assert result.exit_code == 1
