"""Pattern matching engine for security checks.

This module provides the PatternMatcher class for checking commands and
file paths against blocked patterns. It supports context-aware matching
and can distinguish between safe and dangerous uses.

Usage:
    >>> from adw.security.patterns import PatternMatcher
    >>> matcher = PatternMatcher()
    >>> matches = matcher.match_command("rm -rf /")
    >>> if matches:
    ...     print(f"Blocked: {matches[0].description}")
"""

import re
from typing import NamedTuple

from adw.models.security import BlockedPattern
from adw.security.defaults import (
    ALLOWED_ENV_PATTERNS,
    DEFAULT_FILE_PATTERNS,
    DEFAULT_SHELL_PATTERNS,
)


class PatternMatch(NamedTuple):
    """Result of a pattern match against a command or file path.

    Attributes:
        pattern: The regex pattern that matched
        description: Human-readable description of what was matched
        severity: Severity level (critical/warning/info)
        category: Category of the pattern
        alternative: Suggested safe alternative
    """

    pattern: str
    description: str
    severity: str
    category: str
    alternative: str


class CompiledPattern:
    """A compiled regex pattern with associated metadata.

    Pre-compiles patterns at initialization for better performance.
    """

    def __init__(self, blocked_pattern: BlockedPattern) -> None:
        """Initialize a compiled pattern.

        Args:
            blocked_pattern: The BlockedPattern to compile
        """
        self.blocked_pattern = blocked_pattern
        self._compiled = re.compile(blocked_pattern.pattern)

    def matches(self, text: str) -> bool:
        """Check if the pattern matches the given text.

        Args:
            text: The text to check against

        Returns:
            True if the pattern matches
        """
        return bool(self._compiled.search(text))

    def to_match(self) -> PatternMatch:
        """Convert to a PatternMatch result.

        Returns:
            PatternMatch with pattern metadata
        """
        return PatternMatch(
            pattern=self.blocked_pattern.pattern,
            description=self.blocked_pattern.description,
            severity=self.blocked_pattern.severity,
            category=self.blocked_pattern.category,
            alternative=self.blocked_pattern.alternative,
        )


class PatternMatcher:
    """Matches commands and file paths against blocked patterns.

    The PatternMatcher maintains compiled regex patterns for efficient
    matching and supports both shell command matching and file access
    pattern matching.

    Example:
        >>> matcher = PatternMatcher()
        >>> matches = matcher.match_command("git push --force origin main")
        >>> for m in matches:
        ...     print(f"{m.severity}: {m.description}")
        warning: Force push to remote repository
    """

    def __init__(
        self,
        additional_patterns: list[BlockedPattern] | None = None,
        additional_file_patterns: list[str] | None = None,
    ) -> None:
        """Initialize the pattern matcher.

        Args:
            additional_patterns: Custom patterns to add to default shell patterns
            additional_file_patterns: Additional file path patterns to block
        """
        # Compile shell patterns
        all_shell_patterns = list(DEFAULT_SHELL_PATTERNS)
        if additional_patterns:
            all_shell_patterns.extend(additional_patterns)

        self._shell_patterns: list[CompiledPattern] = [
            CompiledPattern(p) for p in all_shell_patterns
        ]

        # Compile file patterns
        all_file_patterns = list(DEFAULT_FILE_PATTERNS)
        if additional_file_patterns:
            for pat in additional_file_patterns:
                all_file_patterns.append(
                    BlockedPattern(
                        pattern=pat,
                        description=f"Custom blocked file pattern: {pat}",
                        severity="warning",
                        category="secret_access",
                    )
                )

        self._file_patterns: list[CompiledPattern] = [
            CompiledPattern(p) for p in all_file_patterns
        ]

        # Compile allowed patterns (for exceptions like .env.example)
        self._allowed_patterns: list[re.Pattern[str]] = [
            re.compile(p) for p in ALLOWED_ENV_PATTERNS
        ]

    def match_command(self, command: str) -> list[PatternMatch]:
        """Check a shell command against blocked patterns.

        Scans the command string against all shell patterns and returns
        a list of matches. Each match includes the pattern that matched,
        a description, and suggested alternatives.

        Args:
            command: The shell command to check

        Returns:
            List of PatternMatch objects for each matching pattern

        Example:
            >>> matcher = PatternMatcher()
            >>> matches = matcher.match_command("rm -rf ~")
            >>> matches[0].category
            'destructive'
        """
        matches: list[PatternMatch] = []

        for compiled in self._shell_patterns:
            if compiled.matches(command):
                matches.append(compiled.to_match())

        return matches

    def match_file_access(self, path: str) -> list[PatternMatch]:
        """Check a file path against blocked patterns.

        Scans the file path against file access patterns. Automatically
        allows exceptions like .env.example, .env.sample, .env.template.

        Args:
            path: The file path to check

        Returns:
            List of PatternMatch objects for each matching pattern

        Example:
            >>> matcher = PatternMatcher()
            >>> matches = matcher.match_file_access(".env")
            >>> len(matches) > 0
            True
            >>> matches = matcher.match_file_access(".env.example")
            >>> len(matches)
            0
        """
        # First check if this path matches an allowed exception
        for allowed_pattern in self._allowed_patterns:
            if allowed_pattern.search(path):
                # This is an allowed file (e.g., .env.example)
                return []

        matches: list[PatternMatch] = []

        for compiled in self._file_patterns:
            if compiled.matches(path):
                matches.append(compiled.to_match())

        return matches

    def is_blocked(
        self, command: str | None = None, file_path: str | None = None
    ) -> tuple[bool, list[PatternMatch]]:
        """Check if a command or file path is blocked.

        Convenience method that checks both command and file path and
        returns whether blocking should occur along with all matches.

        Args:
            command: Shell command to check (optional)
            file_path: File path to check (optional)

        Returns:
            Tuple of (is_blocked, list of matches)

        Example:
            >>> matcher = PatternMatcher()
            >>> blocked, matches = matcher.is_blocked(command="rm -rf /")
            >>> blocked
            True
        """
        matches: list[PatternMatch] = []

        if command:
            matches.extend(self.match_command(command))

        if file_path:
            matches.extend(self.match_file_access(file_path))

        is_blocked = len(matches) > 0

        return is_blocked, matches
