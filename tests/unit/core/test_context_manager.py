"""Tests for ContextManager with atomic writes and durability.

This module tests the ContextManager class which handles atomic saves and loads
of RunContext with fsync, temp file pattern, and lock integration.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import filelock
import pytest

from adw.core.context_manager import ContextManager
from adw.exceptions import StateError
from adw.models import RunContext


@pytest.fixture
def sample_context() -> RunContext:
    """Create a sample RunContext for testing."""
    # Valid ULID (Crockford's Base32: 0123456789ABCDEFGHJKMNPQRSTVWXYZ - no I, L, O, U)
    return RunContext(
        run_id="01HQXYZ123456789ABCDEFGHJK",
        feature_description="Test feature",
        current_phase="plan",
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Create a runs directory for testing."""
    runs = tmp_path / ".adw" / "runs"
    runs.mkdir(parents=True)
    return runs


@pytest.fixture
def context_manager(runs_dir: Path) -> ContextManager:
    """Create a ContextManager instance for testing."""
    return ContextManager(runs_dir)


class TestContextManagerSave:
    """Tests for ContextManager.save() method."""

    def test_save_creates_context_file(
        self, context_manager: ContextManager, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test that save creates context.json file."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        # Create lock file
        (run_dir / ".lock").touch()

        context_manager.save(sample_context)

        context_path = run_dir / "context.json"
        assert context_path.exists()

    def test_save_uses_temp_file_pattern(
        self, context_manager: ContextManager, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test that save uses temp file + rename pattern for atomicity."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        # Track rename calls
        original_rename = Path.rename
        rename_calls: list[tuple[Path, Path]] = []

        def tracked_rename(self: Path, target: Path) -> None:
            rename_calls.append((self, target))
            return original_rename(self, target)

        with patch.object(Path, "rename", tracked_rename):
            context_manager.save(sample_context)

        # Should have called rename (atomic)
        assert len(rename_calls) == 1
        assert rename_calls[0][0].name == ".context.json.tmp"
        assert rename_calls[0][1].name == "context.json"

    def test_save_calls_fsync(
        self, context_manager: ContextManager, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test that save calls fsync for durability."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        fsync_calls: list[int] = []
        original_fsync = os.fsync

        def tracked_fsync(fd: int) -> None:
            fsync_calls.append(fd)
            return original_fsync(fd)

        with patch("os.fsync", tracked_fsync):
            context_manager.save(sample_context)

        assert len(fsync_calls) == 1

    def test_save_content_is_valid_json(
        self, context_manager: ContextManager, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test that saved content is valid JSON."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        context_manager.save(sample_context)

        context_path = run_dir / "context.json"
        content = context_path.read_text()
        data = json.loads(content)
        assert data["run_id"] == sample_context.run_id
        assert data["feature_description"] == sample_context.feature_description

    def test_save_cleans_up_temp_on_error(
        self, context_manager: ContextManager, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test that temp file is cleaned up on write error."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        # Patch os.fsync to raise an error after file is written
        def failing_fsync(fd: int) -> None:
            raise OSError("Disk full")

        with patch("adw.core.context_manager.os.fsync", failing_fsync):
            with pytest.raises(StateError) as exc_info:
                context_manager.save(sample_context)

        assert exc_info.value.code == "CONTEXT_WRITE_FAILED"
        # Temp file should be cleaned up
        temp_path = run_dir / ".context.json.tmp"
        assert not temp_path.exists()


class TestContextManagerLoad:
    """Tests for ContextManager.load() method."""

    def test_load_returns_valid_context(
        self, context_manager: ContextManager, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test that load returns a valid RunContext."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        # Save first
        context_manager.save(sample_context)

        # Then load
        loaded = context_manager.load(sample_context.run_id)

        assert loaded.run_id == sample_context.run_id
        assert loaded.feature_description == sample_context.feature_description
        assert loaded.current_phase == sample_context.current_phase

    def test_load_missing_file_raises_error(
        self, context_manager: ContextManager, runs_dir: Path
    ) -> None:
        """Test that loading non-existent context raises CONTEXT_NOT_FOUND."""
        # Using valid ULID format (directory name doesn't need ULID validation)
        run_id = "01HQXYZ1234567890BCDEFGHM"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        with pytest.raises(StateError) as exc_info:
            context_manager.load(run_id)

        assert exc_info.value.code == "CONTEXT_NOT_FOUND"

    def test_load_corrupted_json_raises_error(
        self, context_manager: ContextManager, runs_dir: Path
    ) -> None:
        """Test that corrupted JSON raises CONTEXT_CORRUPTED."""
        run_id = "01HQXYZ1234567890BCDEFGHN"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()
        (run_dir / "context.json").write_text("not valid json {{{")

        with pytest.raises(StateError) as exc_info:
            context_manager.load(run_id)

        assert exc_info.value.code == "CONTEXT_CORRUPTED"
        assert "snapshots" in exc_info.value.suggestion

    def test_load_invalid_schema_raises_error(
        self, context_manager: ContextManager, runs_dir: Path
    ) -> None:
        """Test that invalid schema raises CONTEXT_CORRUPTED."""
        run_id = "01HQXYZ1234567890BCDEFGHP"
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()
        # Valid JSON but missing required fields
        (run_dir / "context.json").write_text('{"run_id": "01HQXYZ1234567890BCDEFGHP"}')

        with pytest.raises(StateError) as exc_info:
            context_manager.load(run_id)

        assert exc_info.value.code == "CONTEXT_CORRUPTED"


class TestContextManagerLocking:
    """Tests for lock integration in ContextManager."""

    def test_save_acquires_lock(
        self, context_manager: ContextManager, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test that save acquires lock before writing."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        lock_acquired = False
        original_enter = filelock.FileLock.__enter__

        def tracked_enter(self: filelock.FileLock) -> filelock.FileLock:
            nonlocal lock_acquired
            lock_acquired = True
            return original_enter(self)

        with patch.object(filelock.FileLock, "__enter__", tracked_enter):
            context_manager.save(sample_context)

        assert lock_acquired

    def test_load_acquires_lock(
        self, context_manager: ContextManager, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test that load acquires lock before reading."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()
        context_manager.save(sample_context)

        lock_acquired = False
        original_enter = filelock.FileLock.__enter__

        def tracked_enter(self: filelock.FileLock) -> filelock.FileLock:
            nonlocal lock_acquired
            lock_acquired = True
            return original_enter(self)

        with patch.object(filelock.FileLock, "__enter__", tracked_enter):
            context_manager.load(sample_context.run_id)

        assert lock_acquired

    def test_save_lock_timeout_raises_error(
        self, context_manager: ContextManager, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test that lock timeout raises LOCK_TIMEOUT."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        def timeout_enter(self: filelock.FileLock) -> filelock.FileLock:
            raise filelock.Timeout(run_dir / ".lock")

        with patch.object(filelock.FileLock, "__enter__", timeout_enter):
            with pytest.raises(StateError) as exc_info:
                context_manager.save(sample_context)

        assert exc_info.value.code == "LOCK_TIMEOUT"
        assert exc_info.value.recoverable is True

    def test_load_lock_timeout_raises_error(
        self, context_manager: ContextManager, sample_context: RunContext, runs_dir: Path
    ) -> None:
        """Test that lock timeout on load raises LOCK_TIMEOUT."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()
        (run_dir / "context.json").write_text(sample_context.model_dump_json())

        def timeout_enter(self: filelock.FileLock) -> filelock.FileLock:
            raise filelock.Timeout(run_dir / ".lock")

        with patch.object(filelock.FileLock, "__enter__", timeout_enter):
            with pytest.raises(StateError) as exc_info:
                context_manager.load(sample_context.run_id)

        assert exc_info.value.code == "LOCK_TIMEOUT"
