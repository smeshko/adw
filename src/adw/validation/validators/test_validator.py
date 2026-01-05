"""TestValidator - Executes test suites and reports failures.

This validator runs the configured test command (pytest, npm test, etc.)
and converts test failures into ValidationIssues.
"""

from __future__ import annotations

import logging
import re
import subprocess
from typing import TYPE_CHECKING

from adw.validation.models import ValidationIssue, ValidationSource

if TYPE_CHECKING:
    from adw.models import RunContext

logger = logging.getLogger(__name__)


# Regex patterns for parsing test output
PYTEST_FAILED_PATTERN = re.compile(
    r"FAILED\s+([^\s]+)::(\w+)(?:\s+-\s+(.+))?",
    re.MULTILINE,
)
PYTEST_SHORT_SUMMARY_PATTERN = re.compile(
    r"FAILED\s+([^\s]+)\s+-\s+(.+)",
    re.MULTILINE,
)
NPM_FAIL_PATTERN = re.compile(
    r"FAIL\s+(.+\.(?:test|spec)\.(?:js|ts|jsx|tsx))",
    re.MULTILINE,
)
NPM_TEST_ERROR_PATTERN = re.compile(
    r"●\s+(.+?)\s+›\s+(.+)",
    re.MULTILINE,
)
GENERIC_ERROR_PATTERN = re.compile(
    r"(?:ERROR|FAIL|FAILED)[:|\s]+(.+)",
    re.MULTILINE | re.IGNORECASE,
)


class TestValidator:
    """Validator that executes test suites and reports failures.

    Runs the configured test command and parses the output to
    identify failing tests. Each failure is converted to a
    ValidationIssue with source=TEST.

    Attributes:
        test_command: The command to run tests (e.g., "pytest", "npm test").
        timeout_seconds: Maximum time to wait for tests to complete.
    """

    def __init__(
        self,
        test_command: str | None = None,
        timeout_seconds: int = 300,
    ) -> None:
        """Initialize the test validator.

        Args:
            test_command: Command to run tests. Auto-detects if None.
            timeout_seconds: Timeout for test execution.
        """
        self._test_command = test_command
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        """Return the validator's name."""
        return "test"

    @property
    def test_command(self) -> str | None:
        """Return the configured test command."""
        return self._test_command

    def validate(self, context: RunContext) -> list[ValidationIssue]:
        """Execute tests and return any failures as issues.

        Args:
            context: Current run context.

        Returns:
            List of ValidationIssues for each test failure.
        """
        command = self._get_test_command()
        if not command:
            return [
                ValidationIssue(
                    source=ValidationSource.TEST,
                    message="No test command configured and could not auto-detect",
                    severity="critical",
                )
            ]

        logger.info(f"Running test command: {command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )

            # Check for success
            if result.returncode == 0:
                logger.info("All tests passed")
                return []

            # Parse failures from output
            output = result.stdout + result.stderr
            issues = self._parse_test_output(output, command)

            if not issues:
                # If we couldn't parse specific failures, create a generic issue
                issues = [
                    ValidationIssue(
                        source=ValidationSource.TEST,
                        message=f"Tests failed with exit code {result.returncode}",
                        severity="high",
                    )
                ]

            logger.info(f"Found {len(issues)} test failures")
            return issues

        except subprocess.TimeoutExpired:
            logger.warning(f"Test execution timed out after {self._timeout_seconds}s")
            return [
                ValidationIssue(
                    source=ValidationSource.TEST,
                    message=f"Test execution timed out after {self._timeout_seconds}s",
                    severity="high",
                )
            ]
        except FileNotFoundError as e:
            logger.error(f"Test command not found: {e}")
            return [
                ValidationIssue(
                    source=ValidationSource.TEST,
                    message=f"Test command not found: {command}. Error: {e}",
                    severity="critical",
                )
            ]
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return [
                ValidationIssue(
                    source=ValidationSource.TEST,
                    message=f"Error running tests: {e}",
                    severity="critical",
                )
            ]

    def _get_test_command(self) -> str | None:
        """Get the test command to run.

        Returns configured command or attempts to auto-detect.

        Returns:
            Test command string or None if cannot determine.
        """
        if self._test_command:
            return self._test_command

        # Auto-detect based on project files
        # This is a simplified version - could be enhanced with platform detection
        return "pytest"  # Default to pytest for Python projects

    def _parse_test_output(
        self, output: str, command: str
    ) -> list[ValidationIssue]:
        """Parse test output to extract failures.

        Args:
            output: Combined stdout and stderr from test run.
            command: The test command that was run.

        Returns:
            List of ValidationIssues for each failure found.
        """
        issues: list[ValidationIssue] = []

        if "pytest" in command.lower():
            issues = self._parse_pytest_output(output)
        elif "npm" in command.lower() or "jest" in command.lower():
            issues = self._parse_npm_output(output)
        else:
            issues = self._parse_generic_output(output)

        return issues

    def _parse_pytest_output(self, output: str) -> list[ValidationIssue]:
        """Parse pytest output for failures.

        Args:
            output: Pytest output text.

        Returns:
            List of ValidationIssues for each pytest failure.
        """
        issues: list[ValidationIssue] = []

        # Try to find failures in short test summary
        matches = PYTEST_SHORT_SUMMARY_PATTERN.findall(output)
        for match in matches:
            file_test = match[0]
            reason = match[1] if len(match) > 1 else ""

            # Extract file path and test name
            parts = file_test.split("::")
            file_path = parts[0] if parts else None
            test_name = parts[1] if len(parts) > 1 else file_test

            msg = f"Test failed: {test_name}"
            if reason:
                msg += f" - {reason}"
            issues.append(
                ValidationIssue(
                    source=ValidationSource.TEST,
                    message=msg,
                    severity="high",
                    file_path=file_path,
                )
            )

        # If no matches from short summary, try the full pattern
        if not issues:
            matches = PYTEST_FAILED_PATTERN.findall(output)
            for match in matches:
                file_path = match[0]
                test_name = match[1]
                reason = match[2] if len(match) > 2 else ""

                msg = f"Test failed: {test_name}"
                if reason:
                    msg += f" - {reason}"
                issues.append(
                    ValidationIssue(
                        source=ValidationSource.TEST,
                        message=msg,
                        severity="high",
                        file_path=file_path,
                    )
                )

        return issues

    def _parse_npm_output(self, output: str) -> list[ValidationIssue]:
        """Parse npm/jest test output for failures.

        Args:
            output: npm test output text.

        Returns:
            List of ValidationIssues for each npm test failure.
        """
        issues: list[ValidationIssue] = []

        # Find test error descriptions
        matches = NPM_TEST_ERROR_PATTERN.findall(output)
        for match in matches:
            suite_name = match[0]
            test_name = match[1]

            issues.append(
                ValidationIssue(
                    source=ValidationSource.TEST,
                    message=f"Test failed: {suite_name} › {test_name}",
                    severity="high",
                )
            )

        # If no specific matches, try to find failing files
        if not issues:
            file_matches = NPM_FAIL_PATTERN.findall(output)
            for file_path in file_matches:
                issues.append(
                    ValidationIssue(
                        source=ValidationSource.TEST,
                        message=f"Test file failed: {file_path}",
                        severity="high",
                        file_path=file_path,
                    )
                )

        return issues

    def _parse_generic_output(self, output: str) -> list[ValidationIssue]:
        """Parse generic test output for failures.

        Args:
            output: Test output text.

        Returns:
            List of ValidationIssues for each failure found.
        """
        issues: list[ValidationIssue] = []

        matches = GENERIC_ERROR_PATTERN.findall(output)
        for match in matches[:10]:  # Limit to first 10 to avoid spam
            # Truncate long messages
            error_text = match.strip()[:200]
            issues.append(
                ValidationIssue(
                    source=ValidationSource.TEST,
                    message=f"Test error: {error_text}",
                    severity="high",
                )
            )

        return issues


__all__ = ["TestValidator"]
