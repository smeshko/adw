"""Unit tests for TestValidator implementation.

Tests for the validator that executes test suites and converts
failures to ValidationIssues.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
import subprocess

import pytest

from adw.models import RunContext
from adw.validation.models import IssueSeverity, ValidationIssue, ValidationSource
from adw.validation.validators.test_validator import TestValidator


@pytest.fixture
def mock_context() -> RunContext:
    """Create a mock RunContext for testing."""
    return RunContext(
        run_id="01HQ0000000000000000000000",
        feature_description="Test feature",
        current_phase="validation",
        phase_history=["plan", "build"],
        started_at=datetime.now(UTC),
        completed_at=None,
        status="running",
        artifacts={},
        phase_tokens={},
        worktree_path=None,
        use_worktree=False,
        branch_name=None,
    )


class TestTestValidator:
    """Test cases for TestValidator class."""

    def test_validate_pytest_success(
        self, mock_context: RunContext
    ) -> None:
        """Returns empty issues list on test success."""
        validator = TestValidator(test_command="pytest")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="===== 10 passed in 1.23s =====",
                stderr="",
            )

            issues = validator.validate(mock_context)

            assert issues == []
            mock_run.assert_called_once()

    def test_validate_pytest_failures(
        self, mock_context: RunContext
    ) -> None:
        """Parses pytest output and returns issues for failures."""
        validator = TestValidator(test_command="pytest")

        pytest_output = """
============================= test session starts ==============================
collected 5 items

tests/test_auth.py::test_login_success PASSED
tests/test_auth.py::test_login_invalid_password FAILED
tests/test_auth.py::test_logout PASSED
tests/test_users.py::test_create_user FAILED

=================================== FAILURES ===================================
__________________ test_login_invalid_password __________________

    def test_login_invalid_password():
>       assert result.status == "error"
E       AssertionError: assert 'success' == 'error'

tests/test_auth.py:25: AssertionError
__________________ test_create_user __________________

    def test_create_user():
>       assert user.id is not None
E       AssertionError: assert None is not None

tests/test_users.py:42: AssertionError
=========================== short test summary info ============================
FAILED tests/test_auth.py::test_login_invalid_password - AssertionError
FAILED tests/test_users.py::test_create_user - AssertionError
============================= 2 failed, 3 passed in 0.54s ======================
"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout=pytest_output,
                stderr="",
            )

            issues = validator.validate(mock_context)

            assert len(issues) == 2
            assert all(i.source == ValidationSource.TEST for i in issues)
            # Check that test names are captured
            test_names = [i.message for i in issues]
            assert any("test_login_invalid_password" in name for name in test_names)
            assert any("test_create_user" in name for name in test_names)

    def test_validate_npm_test(
        self, mock_context: RunContext
    ) -> None:
        """Uses npm test for Node.js projects."""
        validator = TestValidator(test_command="npm test")

        npm_output = """
> project@1.0.0 test
> jest

 PASS  tests/utils.test.js
 FAIL  tests/auth.test.js
  ● Auth › should validate credentials

    expect(received).toBe(expected)

    Expected: true
    Received: false

      12 |   const result = validateCredentials(user, pass);
      13 |   expect(result).toBe(true);
         |                  ^
      14 | });

      at Object.<anonymous> (tests/auth.test.js:13:18)

Test Suites: 1 failed, 1 passed, 2 total
Tests:       1 failed, 3 passed, 4 total
"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout=npm_output,
                stderr="",
            )

            issues = validator.validate(mock_context)

            assert len(issues) >= 1
            assert all(i.source == ValidationSource.TEST for i in issues)

    def test_validate_timeout(
        self, mock_context: RunContext
    ) -> None:
        """Returns timeout issue when tests exceed limit."""
        validator = TestValidator(test_command="pytest", timeout_seconds=1)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd="pytest", timeout=1
            )

            issues = validator.validate(mock_context)

            assert len(issues) == 1
            assert issues[0].source == ValidationSource.TEST
            assert "timed out" in issues[0].message.lower()
            assert issues[0].severity == IssueSeverity.ERROR  # high maps to ERROR

    def test_validate_command_not_found(
        self, mock_context: RunContext
    ) -> None:
        """Returns error issue when test command is not found."""
        validator = TestValidator(test_command="nonexistent_test_runner")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("Command not found")

            issues = validator.validate(mock_context)

            assert len(issues) == 1
            assert issues[0].source == ValidationSource.TEST
            assert "not found" in issues[0].message.lower() or "error" in issues[0].message.lower()
            assert issues[0].severity == IssueSeverity.ERROR  # critical maps to ERROR

    def test_name_property(self) -> None:
        """TestValidator returns correct name."""
        validator = TestValidator()
        assert validator.name == "test"

    def test_default_test_command_detection(self) -> None:
        """TestValidator can detect default test command."""
        validator = TestValidator()
        # Default should be pytest for Python projects
        assert validator.test_command in ["pytest", "npm test", None]
