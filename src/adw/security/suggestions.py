"""Alternative suggestions for blocked patterns.

This module provides utilities for formatting user-friendly messages
when a dangerous command is blocked, including alternative suggestions
and override instructions.

Usage:
    >>> from adw.security.suggestions import SuggestionFormatter
    >>> formatter = SuggestionFormatter()
    >>> message = formatter.format_single(pattern_match)
    >>> print(message)
"""

from adw.security.patterns import PatternMatch

# =============================================================================
# OVERRIDE INSTRUCTION
# =============================================================================

OVERRIDE_INSTRUCTION = (
    "To override (use with caution):\n"
    "  adw run --allow-dangerous \"your feature\""
)


def get_override_instruction() -> str:
    """Get the standard override instruction message.

    Returns:
        String containing instructions for using --allow-dangerous

    Example:
        >>> instruction = get_override_instruction()
        >>> "--allow-dangerous" in instruction
        True
    """
    return OVERRIDE_INSTRUCTION


# =============================================================================
# CATEGORY EXAMPLES
#
# Example commands for each category to help users understand
# what types of operations are blocked.
# =============================================================================

CATEGORY_EXAMPLES: dict[str, list[str]] = {
    "destructive": [
        "rm -rf / (deletes entire filesystem)",
        "rm -rf ~ (deletes home directory)",
        "rm -rf . (deletes current directory)",
        "mkfs.ext4 /dev/sda (formats disk)",
        "dd if=/dev/zero of=/dev/sda (overwrites disk)",
    ],
    "permission": [
        "chmod 777 /path (world-writable permissions)",
        "chmod -R 777 . (recursive world-writable)",
        "chown root: /path (change ownership to root)",
    ],
    "git_dangerous": [
        "git push --force (force push)",
        "git push -f (force push short form)",
        "git reset --hard (discard uncommitted changes)",
        "git clean -fd (force delete untracked files)",
        "git branch -D main (delete protected branch)",
    ],
    "secret_access": [
        "cat .env (read environment secrets)",
        "echo \"SECRET=x\" > .env (write to .env file)",
        "cat credentials.json (read credentials)",
        "read private-key.pem (access private key)",
    ],
}


def get_category_examples(category: str) -> list[str]:
    """Get example blocked commands for a category.

    Args:
        category: The pattern category (destructive, permission, etc.)

    Returns:
        List of example commands that would be blocked

    Example:
        >>> examples = get_category_examples("destructive")
        >>> any("rm" in ex.lower() for ex in examples)
        True
    """
    return CATEGORY_EXAMPLES.get(category, [])


# =============================================================================
# SUGGESTION FORMATTER
# =============================================================================


class SuggestionFormatter:
    """Formats pattern match results into user-friendly messages.

    The formatter creates structured error messages that include:
    - What was blocked and why
    - The severity level
    - Suggested alternatives
    - How to override if needed

    Example:
        >>> formatter = SuggestionFormatter()
        >>> match = PatternMatch(...)
        >>> print(formatter.format_single(match))
        [CRITICAL] Recursive delete of root directory

        Suggested alternative:
          Use specific paths: rm -rf ./node_modules

        To override (use with caution):
          adw run --allow-dangerous "your feature"
    """

    def __init__(self, *, include_override: bool = True) -> None:
        """Initialize the formatter.

        Args:
            include_override: Whether to include override instructions
        """
        self.include_override = include_override

    def format_single(self, match: PatternMatch) -> str:
        """Format a single pattern match into a user message.

        Args:
            match: The PatternMatch to format

        Returns:
            Formatted string with all relevant information

        Example:
            >>> formatter = SuggestionFormatter()
            >>> match = PatternMatch(
            ...     pattern=r"rm\\s+-rf",
            ...     description="Recursive delete",
            ...     severity="critical",
            ...     category="destructive",
            ...     alternative="Use specific paths",
            ...     allowed=False,
            ... )
            >>> result = formatter.format_single(match)
            >>> "Recursive delete" in result
            True
        """
        lines: list[str] = []

        # Header with severity
        severity_upper = match.severity.upper()
        lines.append(f"[{severity_upper}] {match.description}")
        lines.append("")

        # Category context
        lines.append(f"Category: {match.category}")
        lines.append("")

        # Alternative suggestion
        if match.alternative:
            lines.append("Suggested alternative:")
            lines.append(f"  {match.alternative}")
            lines.append("")

        # Override instruction
        if self.include_override and not match.allowed:
            lines.append(OVERRIDE_INSTRUCTION)

        return "\n".join(lines)

    def format_multiple(self, matches: list[PatternMatch]) -> str:
        """Format multiple pattern matches into a combined message.

        Args:
            matches: List of PatternMatch objects to format

        Returns:
            Combined formatted string, empty if no matches

        Example:
            >>> formatter = SuggestionFormatter()
            >>> result = formatter.format_multiple([])
            >>> result
            ''
        """
        if not matches:
            return ""

        sections: list[str] = []

        for i, match in enumerate(matches, 1):
            if len(matches) > 1:
                sections.append(f"--- Issue {i} of {len(matches)} ---")
            sections.append(self.format_single(match))
            sections.append("")

        return "\n".join(sections).rstrip()

    def format_error_message(
        self,
        matches: list[PatternMatch],
        *,
        command: str | None = None,
        file_path: str | None = None,
    ) -> str:
        """Format a complete error message for blocked operations.

        Args:
            matches: List of pattern matches
            command: The command that was blocked (optional)
            file_path: The file path that was blocked (optional)

        Returns:
            Complete formatted error message
        """
        lines: list[str] = []

        lines.append("DANGEROUS OPERATION BLOCKED")
        lines.append("=" * 40)
        lines.append("")

        if command:
            lines.append(f"Command: {command}")
        if file_path:
            lines.append(f"File: {file_path}")

        if command or file_path:
            lines.append("")

        lines.append(self.format_multiple(matches))

        return "\n".join(lines)
