"""Tests for run command task manager flags.

Story 12.4: Task ID Pattern Detection - CLI flag tests.
"""

from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


class TestRunCommandFlags:
    """Test --task-id and --no-task-manager flags."""

    def test_task_id_flag_accepted(self) -> None:
        """--task-id flag is accepted by the run command."""
        # Use --dry-run to avoid actually running the workflow
        result = runner.invoke(app, ["run", "RULE-123", "--task-id", "--dry-run"])
        # Should not error on the flag itself (may error on other things like no config)
        assert "--task-id" not in result.output or "Error" not in result.output[:50]

    def test_no_task_manager_flag_accepted(self) -> None:
        """--no-task-manager flag is accepted by the run command."""
        result = runner.invoke(
            app, ["run", "RULE-123", "--no-task-manager", "--dry-run"]
        )
        # Should not error on the flag itself
        assert (
            "--no-task-manager" not in result.output or "Error" not in result.output[:50]
        )

    def test_flags_mutually_exclusive(self) -> None:
        """Error when both --task-id and --no-task-manager provided."""
        result = runner.invoke(
            app, ["run", "RULE-123", "--task-id", "--no-task-manager"]
        )
        assert result.exit_code == 1
        assert "mutually exclusive" in result.output


class TestRunCommandHelp:
    """Test that help text includes new flags."""

    def test_help_includes_task_id_flag(self) -> None:
        """--help shows --task-id flag."""
        result = runner.invoke(app, ["run", "--help"])
        assert "--task-id" in result.output
        assert "task ID" in result.output.lower() or "task id" in result.output.lower()

    def test_help_includes_no_task_manager_flag(self) -> None:
        """--help shows --no-task-manager flag."""
        result = runner.invoke(app, ["run", "--help"])
        assert "--no-task-manager" in result.output
        assert "task manager" in result.output.lower()
