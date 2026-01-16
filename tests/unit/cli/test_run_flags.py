"""Tests for run command task manager flags.

Story 12.4: Task ID Pattern Detection - CLI flag tests.
"""

from unittest.mock import Mock, patch

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
        result = runner.invoke(app, ["run", "Add user authentication", "--task-id"])
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
        result = runner.invoke(app, ["run", "Add login page with OAuth", "--dry-run"])
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


class TestTaskIdSuccessPath:
    """Test successful task ID detection with mocked task manager."""

    def test_successful_task_id_detection(self) -> None:
        """When task manager resolves ID, CLI shows 'Resolved as task ID' message."""
        # Create a mock task manager that recognizes RULE-123
        mock_manager = Mock()
        mock_manager.resolve_task_id.return_value = "RULE-123"
        mock_manager.name = "mock"

        # Patch the factory to return our mock manager
        with patch("adw.cli.app.TaskManagerFactory") as mock_factory_cls:
            mock_factory = Mock()
            mock_factory.create.return_value = mock_manager
            mock_factory_cls.return_value = mock_factory

            result = runner.invoke(app, ["run", "RULE-123", "--dry-run"])

            # Should show task ID was resolved (transparency logging)
            assert "Resolved as task ID" in result.output
            assert "RULE-123" in result.output
            # Should also show the tip about --no-task-manager
            assert "--no-task-manager" in result.output

    def test_task_id_flag_with_matching_manager(self) -> None:
        """--task-id succeeds when task manager recognizes the ID."""
        mock_manager = Mock()
        mock_manager.resolve_task_id.return_value = "PROJ-456"
        mock_manager.name = "mock"

        with patch("adw.cli.app.TaskManagerFactory") as mock_factory_cls:
            mock_factory = Mock()
            mock_factory.create.return_value = mock_manager
            mock_factory_cls.return_value = mock_factory

            result = runner.invoke(app, ["run", "PROJ-456", "--task-id", "--dry-run"])

            # Should succeed without error
            assert "does not match task ID pattern" not in result.output
            assert "Resolved as task ID" in result.output
            # --task-id was explicit, so no tip needed
            assert result.exit_code != 1 or "mutually exclusive" not in result.output

    def test_normalized_task_id_displayed(self) -> None:
        """When task manager normalizes ID (e.g., lowercase to uppercase), normalized form is shown."""
        mock_manager = Mock()
        # Manager normalizes to uppercase
        mock_manager.resolve_task_id.return_value = "RULE-123"
        mock_manager.name = "mock"

        with patch("adw.cli.app.TaskManagerFactory") as mock_factory_cls:
            mock_factory = Mock()
            mock_factory.create.return_value = mock_manager
            mock_factory_cls.return_value = mock_factory

            result = runner.invoke(app, ["run", "rule-123", "--dry-run"])

            # Should show normalized (uppercase) task ID
            assert "RULE-123" in result.output
            assert "Resolved as task ID" in result.output
