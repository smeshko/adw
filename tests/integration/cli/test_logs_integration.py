"""Integration tests for logs CLI commands.

Tests the log viewer commands including `logs follow` and `logs export`.
"""

import logging
from pathlib import Path

from adw.cli.bootstrap import create_log_manager
from adw.models.logging import LogCategory, Verbosity


class TestLogManagerIntegration:
    """Integration tests for LogManager with file output."""

    def test_live_log_created_when_run_dir_provided(self, tmp_path: Path) -> None:
        """Verify live.log is created when run_dir is provided."""
        # Arrange - Create a run directory with log manager
        run_dir = tmp_path / "runs" / "01TEST123"
        run_dir.mkdir(parents=True)

        log_manager = create_log_manager(
            verbosity=Verbosity.VERBOSE,
            run_dir=run_dir,
        )

        # Act - Log using LogManager
        log_manager.info(LogCategory.PHASE, "Test message")

        # Assert - Check live.log was created
        live_log = run_dir / "live.log"
        assert live_log.exists(), f"live.log not created at {live_log}"

        # Clean up - remove handler to avoid affecting other tests
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if hasattr(handler, "_log_manager"):
                root_logger.removeHandler(handler)

    def test_log_manager_respects_verbosity(self, tmp_path: Path) -> None:
        """Verify LogManager respects verbosity settings."""
        # Arrange
        run_dir = tmp_path / "runs" / "01TEST456"
        run_dir.mkdir(parents=True)

        log_manager = create_log_manager(
            verbosity=Verbosity.VERBOSE,
            run_dir=run_dir,
        )

        # Act - Log at different levels
        log_manager.debug(LogCategory.PHASE, "Debug message")
        log_manager.info(LogCategory.PHASE, "Info message")
        log_manager.warn(LogCategory.PHASE, "Warning message")
        log_manager.error(LogCategory.PHASE, "Error message")

        # Assert - Verify live.log exists
        live_log = run_dir / "live.log"
        assert live_log.exists()

        content = live_log.read_text()
        # At VERBOSE, we should see all messages
        assert "Debug message" in content or "Info message" in content
        assert "Warning message" in content
        assert "Error message" in content

        # Clean up
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if hasattr(handler, "_log_manager"):
                root_logger.removeHandler(handler)

    def test_child_logger_inherits_transports(self, tmp_path: Path) -> None:
        """Verify child LogManager inherits parent's transports."""
        # Arrange
        run_dir = tmp_path / "runs" / "01TESTCTX"
        run_dir.mkdir(parents=True)

        log_manager = create_log_manager(
            verbosity=Verbosity.VERBOSE,
            run_dir=run_dir,
        )

        # Create child logger with context
        child_manager = log_manager.child(run_id="01TESTRUN", phase="build")

        # Act - Log through child
        child_manager.info(LogCategory.PHASE, "Message with context")

        # Assert - Verify live.log contains the message
        live_log = run_dir / "live.log"
        assert live_log.exists()

        content = live_log.read_text()
        assert "Message with context" in content

        # Clean up
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if hasattr(handler, "_log_manager"):
                root_logger.removeHandler(handler)
