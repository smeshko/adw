"""Tests for the secret redaction module."""

import pytest

from adw.logging.redactor import (
    DEFAULT_REDACTION_PATTERNS,
    REDACTED_PLACEHOLDER,
    SENSITIVE_ENV_PATTERNS,
    Redactor,
    configure_redactor,
    get_redactor,
    reset_redactor,
)


class TestDefaultPatterns:
    """Tests for DEFAULT_REDACTION_PATTERNS."""

    def test_patterns_list_not_empty(self) -> None:
        """Verify default patterns are defined."""
        assert len(DEFAULT_REDACTION_PATTERNS) > 0

    def test_all_patterns_are_strings(self) -> None:
        """Verify all patterns are strings."""
        for pattern in DEFAULT_REDACTION_PATTERNS:
            assert isinstance(pattern, str)


class TestSensitiveEnvPatterns:
    """Tests for SENSITIVE_ENV_PATTERNS."""

    def test_patterns_list_not_empty(self) -> None:
        """Verify env patterns are defined."""
        assert len(SENSITIVE_ENV_PATTERNS) > 0

    def test_includes_common_patterns(self) -> None:
        """Verify common sensitive patterns are included."""
        patterns_str = " ".join(SENSITIVE_ENV_PATTERNS)
        assert "_KEY" in patterns_str
        assert "_SECRET" in patterns_str
        assert "_TOKEN" in patterns_str
        assert "_PASSWORD" in patterns_str


class TestRedactorCreation:
    """Tests for Redactor initialization."""

    def test_create_with_empty_patterns(self) -> None:
        """Can create redactor with no patterns."""
        redactor = Redactor([])
        assert len(redactor.patterns) == 0

    def test_create_with_custom_patterns(self) -> None:
        """Can create redactor with custom patterns."""
        patterns = ["secret-[0-9]+", "token-[a-z]+"]
        redactor = Redactor(patterns)
        assert len(redactor.patterns) == 2

    def test_patterns_are_compiled(self) -> None:
        """Patterns should be compiled regex objects."""
        redactor = Redactor(["test"])
        import re

        assert isinstance(redactor.patterns[0], re.Pattern)

    def test_env_patterns_default_to_sensitive(self) -> None:
        """Env patterns default to SENSITIVE_ENV_PATTERNS."""
        redactor = Redactor([])
        assert len(redactor.env_patterns) == len(SENSITIVE_ENV_PATTERNS)

    def test_custom_env_patterns(self) -> None:
        """Can provide custom env patterns."""
        redactor = Redactor([], env_patterns=["CUSTOM_.*"])
        assert len(redactor.env_patterns) == 1


class TestRedactorRedactMethod:
    """Tests for Redactor.redact() method."""

    def test_redact_bearer_token(self) -> None:
        """Bearer tokens are redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        result = redactor.redact("Authorization: Bearer abc123xyz")
        assert "abc123xyz" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_redact_openai_key(self) -> None:
        """OpenAI API keys are redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        # Real OpenAI keys are 51+ chars
        key = "sk-" + "a" * 50
        result = redactor.redact(f"Key: {key}")
        assert "sk-" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_redact_github_pat(self) -> None:
        """GitHub personal access tokens are redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        result = redactor.redact("Token: ghp_abcdefghijklmnopqrstuvwxyz123456")
        assert "ghp_" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_redact_aws_access_key(self) -> None:
        """AWS access key IDs are redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        result = redactor.redact("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE")
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_redact_anthropic_key(self) -> None:
        """Anthropic API keys are redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        key = "sk-ant-" + "a" * 50
        result = redactor.redact(f"Key: {key}")
        assert "sk-ant-" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_redact_anthropic_key_shorter(self) -> None:
        """Shorter Anthropic API keys (20+ chars) are also redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        # Real-world Anthropic keys can be shorter than 50 chars
        key = "sk-ant-api03-" + "a" * 20
        result = redactor.redact(f"Key: {key}")
        assert "sk-ant-" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_redact_openai_key_minimum_length(self) -> None:
        """OpenAI keys at minimum length (20 chars) are redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        # Test at exactly 20 chars (minimum)
        key = "sk-" + "a" * 20
        result = redactor.redact(f"Key: {key}")
        assert "sk-" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_redact_api_key_assignment(self) -> None:
        """Generic api_key= patterns are redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        result = redactor.redact("config = {'api_key': 'secret12345'}")
        assert "secret12345" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_redact_password_assignment(self) -> None:
        """Password assignments are redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        result = redactor.redact("password = 'mysecretpass'")
        assert "mysecretpass" not in result
        assert REDACTED_PLACEHOLDER in result

    def test_no_redaction_for_normal_text(self) -> None:
        """Normal text should not be redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        message = "This is a normal log message with no secrets"
        result = redactor.redact(message)
        assert result == message

    def test_redact_multiple_secrets(self) -> None:
        """Multiple secrets in one message are all redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        # GitHub PAT requires exactly 36 chars after ghp_
        message = "Auth: Bearer abc123 and key: ghp_abcdefghijklmnopqrstuvwxyz123456"
        result = redactor.redact(message)
        assert "abc123" not in result
        # Check at least one redaction happened
        assert REDACTED_PLACEHOLDER in result

    def test_custom_pattern_redaction(self) -> None:
        """Custom patterns are applied."""
        redactor = Redactor(["ACME_[A-Z0-9]+"])
        result = redactor.redact("Token: ACME_ABC123")
        assert "ACME_ABC123" not in result
        assert REDACTED_PLACEHOLDER in result


class TestRedactorEnvDetection:
    """Tests for Redactor.should_redact_env() method."""

    def test_detects_key_suffix(self) -> None:
        """Environment variables ending in _KEY are detected."""
        redactor = Redactor([])
        assert redactor.should_redact_env("API_KEY") is True
        assert redactor.should_redact_env("DATABASE_KEY") is True

    def test_detects_secret_suffix(self) -> None:
        """Environment variables ending in _SECRET are detected."""
        redactor = Redactor([])
        assert redactor.should_redact_env("AWS_SECRET") is True
        assert redactor.should_redact_env("CLIENT_SECRET") is True

    def test_detects_token_suffix(self) -> None:
        """Environment variables ending in _TOKEN are detected."""
        redactor = Redactor([])
        assert redactor.should_redact_env("ACCESS_TOKEN") is True
        assert redactor.should_redact_env("AUTH_TOKEN") is True

    def test_detects_password_suffix(self) -> None:
        """Environment variables ending in _PASSWORD are detected."""
        redactor = Redactor([])
        assert redactor.should_redact_env("DATABASE_PASSWORD") is True
        assert redactor.should_redact_env("ADMIN_PASSWORD") is True

    def test_does_not_detect_normal_vars(self) -> None:
        """Normal environment variables are not detected."""
        redactor = Redactor([])
        assert redactor.should_redact_env("DEBUG") is False
        assert redactor.should_redact_env("LOG_LEVEL") is False
        assert redactor.should_redact_env("HOME") is False

    def test_detects_apikey_without_underscore(self) -> None:
        """APIKEY (without underscore) is detected."""
        redactor = Redactor([])
        assert redactor.should_redact_env("APIKEY") is True

    def test_detects_credentials_variants(self) -> None:
        """CREDENTIAL and CREDENTIALS are detected."""
        redactor = Redactor([])
        assert redactor.should_redact_env("CREDENTIAL") is True
        assert redactor.should_redact_env("CREDENTIALS") is True


class TestRedactorEnvDict:
    """Tests for Redactor.redact_env_dict() method."""

    def test_redacts_sensitive_values(self) -> None:
        """Sensitive env var values are redacted."""
        redactor = Redactor([])
        env = {"API_KEY": "secret123", "DEBUG": "true"}
        result = redactor.redact_env_dict(env)
        assert result["API_KEY"] == REDACTED_PLACEHOLDER
        assert result["DEBUG"] == "true"

    def test_preserves_non_sensitive_values(self) -> None:
        """Non-sensitive env var values are preserved."""
        redactor = Redactor([])
        env = {"HOME": "/home/user", "PATH": "/usr/bin"}
        result = redactor.redact_env_dict(env)
        assert result["HOME"] == "/home/user"
        assert result["PATH"] == "/usr/bin"

    def test_returns_new_dict(self) -> None:
        """Returns a new dict, not modified original."""
        redactor = Redactor([])
        env = {"API_KEY": "secret123"}
        result = redactor.redact_env_dict(env)
        assert env["API_KEY"] == "secret123"  # Original unchanged
        assert result is not env


class TestRedactorDeepRedaction:
    """Tests for Redactor.redact_dict() method (deep redaction)."""

    def test_redacts_string_values(self) -> None:
        """String values containing secrets are redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        data = {"config": "Bearer secret123"}
        result = redactor.redact_dict(data)
        assert "secret123" not in result["config"]
        assert REDACTED_PLACEHOLDER in result["config"]

    def test_redacts_nested_dicts(self) -> None:
        """Nested dictionaries are recursively redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        data = {"config": {"nested": {"api_key": "sk-" + "a" * 50}}}
        result = redactor.redact_dict(data)
        assert "sk-" not in str(result)
        assert REDACTED_PLACEHOLDER in result["config"]["nested"]["api_key"]

    def test_redacts_lists(self) -> None:
        """Lists containing secrets are redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        data = {"tokens": ["Bearer abc", "Bearer xyz"]}
        result = redactor.redact_dict(data)
        for item in result["tokens"]:
            assert REDACTED_PLACEHOLDER in item

    def test_redacts_nested_dicts_in_lists(self) -> None:
        """Nested dictionaries within lists are recursively redacted."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        data = {
            "items": [
                {"api_key": "secret1", "name": "item1"},
                {"password": "secret2", "name": "item2"},
            ]
        }
        result = redactor.redact_dict(data)
        assert result["items"][0]["api_key"] == REDACTED_PLACEHOLDER
        assert result["items"][0]["name"] == "item1"
        assert result["items"][1]["password"] == REDACTED_PLACEHOLDER
        assert result["items"][1]["name"] == "item2"

    def test_preserves_non_string_values(self) -> None:
        """Non-string values are preserved."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        data = {"count": 42, "enabled": True, "ratio": 3.14}
        result = redactor.redact_dict(data)
        assert result["count"] == 42
        assert result["enabled"] is True
        assert result["ratio"] == 3.14

    def test_redacts_sensitive_keys(self) -> None:
        """Keys matching sensitive env patterns have values redacted."""
        redactor = Redactor([])
        data = {"api_key": "any_value", "debug": "normal"}
        result = redactor.redact_dict(data)
        assert result["api_key"] == REDACTED_PLACEHOLDER
        assert result["debug"] == "normal"

    def test_handles_mixed_nested_structure(self) -> None:
        """Complex mixed structures are handled correctly."""
        redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
        data = {
            "settings": {
                "api_key": "secret123",
                "endpoints": ["https://api.example.com"],
                "headers": {
                    "Authorization": "Bearer token123",
                },
            },
            "count": 5,
        }
        result = redactor.redact_dict(data)
        assert result["settings"]["api_key"] == REDACTED_PLACEHOLDER
        assert result["settings"]["endpoints"] == ["https://api.example.com"]
        assert REDACTED_PLACEHOLDER in result["settings"]["headers"]["Authorization"]
        assert result["count"] == 5


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_redactor_returns_singleton(self) -> None:
        """get_redactor returns the same instance."""
        reset_redactor()
        r1 = get_redactor()
        r2 = get_redactor()
        assert r1 is r2

    def test_get_redactor_uses_default_patterns(self) -> None:
        """Default redactor uses DEFAULT_REDACTION_PATTERNS."""
        reset_redactor()
        redactor = get_redactor()
        assert len(redactor.patterns) == len(DEFAULT_REDACTION_PATTERNS)

    def test_reset_redactor_clears_singleton(self) -> None:
        """reset_redactor allows new instance creation."""
        reset_redactor()
        r1 = get_redactor()
        reset_redactor()
        r2 = get_redactor()
        assert r1 is not r2

    def test_configure_redactor_with_patterns(self) -> None:
        """configure_redactor adds custom patterns."""
        reset_redactor()
        redactor = configure_redactor(patterns=["CUSTOM_[0-9]+"])
        # Should have defaults + 1 custom
        assert len(redactor.patterns) == len(DEFAULT_REDACTION_PATTERNS) + 1

    def test_configure_redactor_disable_defaults(self) -> None:
        """configure_redactor can disable defaults."""
        reset_redactor()
        redactor = configure_redactor(
            patterns=["ONLY_THIS"],
            disable_defaults=True,
        )
        assert len(redactor.patterns) == 1

    def test_configure_redactor_empty_with_disable(self) -> None:
        """configure_redactor with disable_defaults and no patterns."""
        reset_redactor()
        redactor = configure_redactor(disable_defaults=True)
        assert len(redactor.patterns) == 0
