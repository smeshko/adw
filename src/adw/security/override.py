"""Override logging for --allow-dangerous mode.

This module provides the OverrideLogger class for tracking blocked patterns
that were allowed due to the --allow-dangerous flag. It logs warnings for
each overridden block and maintains a record for run-level reporting.

Usage:
    >>> from adw.security.override import OverrideLogger
    >>> logger = OverrideLogger()
    >>> logger.log_override(match, command="rm -rf /tmp")
    >>> print(f"Allowed {logger.get_override_count()} dangerous operations")
"""

import logging
from datetime import datetime
from typing import TypedDict

from adw.security.patterns import PatternMatch


class OverrideRecord(TypedDict):
    """Record of an overridden security block."""

    match: PatternMatch
    command: str | None
    file_path: str | None
    timestamp: str


# Module logger for security warnings
_logger = logging.getLogger("adw.security.override")


class OverrideLogger:
    """Logs and tracks security overrides when --allow-dangerous is active.

    The OverrideLogger maintains a list of all blocked patterns that were
    allowed during a run. Each override is logged as a warning and recorded
    for run-level summary reporting.

    Attributes:
        overrides: List of all recorded overrides

    Example:
        >>> logger = OverrideLogger()
        >>> match = PatternMatch(...)
        >>> logger.log_override(match, command="rm -rf /tmp")
        >>> logger.get_override_count()
        1
    """

    def __init__(self) -> None:
        """Initialize the override logger."""
        self._overrides: list[OverrideRecord] = []

    @property
    def overrides(self) -> list[OverrideRecord]:
        """Get all recorded overrides.

        Returns:
            List of OverrideRecord dictionaries
        """
        return list(self._overrides)

    def log_override(
        self,
        match: PatternMatch,
        *,
        command: str | None = None,
        file_path: str | None = None,
    ) -> None:
        """Log an overridden security block.

        Emits a warning log message and records the override for later
        summary reporting.

        Args:
            match: The PatternMatch that was overridden
            command: The shell command that was allowed (optional)
            file_path: The file path that was allowed (optional)

        Example:
            >>> logger = OverrideLogger()
            >>> match = PatternMatch(
            ...     pattern=r"rm\\s+-rf",
            ...     description="Recursive delete",
            ...     severity="critical",
            ...     category="destructive",
            ...     alternative="Use specific paths",
            ...     allowed=True,
            ... )
            >>> logger.log_override(match, command="rm -rf /tmp")
        """
        record: OverrideRecord = {
            "match": match,
            "command": command,
            "file_path": file_path,
            "timestamp": datetime.now().isoformat(),
        }
        self._overrides.append(record)

        # Log warning with structured context
        _logger.warning(
            "[ALLOW-DANGEROUS] %s: %s (context: %s)",
            match.category.upper(),
            match.description,
            command if command else file_path,
            extra={
                "pattern": match.pattern,
                "severity": match.severity,
                "category": match.category,
                "command": command,
                "file_path": file_path,
            },
        )

    def get_override_count(self) -> int:
        """Get the total number of recorded overrides.

        Returns:
            Count of overridden security blocks
        """
        return len(self._overrides)

    def get_overrides_by_category(self, category: str) -> list[OverrideRecord]:
        """Get overrides filtered by category.

        Args:
            category: The category to filter by (e.g., "destructive")

        Returns:
            List of matching OverrideRecord dictionaries
        """
        return [o for o in self._overrides if o["match"].category == category]

    def get_summary(self) -> str:
        """Get a human-readable summary of all overrides.

        Returns:
            Formatted summary string

        Example:
            >>> logger = OverrideLogger()
            >>> logger.get_summary()
            'No security blocks were overridden.'
        """
        count = len(self._overrides)
        if count == 0:
            return "No security blocks were overridden."

        # Count by category
        by_category: dict[str, int] = {}
        for override in self._overrides:
            cat = override["match"].category
            by_category[cat] = by_category.get(cat, 0) + 1

        # Count by severity
        by_severity: dict[str, int] = {}
        for override in self._overrides:
            sev = override["match"].severity
            by_severity[sev] = by_severity.get(sev, 0) + 1

        lines = [
            f"⚠️  {count} security block(s) were overridden (--allow-dangerous active)",
            "",
            "By category:",
        ]

        for cat, cat_count in sorted(by_category.items()):
            lines.append(f"  - {cat}: {cat_count}")

        lines.append("")
        lines.append("By severity:")
        for sev, sev_count in sorted(by_severity.items()):
            lines.append(f"  - {sev}: {sev_count}")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all recorded overrides.

        Useful for resetting between runs or for testing.
        """
        self._overrides.clear()


# Module-level default override logger instance
_default_logger: OverrideLogger | None = None


def get_override_logger() -> OverrideLogger:
    """Get the default override logger instance.

    Returns a module-level OverrideLogger instance, creating it on first call.

    Returns:
        The default OverrideLogger instance
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = OverrideLogger()
    return _default_logger


def reset_override_logger() -> None:
    """Reset the default override logger instance.

    Clears the module-level override logger, allowing a fresh instance
    to be created on the next get_override_logger() call.
    """
    global _default_logger
    if _default_logger is not None:
        _default_logger.clear()
    _default_logger = None
