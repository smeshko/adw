"""Tests for LLM-related Pydantic models."""

import pytest

from adw.models import LLMResult, ToolCall


class TestToolCall:
    """Tests for the ToolCall model."""

    def test_create_minimal_tool_call(self) -> None:
        """ToolCall can be created with just tool_name."""
        tc = ToolCall(tool_name="read_file")
        assert tc.tool_name == "read_file"
        assert tc.arguments == {}
        assert tc.result_summary is None

    def test_create_full_tool_call(self) -> None:
        """ToolCall can be created with all fields."""
        tc = ToolCall(
            tool_name="write_file",
            arguments={"path": "/tmp/test.txt", "content": "hello"},
            result_summary="File written successfully",
        )
        assert tc.tool_name == "write_file"
        assert tc.arguments == {"path": "/tmp/test.txt", "content": "hello"}
        assert tc.result_summary == "File written successfully"

    def test_tool_call_serialization(self) -> None:
        """ToolCall serializes to dict correctly."""
        tc = ToolCall(
            tool_name="run_command",
            arguments={"command": "ls -la"},
        )
        d = tc.model_dump()
        assert d["tool_name"] == "run_command"
        assert d["arguments"] == {"command": "ls -la"}
        assert d["result_summary"] is None


class TestLLMResult:
    """Tests for the LLMResult model."""

    def test_create_success_result(self) -> None:
        """LLMResult can be created for successful execution."""
        result = LLMResult(
            success=True,
            content="Generated code here...",
        )
        assert result.success is True
        assert result.content == "Generated code here..."
        assert result.tool_calls == []
        assert result.tokens_used == 0
        assert result.duration_ms == 0
        assert result.error is None

    def test_create_failure_result(self) -> None:
        """LLMResult can be created for failed execution."""
        result = LLMResult(
            success=False,
            content="",
            error="Connection timeout",
        )
        assert result.success is False
        assert result.content == ""
        assert result.error == "Connection timeout"

    def test_create_result_with_tool_calls(self) -> None:
        """LLMResult can include tool calls."""
        tool_calls = [
            ToolCall(tool_name="read_file", arguments={"path": "/src/main.py"}),
            ToolCall(tool_name="write_file", arguments={"path": "/src/new.py"}),
        ]
        result = LLMResult(
            success=True,
            content="Modified the code",
            tool_calls=tool_calls,
        )
        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].tool_name == "read_file"
        assert result.tool_calls[1].tool_name == "write_file"

    def test_create_result_with_metrics(self) -> None:
        """LLMResult can include execution metrics."""
        result = LLMResult(
            success=True,
            content="Response",
            tokens_used=500,
            duration_ms=2500,
        )
        assert result.tokens_used == 500
        assert result.duration_ms == 2500

    def test_result_serialization(self) -> None:
        """LLMResult serializes to dict correctly."""
        result = LLMResult(
            success=True,
            content="Test content",
            tool_calls=[ToolCall(tool_name="test_tool")],
            tokens_used=100,
            duration_ms=500,
        )
        d = result.model_dump()
        assert d["success"] is True
        assert d["content"] == "Test content"
        assert len(d["tool_calls"]) == 1
        assert d["tool_calls"][0]["tool_name"] == "test_tool"
        assert d["tokens_used"] == 100
        assert d["duration_ms"] == 500

    def test_result_json_serialization(self) -> None:
        """LLMResult can be serialized to JSON."""
        result = LLMResult(
            success=True,
            content="JSON test",
            tokens_used=50,
        )
        json_str = result.model_dump_json()
        assert '"success": true' in json_str or '"success":true' in json_str
        assert "JSON test" in json_str

    def test_result_required_fields(self) -> None:
        """LLMResult requires success and content fields."""
        with pytest.raises(Exception):  # Pydantic validation error
            LLMResult()  # type: ignore[call-arg]

    def test_acceptance_criteria_fields(self) -> None:
        """LLMResult includes fields from acceptance criteria.

        Fields: success (bool), content (str), tool_calls (list),
        tokens_used (int), duration_ms (int), error (LLMError | None)
        """
        result = LLMResult(
            success=True,
            content="test",
            tool_calls=[],
            tokens_used=0,
            duration_ms=0,
            error=None,
        )
        # Verify all AC fields exist with correct types
        assert isinstance(result.success, bool)
        assert isinstance(result.content, str)
        assert isinstance(result.tool_calls, list)
        assert isinstance(result.tokens_used, int)
        assert isinstance(result.duration_ms, int)
        assert result.error is None or isinstance(result.error, str)
