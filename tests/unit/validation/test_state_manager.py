"""Tests for ValidationStateManager.

Tests the validation state persistence manager including:
- State save/load operations
- Issues persistence
- Triage persistence
- Fix history persistence
- Resume capability
- Atomic writes
"""

from pathlib import Path

import pytest

from adw.validation.models import (
    IssueSeverity,
    IssueSource,
    LoopState,
    ValidationIssue,
    ValidationState,
)
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

    def test_file_paths_correct(self, tmp_path: Path) -> None:
        """File path properties return correct paths."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()

        manager = ValidationStateManager("run-123", base_path)

        assert manager.state_file == base_path / "validation" / "state.json"
        assert manager.issues_file == base_path / "validation" / "issues.json"
        assert manager.triage_file == base_path / "validation" / "triage.json"
        assert manager.fix_history_file == base_path / "validation" / "fix-history.json"


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


class TestIssuesPersistence:
    """Tests for issues save/load."""

    def test_issues_stored_at_correct_path(self, tmp_path: Path) -> None:
        """Issues are stored at .adw/runs/<id>/validation/issues.json."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Test failed",
            ),
        ]

        manager.save_issues(issues)

        expected_path = base_path / "validation" / "issues.json"
        assert expected_path.exists()
        assert manager.issues_file == expected_path

    def test_save_and_load_issues(self, tmp_path: Path) -> None:
        """Issues round-trip correctly through save and load."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Test failed: test_login",
            ),
            ValidationIssue(
                source=IssueSource.REVIEW,
                severity=IssueSeverity.WARNING,
                description="Missing docstring",
            ),
        ]

        manager.save_issues(issues)
        loaded = manager.load_issues()

        assert len(loaded) == 2
        assert loaded[0].description == "Test failed: test_login"
        assert loaded[0].source == IssueSource.TEST
        assert loaded[1].description == "Missing docstring"
        assert loaded[1].severity == IssueSeverity.WARNING

    def test_load_issues_empty_file(self, tmp_path: Path) -> None:
        """Load returns empty list when no issues file exists."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        loaded = manager.load_issues()

        assert loaded == []

    def test_load_issues_corrupted_file(self, tmp_path: Path) -> None:
        """Load returns empty list when issues file is corrupted."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)
        manager.issues_file.write_text("not valid json")

        loaded = manager.load_issues()

        assert loaded == []


class TestTriagePersistence:
    """Tests for triage decision save/load."""

    def test_triage_stored_at_correct_path(self, tmp_path: Path) -> None:
        """Triage decisions are stored at .adw/runs/<id>/validation/triage.json."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        decisions = [{"issue_id": "VI-001", "decision": "FIX", "reason": "Test"}]
        manager.save_triage(decisions)

        expected_path = base_path / "validation" / "triage.json"
        assert expected_path.exists()
        assert manager.triage_file == expected_path

    def test_save_and_load_triage(self, tmp_path: Path) -> None:
        """Triage decisions round-trip correctly."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        decisions = [
            {
                "issue_id": "VI-001",
                "decision": "FIX",
                "reason": "Critical test failure",
                "auto_decided": False,
            },
            {
                "issue_id": "VI-002",
                "decision": "DEFER",
                "reason": "Low priority",
                "auto_decided": True,
            },
        ]

        manager.save_triage(decisions)
        loaded = manager.load_triage()

        assert len(loaded) == 2
        assert "VI-001" in loaded
        assert loaded["VI-001"]["decision"] == "FIX"
        assert "timestamp" in loaded["VI-001"]  # Auto-added

    def test_triage_preserves_reasoning_for_audit(self, tmp_path: Path) -> None:
        """Triage reasoning is preserved for audit trail."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        decisions = [
            {
                "issue_id": "VI-001",
                "decision": "DISMISS",
                "reason": "False positive - test expects old behavior",
                "auto_decided": False,
            },
        ]

        manager.save_triage(decisions)
        loaded = manager.load_triage()

        # Verify reasoning is preserved for audit
        assert loaded["VI-001"]["reason"] == "False positive - test expects old behavior"
        assert loaded["VI-001"]["auto_decided"] is False

    def test_load_triage_empty(self, tmp_path: Path) -> None:
        """Load returns empty dict when no triage file exists."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        loaded = manager.load_triage()

        assert loaded == {}

    def test_load_triage_non_list_json(self, tmp_path: Path) -> None:
        """Load returns empty dict when triage.json contains non-list JSON."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)
        # Write valid JSON but wrong type (number instead of list)
        manager.triage_file.write_text("42")

        loaded = manager.load_triage()

        # Should gracefully return empty dict, not crash with TypeError
        assert loaded == {}


class TestFixHistoryPersistence:
    """Tests for fix history save/load."""

    def test_fix_history_stored_at_correct_path(self, tmp_path: Path) -> None:
        """Fix history is stored at .adw/runs/<id>/validation/fix-history.json."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        history = [{"iteration": 1, "issues_fixed": 1, "files_modified": []}]
        manager.save_fix_history(history)

        expected_path = base_path / "validation" / "fix-history.json"
        assert expected_path.exists()
        assert manager.fix_history_file == expected_path

    def test_save_and_load_fix_history(self, tmp_path: Path) -> None:
        """Fix history round-trips correctly."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        history = [
            {
                "iteration": 1,
                "issues_fixed": 3,
                "issues_remaining": 2,
                "issues_deferred": 1,
                "files_modified": ["src/auth.py", "tests/test_auth.py"],
            },
        ]

        manager.save_fix_history(history)
        loaded = manager.load_fix_history()

        assert len(loaded) == 1
        assert loaded[0]["iteration"] == 1
        assert loaded[0]["issues_fixed"] == 3
        assert "timestamp" in loaded[0]  # Auto-added

    def test_fix_history_includes_file_modifications(self, tmp_path: Path) -> None:
        """Fix history preserves file modifications for each iteration."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        history = [
            {
                "iteration": 1,
                "issues_fixed": 2,
                "issues_remaining": 3,
                "issues_deferred": 0,
                "files_modified": [
                    "src/adw/validation/models.py",
                    "src/adw/validation/phase.py",
                    "tests/unit/validation/test_models.py",
                ],
            },
            {
                "iteration": 2,
                "issues_fixed": 3,
                "issues_remaining": 0,
                "issues_deferred": 0,
                "files_modified": ["src/adw/validation/phase.py"],
            },
        ]

        manager.save_fix_history(history)
        loaded = manager.load_fix_history()

        assert len(loaded) == 2
        assert loaded[0]["files_modified"] == [
            "src/adw/validation/models.py",
            "src/adw/validation/phase.py",
            "tests/unit/validation/test_models.py",
        ]
        assert loaded[1]["files_modified"] == ["src/adw/validation/phase.py"]

    def test_load_fix_history_empty(self, tmp_path: Path) -> None:
        """Load returns empty list when no fix history file exists."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        loaded = manager.load_fix_history()

        assert loaded == []


class TestStatePersistence:
    """Tests for state save/load."""

    def test_state_stored_at_correct_path(self, tmp_path: Path) -> None:
        """State is stored at .adw/runs/<id>/validation/state.json."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        state = {"current_iteration": 1}
        manager.save_state(state)

        expected_path = base_path / "validation" / "state.json"
        assert expected_path.exists()
        assert manager.state_file == expected_path

    def test_save_state_uses_atomic_write(self, tmp_path: Path) -> None:
        """State save uses atomic write (no temp file remains)."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        state = {"current_iteration": 1}
        manager.save_state(state)

        # Verify no temp file remains
        temp_file = manager.state_file.with_suffix(".tmp")
        assert not temp_file.exists()
        assert manager.state_file.exists()

    def test_save_and_load_state(self, tmp_path: Path) -> None:
        """State round-trips correctly."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        state = {
            "current_iteration": 2,
            "total_iterations": 5,
            "started_at": "2026-01-05T10:00:00Z",
        }

        manager.save_state(state)
        loaded = manager.load_state()

        assert loaded is not None
        assert loaded["current_iteration"] == 2
        assert loaded["run_id"] == "run-123"  # Auto-set
        assert "last_updated" in loaded  # Auto-set

    def test_save_state_accepts_validation_state_model(self, tmp_path: Path) -> None:
        """save_state accepts ValidationState model."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        loop_state = LoopState(issues_resolved=5, issues_remaining=2)
        state = ValidationState(
            run_id="run-123",
            current_iteration=3,
            total_iterations=5,
            loop_state=loop_state,
        )

        manager.save_state(state)
        loaded = manager.load_state()

        assert loaded is not None
        assert loaded["current_iteration"] == 3
        assert loaded["loop_state"]["issues_resolved"] == 5
        assert loaded["loop_state"]["issues_remaining"] == 2

    def test_load_state_model_returns_validation_state(self, tmp_path: Path) -> None:
        """load_state_model returns ValidationState model."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        loop_state = LoopState(issues_resolved=5)
        state = ValidationState(
            run_id="run-123",
            current_iteration=3,
            loop_state=loop_state,
        )
        manager.save_state(state)

        loaded = manager.load_state_model()

        assert loaded is not None
        assert isinstance(loaded, ValidationState)
        assert loaded.current_iteration == 3
        assert loaded.loop_state.issues_resolved == 5

    def test_load_state_missing_file(self, tmp_path: Path) -> None:
        """Load returns None when no state file exists."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        loaded = manager.load_state()

        assert loaded is None

    def test_load_state_model_missing_file(self, tmp_path: Path) -> None:
        """load_state_model returns None when no state file exists."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        loaded = manager.load_state_model()

        assert loaded is None

    def test_load_state_corrupted_file(self, tmp_path: Path) -> None:
        """Load returns None when state file is corrupted."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)
        manager.state_file.write_text("not valid json")

        loaded = manager.load_state()

        assert loaded is None


class TestResumeCapability:
    """Tests for resume functionality."""

    def test_can_resume_true(self, tmp_path: Path) -> None:
        """can_resume returns True with valid resumable state."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        state = {"current_iteration": 2, "total_iterations": 5}
        manager.save_state(state)

        assert manager.can_resume() is True

    def test_can_resume_false_no_state(self, tmp_path: Path) -> None:
        """can_resume returns False when no state file exists."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        assert manager.can_resume() is False

    def test_can_resume_false_wrong_run_id(self, tmp_path: Path) -> None:
        """can_resume returns False when run_id doesn't match."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()

        # Create state with different run_id
        manager1 = ValidationStateManager("run-123", base_path)
        manager1.state_file.write_text('{"run_id": "different-run", "current_iteration": 2}')

        # Try to resume with different run_id
        manager2 = ValidationStateManager("run-123", base_path)

        assert manager2.can_resume() is False

    def test_can_resume_false_zero_iteration(self, tmp_path: Path) -> None:
        """can_resume returns False when iteration is 0."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        state = {"current_iteration": 0}
        manager.save_state(state)

        assert manager.can_resume() is False

    def test_resume_returns_validation_state(self, tmp_path: Path) -> None:
        """resume returns ValidationState model when state is valid."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        loop_state = LoopState(issues_resolved=3, issues_remaining=2)
        state = ValidationState(
            run_id="run-123",
            current_iteration=2,
            total_iterations=5,
            loop_state=loop_state,
        )
        manager.save_state(state)

        resumed = manager.resume()

        assert isinstance(resumed, ValidationState)
        assert resumed.current_iteration == 2
        assert resumed.loop_state.issues_resolved == 3
        assert resumed.loop_state.issues_remaining == 2

    def test_resume_raises_when_cannot_resume(self, tmp_path: Path) -> None:
        """resume raises ValueError when state cannot be resumed."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        with pytest.raises(ValueError, match="Cannot resume validation"):
            manager.resume()

    def test_resume_validates_state_integrity(self, tmp_path: Path) -> None:
        """resume validates that state is properly structured."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        # Save minimal valid state for can_resume to pass
        loop_state = LoopState(issues_resolved=0, issues_remaining=5)
        state = ValidationState(
            run_id="run-123",
            current_iteration=1,
            loop_state=loop_state,
        )
        manager.save_state(state)

        # resume should work with valid state
        resumed = manager.resume()
        assert resumed.current_iteration == 1


class TestClear:
    """Tests for state clearing."""

    def test_clear_removes_all_files(self, tmp_path: Path) -> None:
        """Clear removes all state files."""
        base_path = tmp_path / "run-123"
        base_path.mkdir()
        manager = ValidationStateManager("run-123", base_path)

        # Create all state files
        manager.save_state({"current_iteration": 1})
        manager.save_issues([])
        manager.save_triage([])
        manager.save_fix_history([])

        # Verify files exist
        assert manager.state_file.exists()
        assert manager.issues_file.exists()
        assert manager.triage_file.exists()
        assert manager.fix_history_file.exists()

        # Clear
        manager.clear()

        # Verify all removed
        assert not manager.state_file.exists()
        assert not manager.issues_file.exists()
        assert not manager.triage_file.exists()
        assert not manager.fix_history_file.exists()
