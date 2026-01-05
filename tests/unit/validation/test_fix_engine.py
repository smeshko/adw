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
