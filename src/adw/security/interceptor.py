"""Security interceptor for validating LLM tool calls.

This module provides the SecurityInterceptor class that validates
tool calls against security patterns before execution.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from adw.models.security import BlockedPattern, SecurityConfig, SecuritySeverity
from adw.security.patterns import (
    is_allowed_env_file,
    match_file_pattern,
    match_shell_pattern,
)

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
        blocked_pattern: The pattern that matched, if any.
        description: Description of the security issue.
        tool_name: Name of the tool being checked.
        command_or_path: The command or file path that was checked.
    """
    
    result: SecurityCheckResult
    blocked_pattern: str | None = None
    description: str | None = None
    tool_name: str | None = None
    command_or_path: str | None = None


class SecurityInterceptor:
    """Validates LLM tool calls against security patterns.
    
    The interceptor checks shell commands and file access against
    both default and custom blocked patterns. It can be configured
    to either block dangerous operations or just log warnings.
    
    Attributes:
        config: Security configuration including custom patterns.
        allow_dangerous: If True, log warnings instead of blocking.
        
    Example:
        >>> interceptor = SecurityInterceptor()
        >>> response = interceptor.check_tool_call("Bash", {"command": "ls -la"})
        >>> response.result
        <SecurityCheckResult.ALLOWED: 'allowed'>
    """
    
    def __init__(
        self,
        config: SecurityConfig | None = None,
        allow_dangerous: bool = False,
    ) -> None:
        """Initialize the security interceptor.
        
        Args:
            config: Optional security configuration with custom patterns.
            allow_dangerous: If True, issue warnings instead of blocking.
        """
        self.config = config or SecurityConfig()
        self.allow_dangerous = allow_dangerous or self.config.allow_dangerous
        
        # Compile custom patterns from config
        self._custom_patterns: list[tuple[re.Pattern[str], BlockedPattern]] = []
        for pattern in self.config.blocked_patterns:
            try:
                compiled = re.compile(pattern.pattern, re.IGNORECASE)
                self._custom_patterns.append((compiled, pattern))
            except re.error as e:
                # Log warning for invalid patterns and skip them
                logger.warning(
                    "Invalid regex pattern in security config, skipping",
                    extra={
                        "pattern": pattern.pattern,
                        "error": str(e),
                    },
                )
    
    def check_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> SecurityCheckResponse:
        """Check if a tool call should be allowed.
        
        Args:
            tool_name: Name of the tool being called (e.g., "Bash", "Read").
            arguments: Arguments passed to the tool.
            
        Returns:
            SecurityCheckResponse with the result of the check.
        """
        # Route to appropriate checker based on tool name (case-insensitive)
        tool_lower = tool_name.lower()

        if tool_lower == "bash":
            command = arguments.get("command", "")
            return self._check_shell_command(tool_name, command)

        if tool_lower in ("read", "write", "edit"):
            file_path = arguments.get("file_path", arguments.get("path", ""))
            return self._check_file_access(tool_name, file_path)
        
        # Check custom patterns against all arguments
        for key, value in arguments.items():
            if isinstance(value, str):
                response = self._check_custom_patterns(tool_name, value)
                if response.result != SecurityCheckResult.ALLOWED:
                    return response
        
        # Default: allow
        return SecurityCheckResponse(result=SecurityCheckResult.ALLOWED)
    
    def _check_shell_command(
        self,
        tool_name: str,
        command: str,
    ) -> SecurityCheckResponse:
        """Check a shell command against blocked patterns.
        
        Args:
            tool_name: Name of the tool.
            command: The shell command to check.
            
        Returns:
            SecurityCheckResponse with the result.
        """
        # Check default patterns
        match = match_shell_pattern(command)
        if match:
            pattern, description = match
            return self._create_response(
                tool_name=tool_name,
                command_or_path=command,
                pattern=pattern,
                description=description,
            )
        
        # Check custom patterns
        response = self._check_custom_patterns(tool_name, command)
        if response.result != SecurityCheckResult.ALLOWED:
            return response
        
        return SecurityCheckResponse(result=SecurityCheckResult.ALLOWED)
    
    def _check_file_access(
        self,
        tool_name: str,
        file_path: str,
    ) -> SecurityCheckResponse:
        """Check a file access against blocked patterns.
        
        Args:
            tool_name: Name of the tool.
            file_path: The file path to check.
            
        Returns:
            SecurityCheckResponse with the result.
        """
        # Check if file is in allowed list first
        if is_allowed_env_file(file_path):
            return SecurityCheckResponse(result=SecurityCheckResult.ALLOWED)
        
        # Check default patterns
        match = match_file_pattern(file_path)
        if match:
            pattern, description = match
            return self._create_response(
                tool_name=tool_name,
                command_or_path=file_path,
                pattern=pattern,
                description=description,
            )
        
        # Check custom patterns
        response = self._check_custom_patterns(tool_name, file_path)
        if response.result != SecurityCheckResult.ALLOWED:
            return response
        
        return SecurityCheckResponse(result=SecurityCheckResult.ALLOWED)
    
    def _check_custom_patterns(
        self,
        tool_name: str,
        value: str,
    ) -> SecurityCheckResponse:
        """Check a value against custom patterns from config.
        
        Args:
            tool_name: Name of the tool.
            value: The value to check.
            
        Returns:
            SecurityCheckResponse with the result.
        """
        for pattern, blocked_pattern in self._custom_patterns:
            if pattern.search(value):
                return self._create_response(
                    tool_name=tool_name,
                    command_or_path=value,
                    pattern=blocked_pattern.pattern,
                    description=blocked_pattern.description,
                )
        
        return SecurityCheckResponse(result=SecurityCheckResult.ALLOWED)
    
    def _create_response(
        self,
        tool_name: str,
        command_or_path: str,
        pattern: str,
        description: str,
    ) -> SecurityCheckResponse:
        """Create a blocked or warning response.
        
        Args:
            tool_name: Name of the tool.
            command_or_path: The command or path that matched.
            pattern: The pattern that matched.
            description: Description of the security issue.
            
        Returns:
            SecurityCheckResponse with BLOCKED or WARNING result.
        """
        result = (
            SecurityCheckResult.WARNING
            if self.allow_dangerous
            else SecurityCheckResult.BLOCKED
        )
        
        return SecurityCheckResponse(
            result=result,
            blocked_pattern=pattern,
            description=description,
            tool_name=tool_name,
            command_or_path=command_or_path,
        )
    
    def is_blocked(self, command: str) -> tuple[bool, BlockedPattern | None]:
        """Check if a command is blocked (convenience method).
        
        Args:
            command: The command to check.
            
        Returns:
            Tuple of (is_blocked, matching_pattern).
        """
        response = self._check_shell_command("Bash", command)
        
        if response.result == SecurityCheckResult.BLOCKED:
            pattern = BlockedPattern(
                pattern=response.blocked_pattern or "",
                description=response.description or "Blocked by security policy",
                severity=SecuritySeverity.HIGH,
            )
            return (True, pattern)
        
        return (False, None)
