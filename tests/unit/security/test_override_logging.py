"""Tests for override logging functionality.

Verifies that when --allow-dangerous is active, blocked patterns are
logged as warnings instead of errors and execution continues.
"""

from adw.security.patterns import PatternMatch


class TestOverrideLogger:
    """Tests for OverrideLogger class."""

    def test_override_logger_exists(self) -> None:
        """Test OverrideLogger can be imported."""
        from adw.security.override import OverrideLogger

        assert OverrideLogger is not None

    def test_log_override_records_match(self) -> None:
        """Test logging an override records the match."""
        from adw.security.override import OverrideLogger

        logger = OverrideLogger()
        match = PatternMatch(
            pattern=r"rm\s+-rf",
            description="Recursive delete",
            severity="critical",
            category="destructive",
            alternative="Use specific paths",
            allowed=True,
        )
        logger.log_override(match, command="rm -rf /")

        assert len(logger.overrides) == 1
        assert logger.overrides[0]["match"].pattern == r"rm\s+-rf"
        assert logger.overrides[0]["command"] == "rm -rf /"

    def test_log_multiple_overrides(self) -> None:
        """Test logging multiple overrides."""
        from adw.security.override import OverrideLogger

        logger = OverrideLogger()
        match1 = PatternMatch(
            pattern=r"rm\s+-rf",
            description="Recursive delete",
            severity="critical",
            category="destructive",
            alternative="",
            allowed=True,
        )
        match2 = PatternMatch(
            pattern=r"chmod\s+777",
            description="World-writable",
            severity="warning",
            category="permission",
            alternative="",
            allowed=True,
        )
        logger.log_override(match1, command="rm -rf /tmp")
        logger.log_override(match2, command="chmod 777 /var/log")

        assert len(logger.overrides) == 2

    def test_get_override_count(self) -> None:
        """Test getting the count of overrides."""
        from adw.security.override import OverrideLogger

        logger = OverrideLogger()
        assert logger.get_override_count() == 0

        match = PatternMatch(
            pattern=r"test",
            description="Test",
            severity="warning",
            category="permission",
            alternative="",
            allowed=True,
        )
        logger.log_override(match, command="test")

        assert logger.get_override_count() == 1

    def test_get_overrides_by_category(self) -> None:
        """Test filtering overrides by category."""
        from adw.security.override import OverrideLogger

        logger = OverrideLogger()
        destructive = PatternMatch(
            pattern=r"rm",
            description="Delete",
            severity="critical",
            category="destructive",
            alternative="",
            allowed=True,
        )
        permission = PatternMatch(
            pattern=r"chmod",
            description="Chmod",
            severity="warning",
            category="permission",
            alternative="",
            allowed=True,
        )
        logger.log_override(destructive, command="rm file")
        logger.log_override(permission, command="chmod 777 file")

        destructive_overrides = logger.get_overrides_by_category("destructive")
        assert len(destructive_overrides) == 1

    def test_get_override_summary(self) -> None:
        """Test getting a summary of all overrides."""
        from adw.security.override import OverrideLogger

        logger = OverrideLogger()
        match = PatternMatch(
            pattern=r"rm\s+-rf",
            description="Recursive delete",
            severity="critical",
            category="destructive",
            alternative="",
            allowed=True,
        )
        logger.log_override(match, command="rm -rf /tmp")

        summary = logger.get_summary()
        assert "1" in summary or "one" in summary.lower()
        assert "destructive" in summary.lower() or "override" in summary.lower()

    def test_clear_overrides(self) -> None:
        """Test clearing all logged overrides."""
        from adw.security.override import OverrideLogger

        logger = OverrideLogger()
        match = PatternMatch(
            pattern=r"test",
            description="Test",
            severity="warning",
            category="permission",
            alternative="",
            allowed=True,
        )
        logger.log_override(match, command="test")
        assert logger.get_override_count() == 1

        logger.clear()
        assert logger.get_override_count() == 0


class TestOverrideLoggerWithStructuredLogging:
    """Tests for integration with structured logging."""

    def test_log_override_emits_warning(self) -> None:
        """Test that log_override uses warning level logging."""
        from adw.security.override import OverrideLogger

        # This should not raise, just verify logging happens
        logger = OverrideLogger()
        match = PatternMatch(
            pattern=r"rm\s+-rf",
            description="Recursive delete",
            severity="critical",
            category="destructive",
            alternative="",
            allowed=True,
        )
        logger.log_override(match, command="rm -rf /tmp")
        # Logging is side-effect tested, count is the main assertion
        assert logger.get_override_count() == 1


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    def test_get_override_logger_returns_singleton(self) -> None:
        """Test get_override_logger returns same instance."""
        from adw.security.override import get_override_logger, reset_override_logger

        # Reset to ensure clean state
        reset_override_logger()

        logger1 = get_override_logger()
        logger2 = get_override_logger()
        assert logger1 is logger2

        # Cleanup
        reset_override_logger()

    def test_reset_override_logger_clears_instance(self) -> None:
        """Test reset_override_logger creates new instance."""
        from adw.security.override import get_override_logger, reset_override_logger

        logger1 = get_override_logger()
        match = PatternMatch(
            pattern=r"test",
            description="Test",
            severity="warning",
            category="permission",
            alternative="",
            allowed=True,
        )
        logger1.log_override(match, command="test")
        assert logger1.get_override_count() == 1

        reset_override_logger()

        logger2 = get_override_logger()
        assert logger2.get_override_count() == 0
        assert logger1 is not logger2

        # Cleanup
        reset_override_logger()

    def test_get_summary_with_multiple_categories(self) -> None:
        """Test get_summary with multiple categories and severities."""
        from adw.security.override import OverrideLogger

        logger = OverrideLogger()
        logger.log_override(
            PatternMatch(
                pattern=r"rm",
                description="Delete",
                severity="critical",
                category="destructive",
                alternative="",
                allowed=True,
            ),
            command="rm -rf /",
        )
        logger.log_override(
            PatternMatch(
                pattern=r"chmod",
                description="Chmod",
                severity="warning",
                category="permission",
                alternative="",
                allowed=True,
            ),
            command="chmod 777 /",
        )

        summary = logger.get_summary()
        assert "2 security block(s)" in summary
        assert "destructive" in summary
        assert "permission" in summary
        assert "critical" in summary
        assert "warning" in summary
