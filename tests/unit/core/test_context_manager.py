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

    def test_save_uses_temp_file_pattern(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
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

    def test_save_cleans_up_temp_on_error(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
    ) -> None:
        """Test that temp file is cleaned up on write error."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        # Patch os.fsync to raise an error after file is written
        def failing_fsync(fd: int) -> None:
            raise OSError("Disk full")

        with (
            patch("adw.core.context_manager.os.fsync", failing_fsync),
            pytest.raises(StateError) as exc_info,
        ):
            context_manager.save(sample_context)

        assert exc_info.value.code == "CONTEXT_WRITE_FAILED"
        # Temp file should be cleaned up
        temp_path = run_dir / ".context.json.tmp"
        assert not temp_path.exists()

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

        This simulates a scenario where the rename fails after temp file
        is written. The old context.json should remain intact.
        """
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        # First, save a valid context
        context_manager.save(sample_context)
        original_content = (run_dir / "context.json").read_text()

        # Now try to save a modified context but fail the rename
        modified = sample_context.model_copy(update={"current_phase": "build"})

        def failing_rename(self: Path, target: Path) -> None:
            raise OSError("Simulated filesystem error during rename")

        with patch.object(Path, "rename", failing_rename), pytest.raises(StateError):
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

        # Temp file should not exist after successful save
        temp_path = run_dir / ".context.json.tmp"
        assert not temp_path.exists()

    def test_temp_file_cleaned_after_failed_save(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
    ) -> None:
        """Test that temp file is cleaned up after failed save."""
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        def failing_fsync(fd: int) -> None:
            raise OSError("Simulated disk error")

        with (
            patch("adw.core.context_manager.os.fsync", failing_fsync),
            pytest.raises(StateError),
        ):
            context_manager.save(sample_context)

        # Temp file should be cleaned up
        temp_path = run_dir / ".context.json.tmp"
        assert not temp_path.exists()

    def test_partial_write_never_corrupts_context(
        self,
        context_manager: ContextManager,
        sample_context: RunContext,
        runs_dir: Path,
    ) -> None:
        """Test that a partial write never leaves a corrupted context.json.

        If the write fails at any point before the atomic rename, the
        original context.json should remain untouched.
        """
        run_dir = runs_dir / sample_context.run_id
        run_dir.mkdir(parents=True)
        (run_dir / ".lock").touch()

        # Create initial valid context
        context_manager.save(sample_context)

        # Simulate partial write by failing during file.write()
        original_open = open
        call_count = 0

        def partial_write_open(path: str, mode: str = "r", *args, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal call_count
            if mode == "w" and ".context.json.tmp" in str(path):
                call_count += 1
                if call_count >= 1:
                    # Return a file that fails on write
                    class FailingFile:
                        def write(self, data: str) -> int:
                            # Write partial data then fail
                            raise OSError("Simulated partial write failure")

                        def __enter__(self) -> "FailingFile":
                            return self

                        def __exit__(self, *args: object) -> None:
                            pass

                    return FailingFile()
            return original_open(path, mode, *args, **kwargs)

        modified = sample_context.model_copy(update={"current_phase": "verify"})

        with patch("builtins.open", partial_write_open), pytest.raises(StateError):
            context_manager.save(modified)

        # Original context.json should still be valid and loadable
        loaded = context_manager.load(sample_context.run_id)
        assert loaded.run_id == sample_context.run_id
        assert loaded.current_phase == "plan"  # Original, not modified

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
        phases = ["plan", "build", "verify", "document"]
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
