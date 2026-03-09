"""Integration tests for token tracking.

These tests verify the complete token tracking flow with realistic
Claude Code output fixtures.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from adw.executors.claude_code import ClaudeCodeExecutor
from adw.models.config import LLMConfig
from adw.models.context import RunContext
from adw.models.phase import PhaseResult, PhaseStatus


class TestTokenTrackingIntegration:
    """Integration tests for token tracking with realistic fixtures."""

    @pytest.fixture
    def executor(self) -> ClaudeCodeExecutor:
        """Create a ClaudeCodeExecutor for testing."""
        config = LLMConfig(path="claude")
        return ClaudeCodeExecutor(config)

    @pytest.fixture
    def fixtures_path(self) -> Path:
        """Get the path to Claude output fixtures."""
        return Path(__file__).parent.parent / "fixtures" / "claude_output"

    def test_parse_simple_response_fixture(
        self, executor: ClaudeCodeExecutor, fixtures_path: Path
    ) -> None:
        """Test parsing a simple response from Claude Code."""
        fixture_file = fixtures_path / "simple_response.jsonl"
        output = fixture_file.read_text()

        parsed = executor._parse_output(output)

        # Verify token extraction
        assert parsed["tokens_used"] == 200  # 150 + 50
        assert parsed["tokens_used"] > 0
        assert parsed["tokens_used"] < 10000  # Reasonable upper bound

        # Verify content extraction
        assert "Hello" in parsed["content"]
        assert "help you" in parsed["content"]

        # No tool calls in simple response
        assert parsed["tool_calls"] == []

    def test_parse_response_with_tool_calls_fixture(
        self, executor: ClaudeCodeExecutor, fixtures_path: Path
    ) -> None:
        """Test parsing a response with multiple tool calls."""
        fixture_file = fixtures_path / "with_tool_calls.jsonl"
        output = fixture_file.read_text()

        parsed = executor._parse_output(output)

        # Verify token extraction
        assert parsed["tokens_used"] == 850  # 500 + 350
        assert parsed["tokens_used"] > 0

        # Verify tool calls captured
        assert len(parsed["tool_calls"]) == 2

        # First tool call: read_file
        assert parsed["tool_calls"][0].tool_name == "read_file"
        assert parsed["tool_calls"][0].arguments == {"path": "/src/main.py"}

        # Second tool call: write_file
        assert parsed["tool_calls"][1].tool_name == "write_file"
        assert "improved.py" in parsed["tool_calls"][1].arguments.get("path", "")

        # Verify content extraction
        assert "read the file" in parsed["content"]
        assert "analyze" in parsed["content"]

    def test_token_counts_are_reasonable(
        self, executor: ClaudeCodeExecutor, fixtures_path: Path
    ) -> None:
        """Verify token counts are within reasonable bounds."""
        # Test all fixture files
        for fixture_file in fixtures_path.glob("*.jsonl"):
            output = fixture_file.read_text()
            parsed = executor._parse_output(output)

            # Tokens should be non-negative
            assert parsed["tokens_used"] >= 0, f"Negative tokens in {fixture_file.name}"

            # Tokens should be within reasonable range (< 100k for typical requests)
            assert parsed["tokens_used"] < 100000, (
                f"Unreasonable token count in {fixture_file.name}"
            )

    def test_phase_result_with_real_data(
        self, executor: ClaudeCodeExecutor, fixtures_path: Path
    ) -> None:
        """Test creating PhaseResult with parsed data from fixture."""
        fixture_file = fixtures_path / "with_tool_calls.jsonl"
        output = fixture_file.read_text()
        parsed = executor._parse_output(output)

        start = datetime.now()
        end = start + timedelta(seconds=5)

        # Create PhaseResult with parsed data
        result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=start,
            completed_at=end,
            tokens_used=parsed["tokens_used"],
            tool_calls=parsed["tool_calls"],
        )

        assert result.tokens_used == 850
        assert len(result.tool_calls) == 2
        assert result.duration_ms == 5000

    def test_run_context_token_aggregation_scenario(self) -> None:
        """Test realistic token aggregation across multiple phases."""
        # Simulate tokens from multiple phases
        phase_tokens = {
            "plan": 500,
            "code": 1200,
            "test": 800,
            "validate": 300,
        }

        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add user authentication",
            current_phase="validate",
            phase_history=["plan", "code", "test", "verify"],
            started_at=datetime.now(),
            phase_tokens=phase_tokens,
        )

        # Verify aggregation
        assert context.total_tokens == 2800

        # Verify individual phase access
        assert context.phase_tokens["plan"] == 500
        assert context.phase_tokens["code"] == 1200

        # Verify immutable update preserves aggregation
        updated = context.model_copy(
            update={"phase_tokens": {**phase_tokens, "review": 200}}
        )
        assert updated.total_tokens == 3000

    def test_multiple_phase_results_accumulation(
        self, executor: ClaudeCodeExecutor, fixtures_path: Path
    ) -> None:
        """Test accumulating tokens across multiple PhaseResults."""
        simple_output = (fixtures_path / "simple_response.jsonl").read_text()
        complex_output = (fixtures_path / "with_tool_calls.jsonl").read_text()

        # Parse both outputs
        simple_parsed = executor._parse_output(simple_output)
        complex_parsed = executor._parse_output(complex_output)

        # Create phase results
        now = datetime.now()
        plan_result = PhaseResult(
            phase="plan",
            status=PhaseStatus.COMPLETED,
            started_at=now,
            completed_at=now + timedelta(seconds=30),
            tokens_used=simple_parsed["tokens_used"],
            tool_calls=simple_parsed["tool_calls"],
        )

        code_result = PhaseResult(
            phase="code",
            status=PhaseStatus.COMPLETED,
            started_at=now + timedelta(seconds=31),
            completed_at=now + timedelta(seconds=90),
            tokens_used=complex_parsed["tokens_used"],
            tool_calls=complex_parsed["tool_calls"],
        )

        # Verify individual results
        assert plan_result.tokens_used == 200
        assert code_result.tokens_used == 850

        # Verify tool calls
        assert len(plan_result.tool_calls) == 0
        assert len(code_result.tool_calls) == 2

        # Create context with accumulated tokens
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test feature",
            current_phase="code",
            started_at=now,
            phase_tokens={
                "plan": plan_result.tokens_used,
                "code": code_result.tokens_used,
            },
        )

        # Verify total tokens
        assert context.total_tokens == 1050  # 200 + 850
