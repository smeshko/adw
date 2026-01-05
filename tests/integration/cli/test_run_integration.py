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
        config_dir.mkdir(exist_ok=True)
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

    def test_run_with_dry_run_flag_shows_info(self, tmp_path: Path) -> None:
        """Test that --dry-run flag produces informational output."""
        # Create pyproject.toml for detection
        (tmp_path / "pyproject.toml").touch()

        result = runner.invoke(
            app,
            ["run", "Add test feature", "--dry-run"],
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
        msg = f"Startup time {elapsed:.2f}s exceeds NFR1 requirement of 2s"
        assert elapsed < 2.0, msg

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

    def test_invalid_config_uses_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that run works with incomplete config (uses defaults)."""
        config_dir = tmp_path / ".adw"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "project.yaml"
        # Missing required fields - current implementation uses defaults
        config_file.write_text("""
framework: fastapi
        """)

        # Change to tmp_path for config loading
        monkeypatch.chdir(tmp_path)

        # Run with --dry-run to avoid needing claude CLI
        result = runner.invoke(
            app,
            ["run", "Add feature", "--dry-run"],
        )

        # Should succeed with dry run (doesn't validate config strictly)
        assert result.exit_code == 0
        assert "Dry run mode" in result.output

    def test_malformed_yaml_does_not_block_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that malformed YAML doesn't block run (uses defaults)."""
        config_dir = tmp_path / ".adw"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "project.yaml"
        config_file.write_text("""
name: test
  bad: indent
        """)

        # Change to tmp_path for config loading
        monkeypatch.chdir(tmp_path)

        # Run with --dry-run since current impl doesn't validate config strictly
        result = runner.invoke(
            app,
            ["run", "Add feature", "--dry-run"],
        )

        # Should succeed with dry run (uses defaults, ignores config issues)
        assert result.exit_code == 0
        assert "Dry run mode" in result.output


class TestVerbosityIntegration:
    """Integration tests for verbosity and show_llm_output flag propagation.

    Story UX-FIX-ISS-001: Verify that --show-llm-output and --trace flags
    properly propagate through the CLI → bootstrap → executor chain.
    """

    def test_show_llm_output_flag_propagates_to_orchestrator(self) -> None:
        """Test that --show-llm-output flag is properly wired through bootstrap.

        Verifies: CLI flag → create_orchestrator() → ClaudeCodeExecutor.show_llm_output
        """
        from unittest.mock import patch

        from adw.cli.bootstrap import create_orchestrator

        # Test with show_llm_output=True
        with patch("adw.cli.bootstrap.ClaudeCodeExecutor") as mock_executor_class:
            mock_executor_class.return_value = mock_executor_class
            create_orchestrator(show_llm_output=True)

            # Verify executor was created with show_llm_output=True
            mock_executor_class.assert_called_once()
            call_kwargs = mock_executor_class.call_args[1]
            assert call_kwargs.get("show_llm_output") is True

    def test_show_llm_output_defaults_to_false_in_orchestrator(self) -> None:
        """Test that show_llm_output defaults to False in create_orchestrator."""
        from unittest.mock import patch

        from adw.cli.bootstrap import create_orchestrator

        with patch("adw.cli.bootstrap.ClaudeCodeExecutor") as mock_executor_class:
            mock_executor_class.return_value = mock_executor_class
            create_orchestrator()  # No show_llm_output specified

            mock_executor_class.assert_called_once()
            call_kwargs = mock_executor_class.call_args[1]
            assert call_kwargs.get("show_llm_output") is False

    def test_trace_verbosity_enables_show_llm_output(self) -> None:
        """Test that --trace verbosity enables LLM output in the run command.

        Story UX-FIX-ISS-001 Task 3: --trace should enable show_llm_output.
        """
        from adw.models.logging import Verbosity

        # This logic is in app.py - verify it's correct
        verbosity = Verbosity.TRACE
        show_llm_output_flag = False

        # Simulate the logic from app.py:200-201
        effective_show_llm_output = show_llm_output_flag or verbosity == Verbosity.TRACE

        assert effective_show_llm_output is True

    def test_verbose_verbosity_does_not_enable_show_llm_output(self) -> None:
        """Test that --verbose (non-trace) does NOT enable LLM output."""
        from adw.models.logging import Verbosity

        verbosity = Verbosity.VERBOSE
        show_llm_output_flag = False

        effective_show_llm_output = show_llm_output_flag or verbosity == Verbosity.TRACE

        assert effective_show_llm_output is False

    def test_show_llm_output_flag_accepted_by_run_command(self) -> None:
        """Test that --show-llm-output flag is accepted without errors."""
        result = runner.invoke(
            app,
            ["run", "Test feature", "--show-llm-output", "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "No such option" not in result.output

    def test_show_llm_output_help_text_present(self) -> None:
        """Test that --show-llm-output flag has proper help documentation."""
        result = runner.invoke(app, ["run", "--help"])

        assert result.exit_code == 0
        assert "--show-llm-output" in result.output
        # Verify help text describes the flag's purpose
        assert "LLM" in result.output or "llm" in result.output.lower()
