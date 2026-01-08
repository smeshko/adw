"""Tests for run command task manager flags.

Story 12.4: Task ID Pattern Detection - CLI flag tests.
"""

from typer.testing import CliRunner

from adw.cli.app import app

runner = CliRunner()


class TestRunCommandFlags:
    """Test --task-id and --no-task-manager flags."""

    def test_task_id_flag_error_with_null_task_manager(self) -> None:
        """--task-id flag errors when NullTaskManager can't resolve ID.

        NullTaskManager always returns None from resolve_task_id,
        so --task-id will always error until a real task manager is configured.
        """
        result = runner.invoke(app, ["run", "RULE-123", "--task-id", "--dry-run"])
        # NullTaskManager doesn't resolve any IDs, so this correctly errors
        assert result.exit_code == 1
        assert "does not match task ID pattern" in result.output

    def test_no_task_manager_flag_accepted(self) -> None:
        """--no-task-manager flag is accepted and skips task manager resolution."""
        result = runner.invoke(
            app, ["run", "RULE-123", "--no-task-manager", "--dry-run"]
        )
        # Should proceed past resolution (may still fail on other things like no config)
        # The key is it should NOT error on task ID resolution
        assert "does not match task ID pattern" not in result.output

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


class TestAmbiguityHandling:
    """Test ambiguity handling in task ID detection."""

    def test_force_task_id_error_suggests_removal(self) -> None:
        """--task-id error suggests removing the flag."""
        result = runner.invoke(app, ["run", "RULE-123", "--task-id"])
        assert result.exit_code == 1
        assert "Remove --task-id" in result.output

    def test_no_task_manager_bypasses_resolution(self) -> None:
        """--no-task-manager skips task ID resolution entirely."""
        result = runner.invoke(
            app, ["run", "Add user auth", "--no-task-manager", "--dry-run"]
        )
        # Should not mention task ID resolution at all
        assert "Resolved as task ID" not in result.output
        assert "does not match task ID pattern" not in result.output


class TestTaskIdFlagVariants:
    """Additional tests for --task-id flag behavior."""

    def test_task_id_with_feature_like_input(self) -> None:
        """--task-id with feature-like input shows appropriate error."""
        result = runner.invoke(
            app, ["run", "Add user authentication", "--task-id"]
        )
        assert result.exit_code == 1
        assert "does not match" in result.output


class TestNoTaskManagerFlagVariants:
    """Additional tests for --no-task-manager flag behavior."""

    def test_no_task_manager_with_task_like_input(self) -> None:
        """--no-task-manager treats task-like input as feature string."""
        result = runner.invoke(
            app, ["run", "PROJ-999", "--no-task-manager", "--dry-run"]
        )
        # Should proceed without task ID resolution
        assert "does not match task ID pattern" not in result.output


class TestIntegrationFlow:
    """Integration tests for full detection flow."""

    def test_auto_detect_feature_string(self) -> None:
        """Feature description auto-detected as feature string."""
        result = runner.invoke(
            app, ["run", "Add login page with OAuth", "--dry-run"]
        )
        # Should not mention task ID - NullTaskManager doesn't match anything
        assert "Resolved as task ID" not in result.output
        # Should proceed to dry-run output (or other expected output)
        # The key is no task ID resolution errors
        assert "does not match task ID pattern" not in result.output

    def test_full_flow_with_no_task_manager(self) -> None:
        """Full flow with --no-task-manager flag processes feature correctly."""
        result = runner.invoke(
            app, ["run", "Implement feature X", "--no-task-manager", "--dry-run"]
        )
        # Should skip task manager entirely and proceed to dry-run
        assert "does not match task ID pattern" not in result.output
        assert "Resolved as task ID" not in result.output
