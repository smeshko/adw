"""Integration tests for logs.jsonl creation and adw logs show command.

Tests the complete flow from Python logging through LogManager to file.
Verifies ISS-006 fix: LogManager connected to Python logging.
"""

import json
import logging
import tempfile
from pathlib import Path

import pytest

from adw.cli.bootstrap import create_log_manager
from adw.models.logging import LogCategory, Verbosity


class TestLogsJsonlCreation:
    """Integration tests for logs.jsonl file creation."""

    def test_python_logging_writes_to_logs_jsonl(self, tmp_path: Path) -> None:
        """Verify Python logging calls create entries in logs.jsonl."""
        # Arrange - Create a run directory with log manager
        run_dir = tmp_path / "runs" / "01TEST123"
        run_dir.mkdir(parents=True)

        log_manager = create_log_manager(
            verbosity=Verbosity.VERBOSE,
            run_dir=run_dir,
        )

        # Act - Log using Python's standard logging
        logger = logging.getLogger("adw.test.integration")
        logger.info("Test message from Python logging")
        logger.warning("Test warning message")
        logger.error("Test error message")

        # Assert - Check logs.jsonl was created with entries
        logs_file = run_dir / "logs" / "logs.jsonl"
        assert logs_file.exists(), f"logs.jsonl not created at {logs_file}"

        # Parse and verify log entries
        entries = []
        with open(logs_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        assert len(entries) >= 3, f"Expected at least 3 entries, got {len(entries)}"

        # Check entry structure
        for entry in entries:
            assert "timestamp" in entry
            assert "level" in entry
            assert "category" in entry
            assert "message" in entry
            assert "context" in entry

        # Clean up - remove handler to avoid affecting other tests
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if hasattr(handler, "_log_manager"):
                root_logger.removeHandler(handler)

    def test_log_levels_are_mapped_correctly(self, tmp_path: Path) -> None:
        """Verify Python log levels are correctly mapped to ADW levels."""
        # Arrange
        run_dir = tmp_path / "runs" / "01TEST456"
        run_dir.mkdir(parents=True)

        create_log_manager(
            verbosity=Verbosity.VERBOSE,
            run_dir=run_dir,
        )

        # Act - Log at different levels
        logger = logging.getLogger("adw.test.levels")
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Assert - Verify levels in file
        logs_file = run_dir / "logs" / "logs.jsonl"
        entries = []
        with open(logs_file) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))

        levels_found = {e["level"] for e in entries}

        # At VERBOSE, we should see debug and above
        assert "debug" in levels_found or "info" in levels_found
        assert "warn" in levels_found
        assert "error" in levels_found

        # Clean up
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if hasattr(handler, "_log_manager"):
                root_logger.removeHandler(handler)

    def test_log_category_is_inferred_from_logger_name(self, tmp_path: Path) -> None:
        """Verify logger names are mapped to appropriate categories."""
        # Arrange
        run_dir = tmp_path / "runs" / "01TEST789"
        run_dir.mkdir(parents=True)

        create_log_manager(
            verbosity=Verbosity.VERBOSE,
            run_dir=run_dir,
        )

        # Act - Log from different module names
        logging.getLogger("adw.executors.claude").info("LLM message")
        logging.getLogger("adw.hooks.runner").info("Hook message")
        logging.getLogger("adw.core.orchestrator").info("Phase message")

        # Assert
        logs_file = run_dir / "logs" / "logs.jsonl"
        entries = []
        with open(logs_file) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))

        categories = {e["category"] for e in entries}

        # Should have mapped categories
        assert "llm" in categories  # From executor
        assert "hook" in categories  # From hooks
        assert "phase" in categories  # Default/orchestrator

        # Clean up
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if hasattr(handler, "_log_manager"):
                root_logger.removeHandler(handler)

    def test_raw_log_also_created(self, tmp_path: Path) -> None:
        """Verify raw.log is created alongside logs.jsonl."""
        # Arrange
        run_dir = tmp_path / "runs" / "01TESTABC"
        run_dir.mkdir(parents=True)

        create_log_manager(
            verbosity=Verbosity.NORMAL,
            run_dir=run_dir,
        )

        # Act
        logger = logging.getLogger("adw.test.raw")
        logger.info("Test message for raw log")

        # Assert
        raw_log = run_dir / "logs" / "raw.log"
        assert raw_log.exists(), "raw.log should be created"

        content = raw_log.read_text()
        assert "Test message for raw log" in content

        # Clean up
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if hasattr(handler, "_log_manager"):
                root_logger.removeHandler(handler)

    def test_context_is_preserved_in_log_entries(self, tmp_path: Path) -> None:
        """Verify context from LogManager child is included in entries."""
        # Arrange
        run_dir = tmp_path / "runs" / "01TESTCTX"
        run_dir.mkdir(parents=True)

        log_manager = create_log_manager(
            verbosity=Verbosity.VERBOSE,
            run_dir=run_dir,
        )

        # Create child logger with context
        child_manager = log_manager.child(run_id="01TESTRUN", phase="build")

        # Log directly through LogManager (which does have context)
        child_manager.info(LogCategory.PHASE, "Message with context")

        # Assert
        logs_file = run_dir / "logs" / "logs.jsonl"
        entries = []
        with open(logs_file) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))

        # Find our entry
        context_entries = [
            e for e in entries if "context" in e and e["context"].get("run_id")
        ]
        assert len(context_entries) >= 1

        entry = context_entries[0]
        assert entry["context"]["run_id"] == "01TESTRUN"
        assert entry["context"]["phase"] == "build"

        # Clean up
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if hasattr(handler, "_log_manager"):
                root_logger.removeHandler(handler)
