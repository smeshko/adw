"""Tests for ContextManager with atomic writes and durability.

This module tests the ContextManager class which handles atomic saves and loads
of RunContext with fsync, temp file pattern, and lock integration.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

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
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
    ) -> None:
        """Test that save creates context.json file."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        # Create lock file
        (run_dir / ".lock").touch()

        context_manager.save(sample_context)

        context_path = run_dir / "context.json"
        assert context_path.exists()

    def test_save_calls_fsync(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
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
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
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

    def test_failed_write_keeps_the_old_context_and_no_temp(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
    ) -> None:
        """A write that fails partway leaves the old context.json and no temp."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()
        context_manager.save(sample_context)
        modified = sample_context.model_copy(update={"current_phase": "build"})

        with (
            patch("adw.fs.os.fsync", side_effect=OSError("Disk full")),
            pytest.raises(StateError) as exc_info,
        ):
            context_manager.save(modified)

        assert exc_info.value.code == "CONTEXT_WRITE_FAILED"
        assert context_manager.load(sample_context.run_id).current_phase == "plan"
        assert list(run_dir.glob("*.tmp")) == []

    def test_save_missing_run_dir_raises_error(
        self, context_manager: ContextManager, sample_context: RunContext
    ) -> None:
        """Test that saving to non-existent run directory raises RUN_DIR_NOT_FOUND."""
        # Don't create the run directory
        with pytest.raises(StateError) as exc_info:
            context_manager.save(sample_context)

        assert exc_info.value.code == "RUN_DIR_NOT_FOUND"
        assert "run directory" in exc_info.value.suggestion.lower()


class TestContextManagerLoad:
    """Tests for ContextManager.load() method."""

    def test_load_returns_valid_context(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
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
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
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
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
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
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
    ) -> None:
        """Test that lock timeout raises LOCK_TIMEOUT."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        def timeout_enter(self: filelock.FileLock) -> filelock.FileLock:
            raise filelock.Timeout(run_dir / ".lock")

        with (
            patch.object(filelock.FileLock, "__enter__", timeout_enter),
            pytest.raises(StateError) as exc_info,
        ):
            context_manager.save(sample_context)

        assert exc_info.value.code == "LOCK_TIMEOUT"
        assert exc_info.value.recoverable is True

    def test_load_lock_timeout_raises_error(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
    ) -> None:
        """Test that lock timeout on load raises LOCK_TIMEOUT."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()
        (run_dir / "context.json").write_text(sample_context.model_dump_json())

        def timeout_enter(self: filelock.FileLock) -> filelock.FileLock:
            raise filelock.Timeout(run_dir / ".lock")

        with (
            patch.object(filelock.FileLock, "__enter__", timeout_enter),
            pytest.raises(StateError) as exc_info,
        ):
            context_manager.load(sample_context.run_id)

        assert exc_info.value.code == "LOCK_TIMEOUT"


class TestContextManagerDurability:
    """Tests for durability and atomic write guarantees."""

    def test_interrupted_write_preserves_old_context(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
    ) -> None:
        """Test that if write is interrupted, old context is preserved.

        This simulates a scenario where the final rename fails after the temp
        file is written. The old context.json should remain intact.
        """
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        # First, save a valid context
        context_manager.save(sample_context)
        original_content = (run_dir / "context.json").read_text()

        # Now try to save a modified context but fail the rename
        modified = sample_context.model_copy(update={"current_phase": "build"})

        with (
            patch("adw.fs.os.replace", side_effect=OSError("rename failed")),
            pytest.raises(StateError),
        ):
            context_manager.save(modified)

        # Original context should still exist and be valid
        assert (run_dir / "context.json").exists()
        current_content = (run_dir / "context.json").read_text()
        assert current_content == original_content

        # The context should still load correctly
        loaded = context_manager.load(sample_context.run_id)
        assert loaded.current_phase == "plan"  # Original, not modified

    def test_temp_file_cleaned_after_successful_save(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
    ) -> None:
        """Test that temp file does not exist after successful save."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        context_manager.save(sample_context)

        # No temp file is left after a successful save
        assert list(run_dir.glob("*.tmp")) == []

    def test_context_file_never_partially_overwritten(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
    ) -> None:
        """Test that context.json is never in a partial state.

        The atomic rename pattern ensures that context.json is either:
        - The old complete file
        - The new complete file
        - Never a partial/mixed state
        """
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        # Save initial context
        context_manager.save(sample_context)
        initial_json = (run_dir / "context.json").read_text()

        # Verify it's valid JSON
        json.loads(initial_json)

        # Save updated context
        modified = sample_context.model_copy(
            update={"current_phase": "build", "feature_description": "Updated feature"}
        )
        context_manager.save(modified)

        # Read final context
        final_json = (run_dir / "context.json").read_text()

        # Both should be valid JSON
        initial_data = json.loads(initial_json)
        final_data = json.loads(final_json)

        # They should be different (update happened)
        assert initial_data["current_phase"] == "plan"
        assert final_data["current_phase"] == "build"

    def test_multiple_rapid_saves_maintain_integrity(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
    ) -> None:
        """Test that multiple rapid saves maintain data integrity.

        Each save should complete atomically, and the final state
        should reflect the last successful save.
        """
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        # Perform multiple rapid saves
        phases = ["plan", "build", "validate", "document"]
        for phase in phases:
            updated = sample_context.model_copy(update={"current_phase": phase})
            context_manager.save(updated)

        # Verify final state
        loaded = context_manager.load(sample_context.run_id)
        assert loaded.current_phase == "document"

        # Verify file is valid JSON
        content = (run_dir / "context.json").read_text()
        data = json.loads(content)
        assert data["current_phase"] == "document"
