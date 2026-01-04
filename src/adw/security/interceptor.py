"""Security interceptor for blocking dangerous LLM tool calls.

This module provides the SecurityInterceptor class that validates
tool calls against security patterns and can block dangerous operations.
It wraps the PatternMatcher and adds blocking/warning capability.

Story 3.6: Security Hook Infrastructure - adds blocking to pattern matching.
"""

import logging
from dataclasses import dataclass
from enum import Enum

from adw.exceptions import SecurityError
from adw.models.security import BlockedPattern
from adw.security.patterns import PatternMatch, PatternMatcher
from adw.security.suggestions import get_override_instruction

logger = logging.getLogger(__name__)


class SecurityCheckResult(Enum):
    """Result of a security check."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    WARNING = "warning"  # Used when allow_dangerous is True


@dataclass
class SecurityCheckResponse:
    """Response from a security check.

    Attributes:
        result: Whether the check passed, was blocked, or issued a warning.
        matches: List of pattern matches found.
        tool_name: Name of the tool being checked.
        command_or_path: The command or file path that was checked.
    """

    result: SecurityCheckResult
    matches: list[PatternMatch]
    tool_name: str | None = None
    command_or_path: str | None = None

    @property
    def blocked_pattern(self) -> str | None:
        """Get the first blocked pattern, if any."""
        return self.matches[0].pattern if self.matches else None

    @property
    def description(self) -> str | None:
        """Get the first match description, if any."""
        return self.matches[0].description if self.matches else None


class SecurityInterceptor:
    """Validates and blocks dangerous LLM tool calls.

    Wraps PatternMatcher to add blocking capability. When allow_dangerous
    is False, dangerous tool calls raise SecurityError. When True,
    warnings are logged but execution continues.

    Example:
        >>> interceptor = SecurityInterceptor()
        >>> response = interceptor.check_tool_call("Bash", {"command": "rm -rf /"})
        >>> response.result
        <SecurityCheckResult.BLOCKED: 'blocked'>
    """

    def __init__(
        self,
        additional_patterns: list[BlockedPattern] | None = None,
        *,
        allow_dangerous: bool = False,
    ) -> None:
        """Initialize the security interceptor.

        Args:
            additional_patterns: Custom patterns to add to defaults.
            allow_dangerous: If True, issue warnings instead of blocking.
        """
        self.allow_dangerous = allow_dangerous
        self._matcher = PatternMatcher(
            additional_patterns=additional_patterns,
            allow_dangerous=allow_dangerous,
        )

    def check_tool_call(
        self,
        tool_name: str,
        arguments: dict,
    ) -> SecurityCheckResponse:
        """Check if a tool call should be allowed.

        Args:
            tool_name: Name of the tool being called (e.g., "Bash", "Read").
            arguments: Arguments passed to the tool.

        Returns:
            SecurityCheckResponse with the result of the check.
        """
        tool_lower = tool_name.lower()

        # Route to appropriate checker based on tool name
        if tool_lower == "bash":
            command = arguments.get("command", "")
            return self._check_command(tool_name, command)

        if tool_lower in ("read", "write", "edit"):
            file_path = arguments.get("file_path", arguments.get("path", ""))
            return self._check_file_access(tool_name, file_path)

        # For unknown tools, allow by default
        return SecurityCheckResponse(
            result=SecurityCheckResult.ALLOWED,
            matches=[],
            tool_name=tool_name,
        )

    def _check_command(
        self,
        tool_name: str,
        command: str,
    ) -> SecurityCheckResponse:
        """Check a shell command against blocked patterns."""
        matches = self._matcher.match_command(command)

        if not matches:
            return SecurityCheckResponse(
                result=SecurityCheckResult.ALLOWED,
                matches=[],
                tool_name=tool_name,
                command_or_path=command,
            )

        result = (
            SecurityCheckResult.WARNING
            if self.allow_dangerous
            else SecurityCheckResult.BLOCKED
        )

        return SecurityCheckResponse(
            result=result,
            matches=matches,
            tool_name=tool_name,
            command_or_path=command,
        )

    def _check_file_access(
        self,
        tool_name: str,
        file_path: str,
    ) -> SecurityCheckResponse:
        """Check file access against blocked patterns."""
        matches = self._matcher.match_file_access(file_path)

        if not matches:
            return SecurityCheckResponse(
                result=SecurityCheckResult.ALLOWED,
                matches=[],
                tool_name=tool_name,
                command_or_path=file_path,
            )

        result = (
            SecurityCheckResult.WARNING
            if self.allow_dangerous
            else SecurityCheckResult.BLOCKED
        )

        return SecurityCheckResponse(
            result=result,
            matches=matches,
            tool_name=tool_name,
            command_or_path=file_path,
        )

    def validate_and_raise(
        self,
        tool_name: str,
        arguments: dict,
    ) -> None:
        """Validate a tool call and raise SecurityError if blocked.

        This is a convenience method for integration with executors.
        It checks the tool call and raises SecurityError if blocked.

        Args:
            tool_name: Name of the tool being called.
            arguments: Arguments passed to the tool.

        Raises:
            SecurityError: If the tool call is blocked and allow_dangerous is False.
        """
        response = self.check_tool_call(tool_name, arguments)

        if response.result == SecurityCheckResult.BLOCKED:
            match = response.matches[0] if response.matches else None
            alternatives = [match.alternative] if match and match.alternative else []

            raise SecurityError(
                code="DANGEROUS_COMMAND_BLOCKED",
                message=f"Tool call blocked: {tool_name}",
                pattern_matched=match.pattern if match else "",
                tool_name=tool_name,
                alternatives=alternatives,
                override_instruction=get_override_instruction(),
                severity=match.severity if match else "warning",
                suggestion="Use --allow-dangerous flag to override security checks",
            )

        if response.result == SecurityCheckResult.WARNING:
            match = response.matches[0] if response.matches else None
            logger.warning(
                "Tool call triggered security warning (allow_dangerous=True)",
                extra={
                    "tool_name": tool_name,
                    "pattern": match.pattern if match else None,
                    "description": match.description if match else None,
                },
            )
