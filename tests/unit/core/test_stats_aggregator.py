"""Unit tests for StatsAggregator.

Tests for cost calculation, pricing configuration, and LLM file parsing.
"""

import json
from pathlib import Path
from datetime import datetime, UTC

import pytest


class TestModelPricing:
    """Tests for model pricing configuration."""

    def test_default_pricing_exists(self) -> None:
        """Default pricing table is defined."""
        from adw.core.stats_aggregator import DEFAULT_PRICING

        assert "claude-3-5-sonnet" in DEFAULT_PRICING
        assert "claude-3-opus" in DEFAULT_PRICING
        assert "claude-3-haiku" in DEFAULT_PRICING
        assert "default" in DEFAULT_PRICING

    def test_sonnet_pricing(self) -> None:
        """Claude 3.5 Sonnet pricing is correct."""
        from adw.core.stats_aggregator import DEFAULT_PRICING

        sonnet = DEFAULT_PRICING["claude-3-5-sonnet"]
        assert sonnet["input"] == 3.00
        assert sonnet["output"] == 15.00

    def test_opus_pricing(self) -> None:
        """Claude 3 Opus pricing is correct."""
        from adw.core.stats_aggregator import DEFAULT_PRICING

        opus = DEFAULT_PRICING["claude-3-opus"]
        assert opus["input"] == 15.00
        assert opus["output"] == 75.00

    def test_haiku_pricing(self) -> None:
        """Claude 3 Haiku pricing is correct."""
        from adw.core.stats_aggregator import DEFAULT_PRICING

        haiku = DEFAULT_PRICING["claude-3-haiku"]
        assert haiku["input"] == 0.25
        assert haiku["output"] == 1.25


class TestCalculateCost:
    """Tests for cost calculation."""

    def test_default_pricing(self) -> None:
        """Uses default pricing when model not found."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.models.stats import TokenUsage

        aggregator = StatsAggregator()
        tokens = TokenUsage(input_tokens=1_000_000, output_tokens=100_000)

        cost = aggregator.calculate_cost(tokens)

        # default: $3/1M input, $15/1M output
        # 1M input = $3, 0.1M output = $1.50
        assert cost == 4.50

    def test_specific_model_pricing(self) -> None:
        """Uses model-specific pricing."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.models.stats import TokenUsage

        aggregator = StatsAggregator()
        tokens = TokenUsage(input_tokens=1_000_000, output_tokens=100_000)

        cost = aggregator.calculate_cost(tokens, model="claude-3-haiku")

        # haiku: $0.25/1M input, $1.25/1M output
        # 1M input = $0.25, 0.1M output = $0.125
        assert cost == 0.38

    def test_sonnet_pricing(self) -> None:
        """Claude 3.5 Sonnet pricing calculation."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.models.stats import TokenUsage

        aggregator = StatsAggregator()
        tokens = TokenUsage(input_tokens=2_000_000, output_tokens=500_000)

        cost = aggregator.calculate_cost(tokens, model="claude-3-5-sonnet")

        # sonnet: $3/1M input, $15/1M output
        # 2M input = $6, 0.5M output = $7.50
        assert cost == 13.50

    def test_opus_pricing(self) -> None:
        """Claude 3 Opus pricing calculation."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.models.stats import TokenUsage

        aggregator = StatsAggregator()
        tokens = TokenUsage(input_tokens=1_000_000, output_tokens=200_000)

        cost = aggregator.calculate_cost(tokens, model="claude-3-opus")

        # opus: $15/1M input, $75/1M output
        # 1M input = $15, 0.2M output = $15
        assert cost == 30.00

    def test_zero_tokens(self) -> None:
        """Zero tokens costs nothing."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.models.stats import TokenUsage

        aggregator = StatsAggregator()
        tokens = TokenUsage(input_tokens=0, output_tokens=0)

        cost = aggregator.calculate_cost(tokens)
        assert cost == 0.00

    def test_custom_pricing_override(self) -> None:
        """Can use custom pricing configuration."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.models.stats import TokenUsage

        custom_pricing = {
            "my-model": {"input": 1.00, "output": 2.00},
            "default": {"input": 1.00, "output": 2.00},
        }

        aggregator = StatsAggregator(pricing=custom_pricing)
        tokens = TokenUsage(input_tokens=1_000_000, output_tokens=500_000)

        cost = aggregator.calculate_cost(tokens, model="my-model")

        # 1M input = $1, 0.5M output = $1
        assert cost == 2.00


class TestParseLLMResponseFiles:
    """Tests for LLM response file parsing."""

    def test_parses_response_files(self, tmp_path: Path) -> None:
        """Parses token stats from response files."""
        from adw.core.stats_aggregator import StatsAggregator

        llm_dir = tmp_path / "llm"
        llm_dir.mkdir()

        # Create test response file
        response = {
            "timestamp": "2026-01-25T10:00:00Z",
            "stats": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "duration_ms": 5000,
            },
        }
        (llm_dir / "001_plan_response.json").write_text(json.dumps(response))

        aggregator = StatsAggregator()
        usage = aggregator._parse_llm_response_files(tmp_path)

        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500

    def test_sums_multiple_files(self, tmp_path: Path) -> None:
        """Sums tokens across multiple response files."""
        from adw.core.stats_aggregator import StatsAggregator

        llm_dir = tmp_path / "llm"
        llm_dir.mkdir()

        # Create multiple response files
        responses = [
            {"stats": {"input_tokens": 1000, "output_tokens": 500}},
            {"stats": {"input_tokens": 2000, "output_tokens": 800}},
            {"stats": {"input_tokens": 500, "output_tokens": 200}},
        ]

        for i, resp in enumerate(responses):
            (llm_dir / f"00{i}_phase_response.json").write_text(json.dumps(resp))

        aggregator = StatsAggregator()
        usage = aggregator._parse_llm_response_files(tmp_path)

        assert usage.input_tokens == 3500
        assert usage.output_tokens == 1500

    def test_handles_missing_llm_dir(self, tmp_path: Path) -> None:
        """Returns empty TokenUsage when llm/ doesn't exist."""
        from adw.core.stats_aggregator import StatsAggregator

        aggregator = StatsAggregator()
        usage = aggregator._parse_llm_response_files(tmp_path)

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_handles_corrupted_files(self, tmp_path: Path) -> None:
        """Skips corrupted files gracefully."""
        from adw.core.stats_aggregator import StatsAggregator

        llm_dir = tmp_path / "llm"
        llm_dir.mkdir()
        (llm_dir / "001_plan_response.json").write_text("invalid json")

        aggregator = StatsAggregator()
        usage = aggregator._parse_llm_response_files(tmp_path)

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_handles_missing_stats(self, tmp_path: Path) -> None:
        """Handles response files without stats field."""
        from adw.core.stats_aggregator import StatsAggregator

        llm_dir = tmp_path / "llm"
        llm_dir.mkdir()

        # Response without stats field
        response = {"timestamp": "2026-01-25T10:00:00Z", "content": "test"}
        (llm_dir / "001_plan_response.json").write_text(json.dumps(response))

        aggregator = StatsAggregator()
        usage = aggregator._parse_llm_response_files(tmp_path)

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_handles_zero_input_tokens(self, tmp_path: Path) -> None:
        """Handles responses with zero input tokens (streaming)."""
        from adw.core.stats_aggregator import StatsAggregator

        llm_dir = tmp_path / "llm"
        llm_dir.mkdir()

        # Response with zero input tokens (common in streaming)
        response = {
            "stats": {"input_tokens": 0, "output_tokens": 13266, "duration_ms": 156671}
        }
        (llm_dir / "001_build_response.json").write_text(json.dumps(response))

        aggregator = StatsAggregator()
        usage = aggregator._parse_llm_response_files(tmp_path)

        assert usage.input_tokens == 0
        assert usage.output_tokens == 13266
