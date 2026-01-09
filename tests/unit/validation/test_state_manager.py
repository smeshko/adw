"""Tests for ValidationStateManager (Story 16.4).

Tests cover:
- Result file persistence
- Atomic writes
- Loading/clearing state
"""

from pathlib import Path

import pytest

from adw.validation.models import ValidationResult
from adw.validation.state_manager import ValidationStateManager


class TestValidationStateManagerInit:
    """Tests for ValidationStateManager initialization."""

    def test_creates_validation_directory(self, tmp_path: Path) -> None:
        """Validation directory is created if it doesn't exist."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()

        manager = ValidationStateManager("run-123", base_path)

        assert manager.validation_dir.exists()
        assert manager.validation_dir == base_path / "validation"

    def test_result_file_path_correct(self, tmp_path: Path) -> None:
        """result_file property returns correct path."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()

        manager = ValidationStateManager("run-123", base_path)

        assert manager.result_file == base_path / "validation" / "result.json"


class TestAtomicWrite:
    """Tests for atomic write functionality."""

    def test_atomic_write_creates_file(self, tmp_path: Path) -> None:
        """Atomic write creates the target file."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        target = manager.validation_dir / "test.json"
        manager._atomic_write(target, '{"test": true}')

        assert target.exists()
        assert target.read_text() == '{"test": true}'

    def test_atomic_write_no_temp_file_remains(self, tmp_path: Path) -> None:
        """Atomic write doesn't leave temp files after success."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        target = manager.validation_dir / "test.json"
        manager._atomic_write(target, '{"test": true}')

        temp_file = target.with_suffix(".tmp")
        assert not temp_file.exists()


class TestSaveResult:
    """Tests for saving validation results."""

    def test_save_result_creates_file(self, tmp_path: Path) -> None:
        """save_result creates result.json file."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=["Fixed bug"],
            issues_remaining=[],
            summary="All good",
        )

        manager.save_result(result)

        assert manager.result_file.exists()

    def test_save_result_content(self, tmp_path: Path) -> None:
        """save_result stores correct JSON content."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        result = ValidationResult(
            passed=False,
            tests_passed=False,
            code_review_passed=True,
            issues_fixed=[],
            issues_remaining=["Test fails"],
            summary="Failing",
        )

        manager.save_result(result)

        import json

        content = json.loads(manager.result_file.read_text())
        assert content["passed"] is False
        assert content["tests_passed"] is False
        assert content["code_review_passed"] is True
        assert content["issues_remaining"] == ["Test fails"]

    def test_save_result_uses_atomic_write(self, tmp_path: Path) -> None:
        """save_result uses atomic write (no temp file remains)."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
        )
        manager.save_result(result)

        temp_file = manager.result_file.with_suffix(".tmp")
        assert not temp_file.exists()


class TestLoadResult:
    """Tests for loading validation results."""

    def test_load_result_returns_none_when_not_exists(self, tmp_path: Path) -> None:
        """load_result returns None when no result file exists."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        result = manager.load_result()

        assert result is None

    def test_load_result_round_trip(self, tmp_path: Path) -> None:
        """Result survives round-trip through save/load."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        original = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
            issues_fixed=["Fixed issue 1", "Fixed issue 2"],
            issues_remaining=[],
            summary="All tests pass",
        )

        manager.save_result(original)
        loaded = manager.load_result()

        assert loaded is not None
        assert loaded.passed == original.passed
        assert loaded.tests_passed == original.tests_passed
        assert loaded.code_review_passed == original.code_review_passed
        assert loaded.issues_fixed == original.issues_fixed
        assert loaded.issues_remaining == original.issues_remaining
        assert loaded.summary == original.summary

    def test_load_result_handles_corrupted_json(self, tmp_path: Path) -> None:
        """load_result returns None for corrupted JSON."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)
        manager.result_file.write_text("not valid json {{{")

        result = manager.load_result()

        assert result is None

    def test_load_result_handles_invalid_schema(self, tmp_path: Path) -> None:
        """load_result returns None for invalid schema."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)
        manager.result_file.write_text('{"invalid": "schema"}')

        result = manager.load_result()

        assert result is None


class TestClear:
    """Tests for state clearing."""

    def test_clear_removes_result_file(self, tmp_path: Path) -> None:
        """Clear removes result.json file."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        # Create a result file
        result = ValidationResult(
            passed=True,
            tests_passed=True,
            code_review_passed=True,
        )
        manager.save_result(result)
        assert manager.result_file.exists()

        # Clear should remove it
        manager.clear()

        assert not manager.result_file.exists()

    def test_clear_handles_missing_files(self, tmp_path: Path) -> None:
        """Clear doesn't error when files don't exist."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        # No files exist yet, clear should not error
        manager.clear()

        assert not manager.result_file.exists()
