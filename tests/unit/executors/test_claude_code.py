"""Tests for ClaudeCodeExecutor token and tool call parsing.

This module tests the token extraction and tool call parsing from
Claude Code CLI output in various formats.
"""

import json

import pytest

from adw.executors.claude_code import ClaudeCodeExecutor
from adw.models.config import LLMConfig
from adw.models.llm import ToolCall


@pytest.fixture
def executor() -> ClaudeCodeExecutor:
    """Create a ClaudeCodeExecutor with default config."""
    config = LLMConfig(path="claude", timeout_seconds=300)
    return ClaudeCodeExecutor(config)


class TestTokenExtraction:
    """Tests for extracting token usage from Claude Code output."""

    def test_extracts_tokens_from_result_message(self, executor: ClaudeCodeExecutor) -> None:
        """Tokens are extracted from result message with usage field."""
        output = json.dumps({
            "type": "result",
            "text": "Hello, World!",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        })

        parsed = executor._parse_output(output)

        assert parsed["tokens_used"] == 150  # 100 + 50

    def test_extracts_tokens_from_message_delta(self, executor: ClaudeCodeExecutor) -> None:
        """Tokens are extracted from message_delta with usage field."""
        output = json.dumps({
            "type": "message_delta",
            "usage": {
                "input_tokens": 200,
                "output_tokens": 300,
            },
        })

        parsed = executor._parse_output(output)

        assert parsed["tokens_used"] == 500  # 200 + 300

    def test_defaults_to_zero_when_no_usage(self, executor: ClaudeCodeExecutor) -> None:
        """Tokens default to 0 when no usage field present."""
        output = json.dumps({
            "type": "result",
            "text": "Response without usage",
        })

        parsed = executor._parse_output(output)

        assert parsed["tokens_used"] == 0

    def test_defaults_to_zero_for_plain_text(self, executor: ClaudeCodeExecutor) -> None:
        """Tokens default to 0 for non-JSON plain text output."""
        output = "This is plain text output without JSON"

        parsed = executor._parse_output(output)

        assert parsed["tokens_used"] == 0

    def test_handles_empty_output(self, executor: ClaudeCodeExecutor) -> None:
        """Tokens default to 0 for empty output."""
        output = ""

        parsed = executor._parse_output(output)

        assert parsed["tokens_used"] == 0

    def test_handles_partial_usage_only_input(self, executor: ClaudeCodeExecutor) -> None:
        """Handles usage with only input_tokens."""
        output = json.dumps({
            "type": "result",
            "usage": {
                "input_tokens": 100,
            },
        })

        parsed = executor._parse_output(output)

        assert parsed["tokens_used"] == 100

    def test_handles_partial_usage_only_output(self, executor: ClaudeCodeExecutor) -> None:
        """Handles usage with only output_tokens."""
        output = json.dumps({
            "type": "result",
            "usage": {
                "output_tokens": 200,
            },
        })

        parsed = executor._parse_output(output)

        assert parsed["tokens_used"] == 200

    def test_multiline_jsonl_takes_last_usage(self, executor: ClaudeCodeExecutor) -> None:
        """With multiple messages, the last usage value is used."""
        lines = [
            json.dumps({
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "First"}]},
            }),
            json.dumps({
                "type": "message_delta",
                "usage": {"input_tokens": 50, "output_tokens": 50},
            }),
            json.dumps({
                "type": "result",
                "text": "Final",
                "usage": {"input_tokens": 100, "output_tokens": 200},
            }),
        ]
        output = "\n".join(lines)

        parsed = executor._parse_output(output)

        # Last result message has usage 100 + 200 = 300
        assert parsed["tokens_used"] == 300


class TestToolCallExtraction:
    """Tests for extracting tool calls from Claude Code output."""

    def test_extracts_tool_calls_from_assistant_message(self, executor: ClaudeCodeExecutor) -> None:
        """Tool calls are extracted from assistant message content blocks."""
        output = json.dumps({
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "read_file",
                        "input": {"path": "/src/main.py"},
                    },
                ],
            },
        })

        parsed = executor._parse_output(output)

        assert len(parsed["tool_calls"]) == 1
        assert parsed["tool_calls"][0].tool_name == "read_file"
        assert parsed["tool_calls"][0].arguments == {"path": "/src/main.py"}

    def test_extracts_multiple_tool_calls(self, executor: ClaudeCodeExecutor) -> None:
        """Multiple tool calls in one message are all extracted."""
        output = json.dumps({
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "read_file",
                        "input": {"path": "/src/main.py"},
                    },
                    {
                        "type": "tool_use",
                        "name": "write_file",
                        "input": {"path": "/src/new.py", "content": "code"},
                    },
                ],
            },
        })

        parsed = executor._parse_output(output)

        assert len(parsed["tool_calls"]) == 2
        assert parsed["tool_calls"][0].tool_name == "read_file"
        assert parsed["tool_calls"][1].tool_name == "write_file"

    def test_tool_call_result_summary_is_none(self, executor: ClaudeCodeExecutor) -> None:
        """Tool calls from output don't have result summary initially."""
        output = json.dumps({
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "bash",
                        "input": {"command": "ls -la"},
                    },
                ],
            },
        })

        parsed = executor._parse_output(output)

        assert parsed["tool_calls"][0].result_summary is None

    def test_handles_empty_tool_arguments(self, executor: ClaudeCodeExecutor) -> None:
        """Tool calls with no arguments have empty dict."""
        output = json.dumps({
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "get_cwd",
                    },
                ],
            },
        })

        parsed = executor._parse_output(output)

        assert parsed["tool_calls"][0].arguments == {}

    def test_no_tool_calls_returns_empty_list(self, executor: ClaudeCodeExecutor) -> None:
        """No tool_use blocks returns empty tool_calls list."""
        output = json.dumps({
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Just a text response"},
                ],
            },
        })

        parsed = executor._parse_output(output)

        assert parsed["tool_calls"] == []

    def test_extracts_tool_calls_across_multiple_messages(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Tool calls from multiple assistant messages are accumulated."""
        lines = [
            json.dumps({
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "read_file", "input": {"path": "a.py"}},
                    ],
                },
            }),
            json.dumps({
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "write_file", "input": {"path": "b.py"}},
                    ],
                },
            }),
        ]
        output = "\n".join(lines)

        parsed = executor._parse_output(output)

        assert len(parsed["tool_calls"]) == 2

    def test_handles_unknown_tool_name(self, executor: ClaudeCodeExecutor) -> None:
        """Tool calls with missing name default to 'unknown'."""
        output = json.dumps({
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "input": {"arg": "value"},
                    },
                ],
            },
        })

        parsed = executor._parse_output(output)

        assert parsed["tool_calls"][0].tool_name == "unknown"


class TestContentExtraction:
    """Tests for extracting text content from Claude Code output."""

    def test_extracts_text_from_assistant_message(self, executor: ClaudeCodeExecutor) -> None:
        """Text content is extracted from assistant message blocks."""
        output = json.dumps({
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Hello, World!"},
                ],
            },
        })

        parsed = executor._parse_output(output)

        assert parsed["content"] == "Hello, World!"

    def test_extracts_text_from_result_message(self, executor: ClaudeCodeExecutor) -> None:
        """Text content is extracted from result message."""
        output = json.dumps({
            "type": "result",
            "text": "Final result text",
        })

        parsed = executor._parse_output(output)

        assert parsed["content"] == "Final result text"

    def test_extracts_text_from_content_block_delta(self, executor: ClaudeCodeExecutor) -> None:
        """Text content is extracted from streaming deltas."""
        output = json.dumps({
            "type": "content_block_delta",
            "delta": {
                "type": "text_delta",
                "text": "Streaming text",
            },
        })

        parsed = executor._parse_output(output)

        assert parsed["content"] == "Streaming text"

    def test_combines_multiple_text_blocks(self, executor: ClaudeCodeExecutor) -> None:
        """Multiple text blocks are combined."""
        lines = [
            json.dumps({
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Part 1"},
                        {"type": "text", "text": " Part 2"},
                    ],
                },
            }),
        ]
        output = "\n".join(lines)

        parsed = executor._parse_output(output)

        assert parsed["content"] == "Part 1 Part 2"

    def test_treats_plain_text_as_content(self, executor: ClaudeCodeExecutor) -> None:
        """Non-JSON text is treated as content."""
        output = "This is plain text"

        parsed = executor._parse_output(output)

        assert parsed["content"] == "This is plain text"

    def test_handles_mixed_json_and_plain_text(self, executor: ClaudeCodeExecutor) -> None:
        """Mix of JSON and plain text lines."""
        lines = [
            "Plain text line",
            json.dumps({"type": "result", "text": "JSON text"}),
        ]
        output = "\n".join(lines)

        parsed = executor._parse_output(output)

        # Both should be in content
        assert "Plain text line" in parsed["content"]
        assert "JSON text" in parsed["content"]


class TestMalformedOutput:
    """Tests for handling malformed or unexpected output."""

    def test_handles_invalid_json(self, executor: ClaudeCodeExecutor) -> None:
        """Invalid JSON is treated as plain text."""
        output = "{not valid json}"

        parsed = executor._parse_output(output)

        assert parsed["content"] == "{not valid json}"
        assert parsed["tokens_used"] == 0
        assert parsed["tool_calls"] == []

    def test_handles_non_dict_json(self, executor: ClaudeCodeExecutor) -> None:
        """Non-dict JSON values (numbers, arrays) are converted to content."""
        output = json.dumps([1, 2, 3])

        parsed = executor._parse_output(output)

        assert parsed["content"] == "[1, 2, 3]"

    def test_handles_json_number(self, executor: ClaudeCodeExecutor) -> None:
        """JSON number is converted to content."""
        output = json.dumps(42)

        parsed = executor._parse_output(output)

        assert parsed["content"] == "42"

    def test_handles_missing_message_field(self, executor: ClaudeCodeExecutor) -> None:
        """Assistant message without 'message' field is handled gracefully."""
        output = json.dumps({
            "type": "assistant",
            # Missing "message" field
        })

        parsed = executor._parse_output(output)

        # Should not crash, return empty content
        assert parsed["tokens_used"] == 0

    def test_handles_empty_content_array(self, executor: ClaudeCodeExecutor) -> None:
        """Empty content array in assistant message."""
        output = json.dumps({
            "type": "assistant",
            "message": {
                "content": [],
            },
        })

        parsed = executor._parse_output(output)

        assert parsed["content"] == ""
        assert parsed["tool_calls"] == []

    def test_handles_unknown_message_type(self, executor: ClaudeCodeExecutor) -> None:
        """Unknown message type is ignored without error."""
        output = json.dumps({
            "type": "unknown_type",
            "data": "some data",
        })

        parsed = executor._parse_output(output)

        # Should not crash, return empty
        assert parsed["tokens_used"] == 0


class TestToolCallModel:
    """Tests for ToolCall model integrity."""

    def test_tool_call_is_pydantic_model(self) -> None:
        """ToolCall is a proper Pydantic model."""
        tc = ToolCall(
            tool_name="test_tool",
            arguments={"key": "value"},
            result_summary="Done",
        )

        assert tc.tool_name == "test_tool"
        assert tc.arguments == {"key": "value"}
        assert tc.result_summary == "Done"

    def test_tool_call_defaults(self) -> None:
        """ToolCall has correct default values."""
        tc = ToolCall(tool_name="test")

        assert tc.arguments == {}
        assert tc.result_summary is None

    def test_tool_call_serialization(self) -> None:
        """ToolCall serializes to JSON correctly."""
        tc = ToolCall(
            tool_name="read_file",
            arguments={"path": "/test.py"},
            result_summary="File read",
        )

        data = tc.model_dump()

        assert data["tool_name"] == "read_file"
        assert data["arguments"] == {"path": "/test.py"}
        assert data["result_summary"] == "File read"
