"""Tests for RetryConfig model."""

import pytest
from pydantic import ValidationError

from adw.models.config import RetryConfig


class TestRetryConfig:
    """Tests for RetryConfig model."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay_seconds == 1.0
        assert config.max_delay_seconds == 60.0
        assert config.multiplier == 2.0

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = RetryConfig(
            max_retries=5,
            base_delay_seconds=0.5,
            max_delay_seconds=120.0,
            multiplier=3.0,
        )

        assert config.max_retries == 5
        assert config.base_delay_seconds == 0.5
        assert config.max_delay_seconds == 120.0
        assert config.multiplier == 3.0

    def test_max_retries_must_be_positive(self) -> None:
        """Test that max_retries must be positive."""
        with pytest.raises(ValidationError):
            RetryConfig(max_retries=0)

        with pytest.raises(ValidationError):
            RetryConfig(max_retries=-1)

    def test_base_delay_must_be_positive(self) -> None:
        """Test that base_delay_seconds must be positive."""
        with pytest.raises(ValidationError):
            RetryConfig(base_delay_seconds=0)

        with pytest.raises(ValidationError):
            RetryConfig(base_delay_seconds=-0.5)

    def test_max_delay_must_be_positive(self) -> None:
        """Test that max_delay_seconds must be positive."""
        with pytest.raises(ValidationError):
            RetryConfig(max_delay_seconds=0)

    def test_multiplier_must_be_greater_than_one(self) -> None:
        """Test that multiplier must be > 1."""
        with pytest.raises(ValidationError):
            RetryConfig(multiplier=1.0)

        with pytest.raises(ValidationError):
            RetryConfig(multiplier=0.5)

    def test_max_delay_must_be_gte_base_delay(self) -> None:
        """Test that max_delay_seconds must be >= base_delay_seconds."""
        with pytest.raises(ValidationError):
            RetryConfig(base_delay_seconds=10.0, max_delay_seconds=5.0)


class TestLLMConfigRetryField:
    """Tests for LLMConfig.retry field."""

    def test_llm_config_has_retry_field_with_defaults(self) -> None:
        """Test that LLMConfig has a retry field with default RetryConfig."""
        from adw.models.config import LLMConfig

        config = LLMConfig()

        assert isinstance(config.retry, RetryConfig)
        assert config.retry.max_retries == 3
        assert config.retry.base_delay_seconds == 1.0
        assert config.retry.max_delay_seconds == 60.0
        assert config.retry.multiplier == 2.0

    def test_llm_config_retry_parses_from_dict(self) -> None:
        """Test that LLMConfig.retry can be parsed from a dictionary."""
        from adw.models.config import LLMConfig

        config = LLMConfig.model_validate(
            {
                "path": "claude",
                "timeout_seconds": 600,
                "retry": {
                    "max_retries": 5,
                    "base_delay_seconds": 2.0,
                    "max_delay_seconds": 120.0,
                    "multiplier": 3.0,
                },
            }
        )

        assert config.retry.max_retries == 5
        assert config.retry.base_delay_seconds == 2.0
        assert config.retry.max_delay_seconds == 120.0
        assert config.retry.multiplier == 3.0

    def test_llm_config_without_retry_key_uses_defaults(self) -> None:
        """Test backward compat: LLMConfig without retry key gets defaults."""
        from adw.models.config import LLMConfig

        config = LLMConfig.model_validate(
            {
                "path": "/usr/bin/claude",
                "timeout_seconds": 300,
            }
        )

        assert isinstance(config.retry, RetryConfig)
        assert config.retry.max_retries == 3
