# REDUCED: Removed TestPackageExports (import verification) and test_reset_logger_exported.
# Kept only tests that verify actual logging behavior.
"""Tests for the logging package convenience functions."""

from adw.logging import (
    LogManager,
    Redactor,
    create_redactor_from_config,
    get_logger,
    reset_logger,
)


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_log_manager(self) -> None:
        """get_logger returns a LogManager instance."""
        reset_logger()

        logger = get_logger()
        assert isinstance(logger, LogManager)

    def test_get_logger_returns_same_instance(self) -> None:
        """get_logger returns the same instance on repeated calls."""
        reset_logger()

        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2


class TestCreateRedactorFromConfig:
    """Tests for create_redactor_from_config function."""

    def test_enabled_returns_redactor(self) -> None:
        """When enabled (default), returns a Redactor instance."""
        redactor = create_redactor_from_config()
        assert isinstance(redactor, Redactor)

    def test_disabled_returns_none(self) -> None:
        """When disabled, returns None."""
        redactor = create_redactor_from_config(enabled=False)
        assert redactor is None

    def test_custom_patterns_merged_with_defaults(self) -> None:
        """Custom patterns are merged with default patterns."""
        redactor = create_redactor_from_config(patterns=["CUSTOM_SECRET_[A-Z]+"])
        assert redactor is not None
        # Should have default patterns plus the custom one
        assert len(redactor.patterns) > 1

    def test_disable_defaults_uses_only_custom(self) -> None:
        """When disable_defaults=True, only custom patterns are used."""
        redactor = create_redactor_from_config(
            patterns=["MY_PATTERN_[0-9]+"],
            disable_defaults=True,
        )
        assert redactor is not None
        assert len(redactor.patterns) == 1

    def test_disable_defaults_no_patterns_returns_empty(self) -> None:
        """When disable_defaults=True with no patterns, returns redactor with no patterns."""
        redactor = create_redactor_from_config(disable_defaults=True)
        assert redactor is not None
        assert len(redactor.patterns) == 0


class TestResetLogger:
    """Tests for reset_logger function."""

    def test_reset_logger_clears_default(self) -> None:
        """reset_logger clears the default logger."""
        reset_logger()
        logger1 = get_logger()

        reset_logger()
        logger2 = get_logger()

        assert logger1 is not logger2
