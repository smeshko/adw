# Test Reduction Summary:
# Removed 9 trivial tests that only verified Pydantic's built-in behavior:
# - test_create_minimal_tool_call, test_create_full_tool_call, test_tool_call_serialization
# - test_create_success_result, test_create_failure_result, test_create_result_with_tool_calls
# - test_create_result_with_metrics, test_result_serialization, test_result_json_serialization
# Kept 2 tests that verify validation and acceptance criteria compliance.
"""Tests for LLM-related Pydantic models."""

import pytest
from pydantic import ValidationError

from adw.models import LLMResult


class TestLLMResult:
    """Tests for the LLMResult model."""

    def test_result_required_fields(self) -> None:
        """LLMResult requires content and nothing else."""
        required = {
            name
            for name, field in LLMResult.model_fields.items()
            if field.is_required()
        }
        assert required == {"content"}
        with pytest.raises(ValidationError):
            LLMResult()  # type: ignore[call-arg]

    def test_unknown_field_rejected(self) -> None:
        """Unknown fields fail loudly instead of being silently dropped."""
        with pytest.raises(ValidationError):
            LLMResult(content="x", success=True)  # type: ignore[call-arg]

    def test_acceptance_criteria_fields(self) -> None:
        """LLMResult includes fields from acceptance criteria.

        Fields: content (str), tool_calls (list), tokens_used (int),
        duration_ms (int)
        """
        result = LLMResult(
            content="test",
            tool_calls=[],
            tokens_used=0,
            duration_ms=0,
        )
        # Verify all AC fields exist with correct types
        assert isinstance(result.content, str)
        assert isinstance(result.tool_calls, list)
        assert isinstance(result.tokens_used, int)
        assert isinstance(result.duration_ms, int)

    def test_final_output_field_exists(self) -> None:
        """LLMResult has final_output field for last message only (ISS-023)."""
        result = LLMResult(
            content="Full conversation",
            final_output="Last message only",
        )
        assert result.final_output == "Last message only"
        assert result.content == "Full conversation"

    def test_final_output_defaults_to_empty(self) -> None:
        """final_output defaults to empty string if not provided."""
        result = LLMResult(
            content="Full conversation",
        )
        assert result.final_output == ""
