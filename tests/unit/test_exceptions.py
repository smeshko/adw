"""Unit tests for ADW exception hierarchy."""

import pytest

from adw.exceptions import (
    ADWError,
    CommandError,
    ConfigError,
    HookError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    PhaseError,
    StateError,
    ValidationError,
)


class TestADWErrorBase:
    """Tests for ADWError base class."""

    def test_adw_error_required_attributes(self) -> None:
        """ADWError has required attributes."""
        error = ADWError(
            code="TEST_ERROR",
            message="Test message",
            suggestion="Try again",
            recoverable=True,
        )
        assert error.code == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.suggestion == "Try again"
        assert error.recoverable is True

    def test_adw_error_default_values(self) -> None:
        """ADWError has sensible defaults."""
        error = ADWError(
            code="TEST_ERROR",
            message="Test message",
        )
        assert error.suggestion is None
        assert error.recoverable is False

    def test_adw_error_str_format_with_suggestion(self) -> None:
        """ADWError formats nicely with suggestion for display."""
        error = ADWError(
            code="TEST_ERROR",
            message="Something failed",
            suggestion="Check logs",
        )
        formatted = str(error)
        assert "[TEST_ERROR]" in formatted
        assert "Something failed" in formatted
        assert "Suggestion: Check logs" in formatted

    def test_adw_error_str_format_without_suggestion(self) -> None:
        """ADWError formats correctly without suggestion."""
        error = ADWError(
            code="TEST_ERROR",
            message="Something failed",
        )
        formatted = str(error)
        assert "[TEST_ERROR]" in formatted
        assert "Something failed" in formatted
        assert "Suggestion:" not in formatted

    def test_adw_error_to_dict(self) -> None:
        """ADWError serializes to dict for structured logging."""
        error = ADWError(
            code="TEST",
            message="Test",
            suggestion="Fix it",
            recoverable=True,
        )
        d = error.to_dict()
        assert d["code"] == "TEST"
        assert d["message"] == "Test"
        assert d["suggestion"] == "Fix it"
        assert d["recoverable"] is True

    def test_adw_error_to_dict_without_suggestion(self) -> None:
        """ADWError to_dict includes None for missing suggestion."""
        error = ADWError(
            code="TEST",
            message="Test",
        )
        d = error.to_dict()
        assert d["suggestion"] is None
        assert d["recoverable"] is False

    def test_adw_error_is_exception(self) -> None:
        """ADWError is a proper Exception subclass."""
        error = ADWError(
            code="TEST_ERROR",
            message="Test message",
        )
        assert isinstance(error, Exception)

    def test_adw_error_can_be_raised(self) -> None:
        """ADWError can be raised and caught."""
        with pytest.raises(ADWError) as exc_info:
            raise ADWError(
                code="RAISED_ERROR",
                message="This was raised",
            )
        assert exc_info.value.code == "RAISED_ERROR"
        assert exc_info.value.message == "This was raised"


class TestConfigError:
    """Tests for ConfigError exception."""

    def test_config_error_is_adw_error(self) -> None:
        """ConfigError inherits from ADWError."""
        error = ConfigError(
            code="CONFIG_NOT_FOUND",
            message="Config file not found",
        )
        assert isinstance(error, ADWError)
        assert isinstance(error, Exception)

    def test_config_error_not_recoverable_by_default(self) -> None:
        """ConfigError is not recoverable by default."""
        error = ConfigError(
            code="CONFIG_NOT_FOUND",
            message="Config file not found",
        )
        assert error.recoverable is False

    def test_config_error_with_suggestion(self) -> None:
        """ConfigError accepts suggestion."""
        error = ConfigError(
            code="CONFIG_NOT_FOUND",
            message="Config file not found",
            suggestion="Create an adw.yaml file",
        )
        assert error.suggestion == "Create an adw.yaml file"
        assert "Suggestion:" in str(error)

    def test_config_error_common_codes(self) -> None:
        """ConfigError works with common error codes."""
        codes = ["CONFIG_NOT_FOUND", "INVALID_CONFIG", "COMMAND_NOT_FOUND"]
        for code in codes:
            error = ConfigError(code=code, message=f"Error with {code}")
            assert error.code == code

    def test_config_error_to_dict(self) -> None:
        """ConfigError serializes properly."""
        error = ConfigError(
            code="INVALID_CONFIG",
            message="Invalid configuration",
            suggestion="Check your adw.yaml",
        )
        d = error.to_dict()
        assert d["code"] == "INVALID_CONFIG"
        assert d["recoverable"] is False


class TestCommandError:
    """Tests for CommandError exception."""

    def test_command_error_is_adw_error(self) -> None:
        """CommandError inherits from ADWError."""
        error = CommandError(
            code="COMMAND_NOT_FOUND",
            message="Command not found",
        )
        assert isinstance(error, ADWError)
        assert isinstance(error, Exception)

    def test_command_error_not_recoverable_by_default(self) -> None:
        """CommandError is not recoverable by default."""
        error = CommandError(
            code="COMMAND_NOT_FOUND",
            message="Command not found",
        )
        assert error.recoverable is False

    def test_command_error_with_suggestion(self) -> None:
        """CommandError accepts suggestion."""
        error = CommandError(
            code="COMMAND_NOT_FOUND",
            message="Command 'deploy' not found",
            suggestion="Check available commands with 'adw list-commands'",
        )
        assert error.suggestion == "Check available commands with 'adw list-commands'"
        assert "Suggestion:" in str(error)

    def test_command_error_common_codes(self) -> None:
        """CommandError works with common error codes."""
        codes = ["COMMAND_NOT_FOUND", "COMMAND_INVALID", "COMMAND_LOAD_FAILED"]
        for code in codes:
            error = CommandError(code=code, message=f"Error with {code}")
            assert error.code == code

    def test_command_error_to_dict(self) -> None:
        """CommandError serializes properly."""
        error = CommandError(
            code="COMMAND_NOT_FOUND",
            message="Command not found",
            suggestion="Check your commands",
        )
        d = error.to_dict()
        assert d["code"] == "COMMAND_NOT_FOUND"
        assert d["recoverable"] is False


class TestHookError:
    """Tests for HookError exception."""

    def test_hook_error_is_adw_error(self) -> None:
        """HookError inherits from ADWError."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
        )
        assert isinstance(error, ADWError)
        assert isinstance(error, Exception)

    def test_hook_error_has_phase_field(self) -> None:
        """HookError includes phase field."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
        )
        assert error.phase == "build"

    def test_hook_error_has_exit_code(self) -> None:
        """HookError includes exit_code field."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
            exit_code=1,
        )
        assert error.exit_code == 1

    def test_hook_error_exit_code_default_none(self) -> None:
        """HookError exit_code defaults to None."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
        )
        assert error.exit_code is None

    def test_hook_error_has_stdout_stderr(self) -> None:
        """HookError includes stdout and stderr fields."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
            stdout="output text",
            stderr="error text",
        )
        assert error.stdout == "output text"
        assert error.stderr == "error text"

    def test_hook_error_stdout_stderr_defaults(self) -> None:
        """HookError stdout and stderr default to empty string."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
        )
        assert error.stdout == ""
        assert error.stderr == ""

    def test_hook_error_not_recoverable_by_default(self) -> None:
        """HookError is not recoverable by default."""
        error = HookError(
            code="HOOK_FAILED",
            message="Pre-hook failed",
            phase="build",
        )
        assert error.recoverable is False

    def test_hook_error_common_codes(self) -> None:
        """HookError works with common error codes."""
        codes = ["HOOK_FAILED", "HOOK_TIMEOUT"]
        for code in codes:
            error = HookError(code=code, message=f"Error with {code}", phase="test")
            assert error.code == code

    def test_hook_error_to_dict_includes_extra_fields(self) -> None:
        """HookError to_dict includes phase, exit_code, stdout, stderr."""
        error = HookError(
            code="HOOK_FAILED",
            message="Failed",
            phase="build",
            exit_code=1,
            stdout="out",
            stderr="err",
        )
        d = error.to_dict()
        assert d["phase"] == "build"
        assert d["exit_code"] == 1
        assert d["stdout"] == "out"
        assert d["stderr"] == "err"


class TestLLMError:
    """Tests for LLMError exception hierarchy."""

    def test_llm_error_is_adw_error(self) -> None:
        """LLMError inherits from ADWError."""
        error = LLMError(
            code="LLM_ERROR",
            message="LLM call failed",
        )
        assert isinstance(error, ADWError)
        assert isinstance(error, Exception)

    def test_llm_error_not_recoverable_by_default(self) -> None:
        """LLMError is not recoverable by default."""
        error = LLMError(
            code="LLM_ERROR",
            message="LLM call failed",
        )
        assert error.recoverable is False


class TestLLMTimeoutError:
    """Tests for LLMTimeoutError exception."""

    def test_llm_timeout_error_is_llm_error(self) -> None:
        """LLMTimeoutError inherits from LLMError."""
        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout after 300s",
            timeout_seconds=300,
            elapsed_seconds=300,
        )
        assert isinstance(error, LLMError)
        assert isinstance(error, ADWError)
        assert isinstance(error, Exception)

    def test_llm_timeout_error_is_recoverable_by_default(self) -> None:
        """LLMTimeoutError is recoverable by default."""
        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout after 300s",
            timeout_seconds=300,
            elapsed_seconds=300,
        )
        assert error.recoverable is True

    def test_llm_timeout_error_has_timeout_fields(self) -> None:
        """LLMTimeoutError includes timeout_seconds and elapsed_seconds."""
        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            timeout_seconds=300,
            elapsed_seconds=299,
        )
        assert error.timeout_seconds == 300
        assert error.elapsed_seconds == 299

    def test_llm_timeout_error_to_dict_includes_extra_fields(self) -> None:
        """LLMTimeoutError to_dict includes timeout fields."""
        error = LLMTimeoutError(
            code="LLM_TIMEOUT",
            message="Timeout",
            timeout_seconds=300,
            elapsed_seconds=299,
        )
        d = error.to_dict()
        assert d["timeout_seconds"] == 300
        assert d["elapsed_seconds"] == 299


class TestLLMRateLimitError:
    """Tests for LLMRateLimitError exception."""

    def test_llm_rate_limit_error_is_llm_error(self) -> None:
        """LLMRateLimitError inherits from LLMError."""
        error = LLMRateLimitError(
            code="LLM_RATE_LIMIT",
            message="Rate limited",
        )
        assert isinstance(error, LLMError)
        assert isinstance(error, ADWError)
        assert isinstance(error, Exception)

    def test_llm_rate_limit_error_is_recoverable_by_default(self) -> None:
        """LLMRateLimitError is recoverable by default."""
        error = LLMRateLimitError(
            code="LLM_RATE_LIMIT",
            message="Rate limited",
        )
        assert error.recoverable is True

    def test_llm_rate_limit_error_has_retry_after(self) -> None:
        """LLMRateLimitError includes retry_after field."""
        error = LLMRateLimitError(
            code="LLM_RATE_LIMIT",
            message="Rate limited",
            retry_after=60,
        )
        assert error.retry_after == 60

    def test_llm_rate_limit_error_retry_after_default_none(self) -> None:
        """LLMRateLimitError retry_after defaults to None."""
        error = LLMRateLimitError(
            code="LLM_RATE_LIMIT",
            message="Rate limited",
        )
        assert error.retry_after is None

    def test_llm_rate_limit_error_to_dict_includes_retry_after(self) -> None:
        """LLMRateLimitError to_dict includes retry_after."""
        error = LLMRateLimitError(
            code="LLM_RATE_LIMIT",
            message="Rate limited",
            retry_after=60,
        )
        d = error.to_dict()
        assert d["retry_after"] == 60


class TestPhaseError:
    """Tests for PhaseError exception."""

    def test_phase_error_is_adw_error(self) -> None:
        """PhaseError inherits from ADWError."""
        error = PhaseError(
            code="PHASE_FAILED",
            message="Phase failed",
            phase="build",
        )
        assert isinstance(error, ADWError)
        assert isinstance(error, Exception)

    def test_phase_error_has_phase_field(self) -> None:
        """PhaseError includes phase field."""
        error = PhaseError(
            code="PHASE_FAILED",
            message="Phase failed",
            phase="build",
        )
        assert error.phase == "build"

    def test_phase_error_not_recoverable_by_default(self) -> None:
        """PhaseError is not recoverable by default."""
        error = PhaseError(
            code="PHASE_FAILED",
            message="Phase failed",
            phase="build",
        )
        assert error.recoverable is False

    def test_phase_error_with_suggestion(self) -> None:
        """PhaseError accepts suggestion."""
        error = PhaseError(
            code="PHASE_FAILED",
            message="Phase 'build' failed",
            phase="build",
            suggestion="Check the phase logs for details",
        )
        assert error.suggestion == "Check the phase logs for details"
        assert "Suggestion:" in str(error)

    def test_phase_error_common_codes(self) -> None:
        """PhaseError works with common error codes."""
        codes = ["PHASE_FAILED", "PHASE_TIMEOUT", "PHASE_SKIPPED", "PHASE_INVALID"]
        for code in codes:
            error = PhaseError(code=code, message=f"Error with {code}", phase="test")
            assert error.code == code

    def test_phase_error_to_dict_includes_phase(self) -> None:
        """PhaseError to_dict includes phase field."""
        error = PhaseError(
            code="PHASE_FAILED",
            message="Phase failed",
            phase="build",
        )
        d = error.to_dict()
        assert d["phase"] == "build"
        assert d["code"] == "PHASE_FAILED"
        assert d["recoverable"] is False


class TestStateError:
    """Tests for StateError exception."""

    def test_state_error_is_adw_error(self) -> None:
        """StateError inherits from ADWError."""
        error = StateError(
            code="CONTEXT_CORRUPTED",
            message="State file corrupted",
        )
        assert isinstance(error, ADWError)
        assert isinstance(error, Exception)

    def test_state_error_not_recoverable_by_default(self) -> None:
        """StateError is not recoverable by default."""
        error = StateError(
            code="CONTEXT_CORRUPTED",
            message="State file corrupted",
        )
        assert error.recoverable is False

    def test_state_error_with_suggestion(self) -> None:
        """StateError accepts suggestion."""
        error = StateError(
            code="RUN_NOT_FOUND",
            message="Run ID not found",
            suggestion="Use 'adw list' to see available runs",
        )
        assert error.suggestion == "Use 'adw list' to see available runs"
        assert "Suggestion:" in str(error)

    def test_state_error_common_codes(self) -> None:
        """StateError works with common error codes."""
        codes = ["CONTEXT_CORRUPTED", "SNAPSHOT_FAILED", "RUN_NOT_FOUND"]
        for code in codes:
            error = StateError(code=code, message=f"Error with {code}")
            assert error.code == code

    def test_state_error_to_dict(self) -> None:
        """StateError serializes properly."""
        error = StateError(
            code="CONTEXT_CORRUPTED",
            message="Context corrupted",
            suggestion="Restart the run",
        )
        d = error.to_dict()
        assert d["code"] == "CONTEXT_CORRUPTED"
        assert d["recoverable"] is False


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_is_adw_error(self) -> None:
        """ValidationError inherits from ADWError."""
        error = ValidationError(
            code="VALIDATION_FAILED",
            message="Schema validation failed",
        )
        assert isinstance(error, ADWError)
        assert isinstance(error, Exception)

    def test_validation_error_not_recoverable_by_default(self) -> None:
        """ValidationError is not recoverable by default."""
        error = ValidationError(
            code="VALIDATION_FAILED",
            message="Schema validation failed",
        )
        assert error.recoverable is False

    def test_validation_error_has_field_errors(self) -> None:
        """ValidationError includes field_errors list."""
        field_errors = [
            {"field": "name", "error": "required field missing"},
            {"field": "age", "error": "must be an integer"},
        ]
        error = ValidationError(
            code="VALIDATION_FAILED",
            message="Schema validation failed",
            field_errors=field_errors,
        )
        assert error.field_errors == field_errors
        assert len(error.field_errors) == 2

    def test_validation_error_field_errors_default_empty(self) -> None:
        """ValidationError field_errors defaults to empty list."""
        error = ValidationError(
            code="VALIDATION_FAILED",
            message="Schema validation failed",
        )
        assert error.field_errors == []

    def test_validation_error_has_schema_path(self) -> None:
        """ValidationError includes schema_path field."""
        error = ValidationError(
            code="VALIDATION_FAILED",
            message="Schema validation failed",
            schema_path="schemas/output.json",
        )
        assert error.schema_path == "schemas/output.json"

    def test_validation_error_schema_path_default_none(self) -> None:
        """ValidationError schema_path defaults to None."""
        error = ValidationError(
            code="VALIDATION_FAILED",
            message="Schema validation failed",
        )
        assert error.schema_path is None

    def test_validation_error_to_dict_includes_extra_fields(self) -> None:
        """ValidationError to_dict includes field_errors and schema_path."""
        field_errors = [{"field": "name", "error": "required"}]
        error = ValidationError(
            code="VALIDATION_FAILED",
            message="Schema validation failed",
            field_errors=field_errors,
            schema_path="schemas/output.json",
        )
        d = error.to_dict()
        assert d["field_errors"] == field_errors
        assert d["schema_path"] == "schemas/output.json"
        assert d["recoverable"] is False


class TestExceptionHierarchy:
    """Tests for the overall exception hierarchy structure."""

    def test_all_exceptions_inherit_from_adw_error(self) -> None:
        """All custom exceptions should inherit from ADWError."""
        exceptions = [
            CommandError(code="TEST", message="test"),
            ConfigError(code="TEST", message="test"),
            HookError(code="TEST", message="test", phase="test"),
            LLMError(code="TEST", message="test"),
            LLMTimeoutError(code="TEST", message="test", timeout_seconds=1, elapsed_seconds=1),
            LLMRateLimitError(code="TEST", message="test"),
            PhaseError(code="TEST", message="test", phase="test"),
            StateError(code="TEST", message="test"),
            ValidationError(code="TEST", message="test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, ADWError), f"{type(exc).__name__} should inherit from ADWError"

    def test_llm_subclasses_inherit_from_llm_error(self) -> None:
        """LLMTimeoutError and LLMRateLimitError should inherit from LLMError."""
        timeout_error = LLMTimeoutError(
            code="TEST", message="test", timeout_seconds=1, elapsed_seconds=1
        )
        rate_limit_error = LLMRateLimitError(code="TEST", message="test")

        assert isinstance(timeout_error, LLMError)
        assert isinstance(rate_limit_error, LLMError)

    def test_error_code_format_convention(self) -> None:
        """Error codes should follow CATEGORY_SPECIFIC format convention."""
        common_codes = [
            "CONFIG_NOT_FOUND",
            "INVALID_CONFIG",
            "COMMAND_NOT_FOUND",
            "COMMAND_INVALID",
            "HOOK_FAILED",
            "HOOK_TIMEOUT",
            "LLM_TIMEOUT",
            "LLM_RATE_LIMIT",
            "PHASE_FAILED",
            "PHASE_TIMEOUT",
            "CONTEXT_CORRUPTED",
            "SNAPSHOT_FAILED",
            "RUN_NOT_FOUND",
            "VALIDATION_FAILED",
        ]
        for code in common_codes:
            assert "_" in code, f"Error code {code} should contain underscore"
            assert code == code.upper(), f"Error code {code} should be uppercase"

    def test_recoverable_defaults(self) -> None:
        """Verify recoverable defaults for each exception type."""
        non_recoverable = [
            CommandError(code="TEST", message="test"),
            ConfigError(code="TEST", message="test"),
            HookError(code="TEST", message="test", phase="test"),
            LLMError(code="TEST", message="test"),
            PhaseError(code="TEST", message="test", phase="test"),
            StateError(code="TEST", message="test"),
            ValidationError(code="TEST", message="test"),
        ]
        recoverable = [
            LLMTimeoutError(code="TEST", message="test", timeout_seconds=1, elapsed_seconds=1),
            LLMRateLimitError(code="TEST", message="test"),
        ]

        for exc in non_recoverable:
            assert exc.recoverable is False, f"{type(exc).__name__} should be non-recoverable by default"

        for exc in recoverable:
            assert exc.recoverable is True, f"{type(exc).__name__} should be recoverable by default"
