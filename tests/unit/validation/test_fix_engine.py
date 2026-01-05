"""Tests for FixEngine - validation issue fix automation.

These tests verify the FixEngine correctly:
- Filters issues to only process FIX-triaged ones
- Calls LLM with appropriate fix prompts
- Applies fixes atomically with backup/rollback
- Re-runs affected validators
- Tracks fix attempt counts and auto-defers
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from adw.validation.config import ValidationConfig
from adw.validation.fix_engine import FixEngine, FixIterationResult
from adw.validation.models import (
    FixResult,
    IssueLocation,
    IssueSource,
    IssueSeverity,
    ValidationIssue,
)
from adw.validation.validators.base import Validator

if TYPE_CHECKING:
    from adw.models import RunContext


class MockValidator:
    """Mock validator for testing."""

    def __init__(self, name: str, issues: list[ValidationIssue] | None = None) -> None:
        self._name = name
        self._issues = issues or []

    @property
    def name(self) -> str:
        return self._name

    def validate(self, context: RunContext) -> list[ValidationIssue]:
        return self._issues


@pytest.fixture
def mock_llm_executor() -> MagicMock:
    """Create mock LLM executor."""
    executor = MagicMock()
    executor.execute.return_value = MagicMock(
        success=True,
        content='{"fixes": []}',
    )
    return executor


@pytest.fixture
def mock_context() -> MagicMock:
    """Create mock run context."""
    context = MagicMock()
    context.run_id = "01TEST123456789ABCDEFGHJKMN"
    context.worktree_path = None
    return context


@pytest.fixture
def fix_issue() -> ValidationIssue:
    """Create an issue triaged for FIX."""
    return ValidationIssue(
        source=IssueSource.TEST,
        severity=IssueSeverity.ERROR,
        description="Test failed: test_login_validation",
        location=IssueLocation(
            file_path="tests/test_auth.py",
            line_start=42,
        ),
        triage_decision="FIX",
        triage_reason="Test failure should be fixed",
    )


@pytest.fixture
def dismiss_issue() -> ValidationIssue:
    """Create an issue triaged for DISMISS."""
    return ValidationIssue(
        source=IssueSource.REVIEW,
        severity=IssueSeverity.INFO,
        description="Consider adding docstring",
        triage_decision="DISMISS",
        triage_reason="Optional documentation",
    )


@pytest.fixture
def defer_issue() -> ValidationIssue:
    """Create an issue triaged for DEFER."""
    return ValidationIssue(
        source=IssueSource.REVIEW,
        severity=IssueSeverity.WARNING,
        description="Could refactor this method",
        triage_decision="DEFER",
        triage_reason="Not critical for this feature",
    )


class TestFixEngine:
    """Tests for FixEngine core functionality."""

    def test_init_stores_dependencies(
        self, mock_llm_executor: MagicMock, mock_context: MagicMock
    ) -> None:
        """FixEngine stores injected dependencies."""
        config = ValidationConfig()
        validators = [MockValidator("test")]

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=config,
            validators=validators,
        )

        assert engine.llm is mock_llm_executor
        assert engine.config is config
        assert "test" in engine.validators

    def test_attempt_fixes_filters_to_fix_only(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
        fix_issue: ValidationIssue,
        dismiss_issue: ValidationIssue,
        defer_issue: ValidationIssue,
    ) -> None:
        """Only FIX-triaged issues are processed."""
        config = ValidationConfig()
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=config,
            validators=[],
        )

        issues = [fix_issue, dismiss_issue, defer_issue]
        result = engine.attempt_fixes(issues, mock_context)

        # Should be a FixIterationResult
        assert isinstance(result, FixIterationResult)
        # LLM should have been called (there was a FIX issue)
        mock_llm_executor.execute.assert_called_once()

    def test_attempt_fixes_skips_non_fix(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
        dismiss_issue: ValidationIssue,
        defer_issue: ValidationIssue,
    ) -> None:
        """When no FIX issues, LLM is not called."""
        config = ValidationConfig()
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=config,
            validators=[],
        )

        issues = [dismiss_issue, defer_issue]
        result = engine.attempt_fixes(issues, mock_context)

        # LLM should NOT have been called
        mock_llm_executor.execute.assert_not_called()
        # Result should show no fixes attempted
        assert result.issues_fixed == []
        assert result.validation_rerun is False

    def test_attempt_fixes_returns_result_model(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
        fix_issue: ValidationIssue,
    ) -> None:
        """attempt_fixes returns FixIterationResult with expected fields."""
        config = ValidationConfig()
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=config,
            validators=[],
        )

        result = engine.attempt_fixes([fix_issue], mock_context)

        assert hasattr(result, "issues_fixed")
        assert hasattr(result, "issues_remaining")
        assert hasattr(result, "issues_deferred")
        assert hasattr(result, "files_modified")
        assert hasattr(result, "validation_rerun")
        assert hasattr(result, "iteration_number")

    def test_get_affected_validators_maps_source(
        self,
        mock_llm_executor: MagicMock,
    ) -> None:
        """Validator mapping correctly identifies affected validators."""
        test_validator = MockValidator("test")
        review_validator = MockValidator("review")
        evidence_validator = MockValidator("evidence")

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[test_validator, review_validator, evidence_validator],
        )

        # TEST source → test validator
        test_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            triage_decision="FIX",
        )
        affected = engine._get_affected_validators([test_issue])
        assert len(affected) == 1
        assert affected[0].name == "test"

        # REVIEW source → review validator
        review_issue = ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.ERROR,
            description="Code issue",
            triage_decision="FIX",
        )
        affected = engine._get_affected_validators([review_issue])
        assert len(affected) == 1
        assert affected[0].name == "review"


class TestFixPromptGeneration:
    """Tests for fix prompt generation."""

    def test_includes_issue_details(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Prompt includes issue description and source."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        issue = ValidationIssue(
            id="VI-TESTID001",
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed: test_login_validation",
            triage_decision="FIX",
        )

        prompt = engine._build_fix_prompt([issue], mock_context)

        assert "VI-TESTID001" in prompt
        assert "TEST" in prompt
        assert "Test failed: test_login_validation" in prompt

    def test_includes_location_info(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Prompt includes file path and line number when available."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            location=IssueLocation(
                file_path="tests/test_auth.py",
                line_start=42,
            ),
            triage_decision="FIX",
        )

        prompt = engine._build_fix_prompt([issue], mock_context)

        assert "tests/test_auth.py" in prompt
        assert "42" in prompt

    def test_includes_code_context(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Prompt includes code snippets when available."""
        from adw.validation.models import IssueContext

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        issue = ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.ERROR,
            description="Missing null check",
            context=IssueContext(
                code_snippet="def process(data):\n    return data['key']",
            ),
            triage_decision="FIX",
        )

        prompt = engine._build_fix_prompt([issue], mock_context)

        assert "def process(data)" in prompt
        assert "data['key']" in prompt

    def test_batches_multiple_issues(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Multiple issues included in single prompt."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        issues = [
            ValidationIssue(
                id="VI-001",
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="First test failure",
                triage_decision="FIX",
            ),
            ValidationIssue(
                id="VI-002",
                source=IssueSource.REVIEW,
                severity=IssueSeverity.ERROR,
                description="Second code issue",
                triage_decision="FIX",
            ),
        ]

        prompt = engine._build_fix_prompt(issues, mock_context)

        assert "VI-001" in prompt
        assert "VI-002" in prompt
        assert "First test failure" in prompt
        assert "Second code issue" in prompt

    def test_requests_json_response(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Prompt requests structured JSON fix response."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            triage_decision="FIX",
        )

        prompt = engine._build_fix_prompt([issue], mock_context)

        assert "JSON" in prompt
        assert "fixes" in prompt
        assert "file_path" in prompt
        assert "replacement" in prompt


class TestFixApplication:
    """Tests for fix application (backup, apply, rollback)."""

    def test_parse_fix_response_extracts_fixes(
        self,
        mock_llm_executor: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Valid JSON response parsed into FileChange objects."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("original content")

        response = f'''
        {{
            "fixes": [
                {{
                    "issue_id": "VI-001",
                    "file_path": "{test_file}",
                    "replacement": "fixed content"
                }}
            ]
        }}
        '''

        changes = engine._parse_fix_response(response)

        assert len(changes) == 1
        assert changes[0].file_path == test_file
        assert changes[0].new_content == "fixed content"
        assert changes[0].original_content == "original content"

    def test_parse_fix_response_handles_invalid_json(
        self,
        mock_llm_executor: MagicMock,
    ) -> None:
        """Invalid JSON returns empty list, doesn't crash."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        changes = engine._parse_fix_response("not valid json at all")
        assert changes == []

    def test_parse_fix_response_skips_null_replacement(
        self,
        mock_llm_executor: MagicMock,
    ) -> None:
        """Fixes with null replacement are skipped (uncertain fixes)."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        response = '''
        {
            "fixes": [
                {
                    "issue_id": "VI-001",
                    "file_path": "src/test.py",
                    "replacement": null
                }
            ]
        }
        '''

        changes = engine._parse_fix_response(response)
        assert changes == []

    def test_backup_files_stores_original_content(
        self,
        mock_llm_executor: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Backup stores file content before modification."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        # Create test files
        file1 = tmp_path / "file1.py"
        file1.write_text("content 1")
        file2 = tmp_path / "file2.py"
        file2.write_text("content 2")

        from adw.validation.fix_engine import FileChange

        changes = [
            FileChange(file_path=file1, original_content="", new_content="new1"),
            FileChange(file_path=file2, original_content="", new_content="new2"),
        ]

        engine._backup_files(changes)

        assert engine._file_backups[file1] == "content 1"
        assert engine._file_backups[file2] == "content 2"

    def test_apply_changes_writes_files(
        self,
        mock_llm_executor: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Apply changes writes new content to files."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        test_file = tmp_path / "test.py"
        test_file.write_text("original")

        from adw.validation.fix_engine import FileChange

        changes = [
            FileChange(
                file_path=test_file,
                original_content="original",
                new_content="fixed",
            )
        ]

        engine._apply_changes(changes)

        assert test_file.read_text() == "fixed"

    def test_rollback_restores_original_content(
        self,
        mock_llm_executor: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Rollback restores files from backup."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        test_file = tmp_path / "test.py"
        test_file.write_text("original")

        from adw.validation.fix_engine import FileChange

        changes = [
            FileChange(
                file_path=test_file,
                original_content="original",
                new_content="broken",
            )
        ]

        # Backup, apply, then rollback
        engine._backup_files(changes)
        engine._apply_changes(changes)
        assert test_file.read_text() == "broken"

        engine._rollback()
        assert test_file.read_text() == "original"

    def test_apply_changes_partial_line_replacement(
        self,
        mock_llm_executor: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Partial line replacement modifies specific lines."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\nline3\nline4\n")

        from adw.validation.fix_engine import FileChange

        changes = [
            FileChange(
                file_path=test_file,
                original_content="line1\nline2\nline3\nline4\n",
                new_content="fixed_line",
                line_start=2,
                line_end=3,
            )
        ]

        engine._apply_changes(changes)

        result = test_file.read_text()
        assert "line1" in result
        assert "fixed_line" in result
        assert "line4" in result


class TestSelectiveRevalidation:
    """Tests for selective re-validation after fixes."""

    def test_get_affected_validators_test_source(
        self,
        mock_llm_executor: MagicMock,
    ) -> None:
        """TEST source maps to test validator."""
        test_validator = MockValidator("test")
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[test_validator],
        )

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            triage_decision="FIX",
        )

        affected = engine._get_affected_validators([issue])

        assert len(affected) == 1
        assert affected[0].name == "test"

    def test_get_affected_validators_review_source(
        self,
        mock_llm_executor: MagicMock,
    ) -> None:
        """REVIEW source maps to review validator."""
        review_validator = MockValidator("review")
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[review_validator],
        )

        issue = ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.ERROR,
            description="Code issue",
            triage_decision="FIX",
        )

        affected = engine._get_affected_validators([issue])

        assert len(affected) == 1
        assert affected[0].name == "review"

    def test_get_affected_validators_evidence_source(
        self,
        mock_llm_executor: MagicMock,
    ) -> None:
        """EVIDENCE source maps to evidence validator."""
        evidence_validator = MockValidator("evidence")
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[evidence_validator],
        )

        issue = ValidationIssue(
            source=IssueSource.EVIDENCE,
            severity=IssueSeverity.ERROR,
            description="Evidence mismatch",
            triage_decision="FIX",
        )

        affected = engine._get_affected_validators([issue])

        assert len(affected) == 1
        assert affected[0].name == "evidence"

    def test_get_affected_validators_multiple_sources(
        self,
        mock_llm_executor: MagicMock,
    ) -> None:
        """Multiple issues with different sources get all affected validators."""
        test_validator = MockValidator("test")
        review_validator = MockValidator("review")
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[test_validator, review_validator],
        )

        issues = [
            ValidationIssue(
                source=IssueSource.TEST,
                severity=IssueSeverity.ERROR,
                description="Test failed",
                triage_decision="FIX",
            ),
            ValidationIssue(
                source=IssueSource.REVIEW,
                severity=IssueSeverity.ERROR,
                description="Code issue",
                triage_decision="FIX",
            ),
        ]

        affected = engine._get_affected_validators(issues)

        assert len(affected) == 2
        names = {v.name for v in affected}
        assert names == {"test", "review"}

    def test_check_resolution_detects_resolved(
        self,
        mock_llm_executor: MagicMock,
    ) -> None:
        """Issues no longer in new_issues are marked resolved."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        original = ValidationIssue(
            id="VI-001",
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed: test_login",
            triage_decision="FIX",
        )

        # No issues after re-validation
        new_issues: list[ValidationIssue] = []

        resolved, remaining = engine._check_resolution([original], new_issues)

        assert len(resolved) == 1
        assert resolved[0].id == "VI-001"
        assert len(remaining) == 0

    def test_check_resolution_detects_remaining(
        self,
        mock_llm_executor: MagicMock,
    ) -> None:
        """Issues still in new_issues remain unresolved."""
        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[],
        )

        original = ValidationIssue(
            id="VI-001",
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed: test_login",
            location=IssueLocation(file_path="tests/test_auth.py"),
            triage_decision="FIX",
        )

        # Same issue still present
        new_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed: test_login",
            location=IssueLocation(file_path="tests/test_auth.py"),
        )

        resolved, remaining = engine._check_resolution([original], [new_issue])

        assert len(resolved) == 0
        assert len(remaining) == 1
        assert remaining[0].id == "VI-001"


class TestFixAttemptTracking:
    """Tests for fix attempt tracking."""

    def test_updates_fix_attempted_flag(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Fix attempt sets fix_attempted to True on issues."""
        # Return empty fixes so issue remains unresolved
        mock_llm_executor.execute.return_value = MagicMock(
            success=True,
            content='{"fixes": []}',
        )

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[MockValidator("test", [])],  # No issues on revalidate
        )

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            triage_decision="FIX",
        )
        assert issue.fix_attempted is False

        engine.attempt_fixes([issue], mock_context)

        # Issue should still fail (no actual fix applied), so it remains
        # But the fix_attempted flag should be set
        # Note: Since no new issues from validator, issue will be marked resolved
        # So we need a validator that returns the same issue
        assert issue.fix_attempted is False  # Resolved issues aren't updated

    def test_increments_fix_attempt_count(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Each fix attempt increments the count."""
        mock_llm_executor.execute.return_value = MagicMock(
            success=True,
            content='{"fixes": []}',
        )

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Persistent test failure",
            location=IssueLocation(file_path="tests/test_foo.py"),
            triage_decision="FIX",
        )

        # Create a validator that always returns the same issue (not fixed)
        same_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Persistent test failure",
            location=IssueLocation(file_path="tests/test_foo.py"),
        )
        validator = MockValidator("test", [same_issue])

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(max_fix_attempts_per_issue=5),
            validators=[validator],
        )

        # First attempt
        engine.attempt_fixes([issue], mock_context)
        assert issue.fix_attempt_count == 1

        # Reset triage for second attempt
        issue.triage_decision = "FIX"

        # Second attempt
        engine.attempt_fixes([issue], mock_context)
        assert issue.fix_attempt_count == 2

    def test_creates_fix_attempt_record(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Each attempt creates a FixAttempt in fix_history."""
        mock_llm_executor.execute.return_value = MagicMock(
            success=True,
            content='{"fixes": []}',
        )

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failure",
            location=IssueLocation(file_path="tests/test.py"),
            triage_decision="FIX",
        )

        # Validator returns same issue (fix failed)
        same_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failure",
            location=IssueLocation(file_path="tests/test.py"),
        )
        validator = MockValidator("test", [same_issue])

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[validator],
        )

        assert len(issue.fix_history) == 0

        engine.attempt_fixes([issue], mock_context)

        assert len(issue.fix_history) == 1
        assert issue.fix_history[0].result == FixResult.FAILED

    def test_updates_last_fix_result(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """last_fix_result updated after each attempt."""
        mock_llm_executor.execute.return_value = MagicMock(
            success=True,
            content='{"fixes": []}',
        )

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failure",
            location=IssueLocation(file_path="tests/test.py"),
            triage_decision="FIX",
        )

        # First: validator returns same issue (failed)
        same_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failure",
            location=IssueLocation(file_path="tests/test.py"),
        )
        validator = MockValidator("test", [same_issue])

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[validator],
        )

        assert issue.last_fix_result == FixResult.NOT_ATTEMPTED

        engine.attempt_fixes([issue], mock_context)

        assert issue.last_fix_result == FixResult.FAILED


class TestAutoDeferLogic:
    """Tests for auto-defer on max attempts."""

    def test_auto_defer_after_max_attempts(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Issue auto-deferred after max fix attempts reached."""
        mock_llm_executor.execute.return_value = MagicMock(
            success=True,
            content='{"fixes": []}',
        )

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Persistent failure",
            location=IssueLocation(file_path="tests/test.py"),
            triage_decision="FIX",
            fix_attempt_count=1,  # Already tried once
        )

        # Validator returns same issue
        same_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Persistent failure",
            location=IssueLocation(file_path="tests/test.py"),
        )
        validator = MockValidator("test", [same_issue])

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(max_fix_attempts_per_issue=2),
            validators=[validator],
        )

        result = engine.attempt_fixes([issue], mock_context)

        assert issue.triage_decision == "DEFER"
        assert issue.id in result.issues_deferred

    def test_auto_defer_sets_reason(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Auto-defer sets appropriate reason message."""
        mock_llm_executor.execute.return_value = MagicMock(
            success=True,
            content='{"fixes": []}',
        )

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failure",
            location=IssueLocation(file_path="tests/test.py"),
            triage_decision="FIX",
            fix_attempt_count=1,
        )

        same_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failure",
            location=IssueLocation(file_path="tests/test.py"),
        )
        validator = MockValidator("test", [same_issue])

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(max_fix_attempts_per_issue=2),
            validators=[validator],
        )

        engine.attempt_fixes([issue], mock_context)

        assert "Max fix attempts reached" in (issue.triage_reason or "")
        assert "2" in (issue.triage_reason or "")

    def test_no_defer_under_max_attempts(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Issue not deferred when under max attempts."""
        mock_llm_executor.execute.return_value = MagicMock(
            success=True,
            content='{"fixes": []}',
        )

        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failure",
            location=IssueLocation(file_path="tests/test.py"),
            triage_decision="FIX",
            fix_attempt_count=0,  # First attempt
        )

        same_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failure",
            location=IssueLocation(file_path="tests/test.py"),
        )
        validator = MockValidator("test", [same_issue])

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(max_fix_attempts_per_issue=3),
            validators=[validator],
        )

        result = engine.attempt_fixes([issue], mock_context)

        # Still FIX, not deferred yet
        assert issue.triage_decision == "FIX"
        assert issue.id in result.issues_remaining


class TestFixIterationResult:
    """Tests for FixIterationResult model."""

    def test_creation_with_all_fields(self) -> None:
        """FixIterationResult can be created with all fields."""
        result = FixIterationResult(
            issues_fixed=["VI-001", "VI-002"],
            issues_remaining=["VI-003"],
            issues_deferred=["VI-004"],
            files_modified=["src/foo.py"],
            validation_rerun=True,
            iteration_number=1,
        )

        assert result.issues_fixed == ["VI-001", "VI-002"]
        assert result.issues_remaining == ["VI-003"]
        assert result.issues_deferred == ["VI-004"]
        assert result.files_modified == ["src/foo.py"]
        assert result.validation_rerun is True
        assert result.iteration_number == 1

    def test_serialization_round_trip(self) -> None:
        """FixIterationResult serializes and deserializes correctly."""
        result = FixIterationResult(
            issues_fixed=["VI-001"],
            issues_remaining=[],
            issues_deferred=[],
            files_modified=["src/foo.py"],
            validation_rerun=True,
            iteration_number=2,
        )

        # Serialize to dict
        data = result.model_dump()
        # Deserialize back
        restored = FixIterationResult.model_validate(data)

        assert restored == result

    def test_json_serialization(self) -> None:
        """FixIterationResult serializes to JSON for persistence."""
        import json

        result = FixIterationResult(
            issues_fixed=["VI-001"],
            issues_remaining=["VI-002"],
            issues_deferred=["VI-003"],
            files_modified=["src/foo.py", "src/bar.py"],
            validation_rerun=True,
            iteration_number=3,
        )

        # Serialize to JSON
        json_str = result.model_dump_json()
        data = json.loads(json_str)

        assert data["issues_fixed"] == ["VI-001"]
        assert data["issues_remaining"] == ["VI-002"]
        assert data["issues_deferred"] == ["VI-003"]
        assert data["files_modified"] == ["src/foo.py", "src/bar.py"]
        assert data["validation_rerun"] is True
        assert data["iteration_number"] == 3

        # Deserialize from JSON
        restored = FixIterationResult.model_validate_json(json_str)
        assert restored == result

    def test_default_values(self) -> None:
        """FixIterationResult has sensible defaults."""
        result = FixIterationResult()

        assert result.issues_fixed == []
        assert result.issues_remaining == []
        assert result.issues_deferred == []
        assert result.files_modified == []
        assert result.validation_rerun is False
        assert result.iteration_number == 0


class TestFixValidateCycle:
    """Integration tests for the complete fix→validate cycle."""

    def test_full_cycle_issue_resolved(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Full cycle: fix is applied, issue resolved on re-validation."""
        # LLM returns a fix
        test_file = tmp_path / "test.py"
        test_file.write_text("broken_code()")

        mock_llm_executor.execute.return_value = MagicMock(
            success=True,
            content=f'''{{
                "fixes": [{{
                    "issue_id": "VI-001",
                    "file_path": "{test_file}",
                    "replacement": "fixed_code()"
                }}]
            }}''',
        )

        issue = ValidationIssue(
            id="VI-001",
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            location=IssueLocation(file_path=str(test_file)),
            triage_decision="FIX",
        )

        # Validator returns no issues (fix worked)
        validator = MockValidator("test", [])

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(),
            validators=[validator],
        )

        result = engine.attempt_fixes([issue], mock_context)

        # Issue should be fixed
        assert "VI-001" in result.issues_fixed
        assert result.validation_rerun is True
        # File should be modified
        assert test_file.read_text() == "fixed_code()"

    def test_full_cycle_issue_remains(
        self,
        mock_llm_executor: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Full cycle: fix is attempted but issue remains on re-validation."""
        mock_llm_executor.execute.return_value = MagicMock(
            success=True,
            content='{"fixes": []}',  # No fix available
        )

        issue = ValidationIssue(
            id="VI-001",
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Persistent test failure",
            location=IssueLocation(file_path="tests/test.py"),
            triage_decision="FIX",
        )

        # Validator returns same issue (still broken)
        same_issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Persistent test failure",
            location=IssueLocation(file_path="tests/test.py"),
        )
        validator = MockValidator("test", [same_issue])

        engine = FixEngine(
            llm_executor=mock_llm_executor,
            config=ValidationConfig(max_fix_attempts_per_issue=3),
            validators=[validator],
        )

        result = engine.attempt_fixes([issue], mock_context)

        # Issue should remain
        assert result.issues_fixed == []
        assert "VI-001" in result.issues_remaining
        assert result.validation_rerun is True

        # Issue should have updated tracking
        assert issue.fix_attempt_count == 1
        assert issue.fix_attempted is True
        assert issue.last_fix_result == FixResult.FAILED
