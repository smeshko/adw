"""Unit tests for StatsAggregator.

Tests for cost calculation, pricing configuration, and LLM file parsing.
"""

import json
import os
from pathlib import Path
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock, patch

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


class TestGetDailyTokenCounts:
    """Tests for get_daily_token_counts method."""

    def test_returns_seven_days(self) -> None:
        """Returns 7 entries by default (one per day)."""
        from adw.core.stats_aggregator import StatsAggregator

        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []
        mock_im.get_recent_runs.return_value = []

        aggregator = StatsAggregator(index_manager=mock_im, project_registry=mock_pr)
        result = aggregator.get_daily_token_counts()

        assert len(result) == 7
        assert all("date" in d for d in result)
        assert all("tokens" in d for d in result)

    def test_all_zeros_when_no_runs(self) -> None:
        """Returns all-zero token counts when no runs exist."""
        from adw.core.stats_aggregator import StatsAggregator

        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []
        mock_im.get_recent_runs.return_value = []

        aggregator = StatsAggregator(index_manager=mock_im, project_registry=mock_pr)
        result = aggregator.get_daily_token_counts()

        assert all(d["tokens"] == 0 for d in result)

    def test_sums_tokens_per_day(self) -> None:
        """Tokens are summed correctly per day with multiple runs."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.models.stats import TokenUsage

        now = datetime.now(UTC)
        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []

        entries = []
        for i in range(3):
            e = MagicMock()
            e.run_id = f"01ABCDEFGHIJKLMNOPQRSTUV{i:01d}"
            e.started_at = now - timedelta(days=1)
            e.project_path = "/projects/test"
            entries.append(e)

        mock_im.get_recent_runs.return_value = entries

        aggregator = StatsAggregator(index_manager=mock_im, project_registry=mock_pr)
        aggregator._parse_llm_response_files = lambda _: TokenUsage(
            input_tokens=500, output_tokens=500,
        )
        result = aggregator.get_daily_token_counts()

        total = sum(d["tokens"] for d in result)
        assert total == 3000  # 3 runs * 1000 tokens each

        # Verify tokens are assigned to the correct day (yesterday)
        yesterday = (now - timedelta(days=1)).date()
        day_map = {d["date"]: d["tokens"] for d in result}
        assert day_map[yesterday] == 3000
        # All other days should be zero
        for d in result:
            if d["date"] != yesterday:
                assert d["tokens"] == 0, f"Expected 0 tokens on {d['date']}, got {d['tokens']}"

    def test_respects_project_filter(self) -> None:
        """Project name filter is passed to get_recent_runs."""
        from adw.core.stats_aggregator import StatsAggregator

        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []
        mock_im.get_recent_runs.return_value = []

        aggregator = StatsAggregator(index_manager=mock_im, project_registry=mock_pr)
        aggregator.get_daily_token_counts(project_name="my-project")

        mock_im.get_recent_runs.assert_called_once()
        call_kwargs = mock_im.get_recent_runs.call_args
        assert call_kwargs.kwargs.get("project_name") == "my-project"

    def test_filters_to_registered_projects(self) -> None:
        """Only includes runs from registered project paths."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.models.stats import TokenUsage

        now = datetime.now(UTC)
        mock_im = MagicMock()
        mock_pr = MagicMock()

        # Register one project
        proj = MagicMock()
        proj.path = "/projects/registered"
        mock_pr.get_all.return_value = [proj]

        # Two entries: one registered, one not
        e1 = MagicMock()
        e1.run_id = "01ABCDEFGHIJKLMNOPQRSTUV0"
        e1.started_at = now - timedelta(days=1)
        e1.project_path = "/projects/registered"

        e2 = MagicMock()
        e2.run_id = "01ABCDEFGHIJKLMNOPQRSTUV1"
        e2.started_at = now - timedelta(days=1)
        e2.project_path = "/projects/unregistered"

        mock_im.get_recent_runs.return_value = [e1, e2]

        aggregator = StatsAggregator(index_manager=mock_im, project_registry=mock_pr)
        aggregator._parse_llm_response_files = lambda _: TokenUsage(
            input_tokens=500, output_tokens=500,
        )
        result = aggregator.get_daily_token_counts()

        total = sum(d["tokens"] for d in result)
        assert total == 1000  # Only the registered project's run

    def test_custom_days_parameter(self) -> None:
        """Respects custom days parameter."""
        from adw.core.stats_aggregator import StatsAggregator

        mock_im = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_all.return_value = []
        mock_im.get_recent_runs.return_value = []

        aggregator = StatsAggregator(index_manager=mock_im, project_registry=mock_pr)
        result = aggregator.get_daily_token_counts(days=3)

        assert len(result) == 3


class TestStatsAggregatorInit:
    """Tests for StatsAggregator initialization."""

    def test_default_cache_path(self) -> None:
        """Default cache path is ~/.adw/stats-cache.json."""
        from adw.core.stats_aggregator import StatsAggregator

        # Clear env var if set
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ADW_TEST_STATS_CACHE_PATH", None)
            aggregator = StatsAggregator()

        assert aggregator.cache_path == Path.home() / ".adw" / "stats-cache.json"

    def test_custom_cache_path(self, tmp_path: Path) -> None:
        """Custom cache path can be specified."""
        from adw.core.stats_aggregator import StatsAggregator

        custom_path = tmp_path / "custom-cache.json"
        aggregator = StatsAggregator(cache_path=custom_path)

        assert aggregator.cache_path == custom_path

    def test_env_var_cache_path(self, tmp_path: Path) -> None:
        """ADW_TEST_STATS_CACHE_PATH env var overrides default."""
        from adw.core.stats_aggregator import StatsAggregator

        env_path = str(tmp_path / "env-cache.json")
        with patch.dict(os.environ, {"ADW_TEST_STATS_CACHE_PATH": env_path}):
            aggregator = StatsAggregator()

        assert aggregator.cache_path == Path(env_path)

    def test_explicit_path_overrides_env(self, tmp_path: Path) -> None:
        """Explicit cache_path parameter overrides env var."""
        from adw.core.stats_aggregator import StatsAggregator

        env_path = str(tmp_path / "env-cache.json")
        custom_path = tmp_path / "custom-cache.json"

        with patch.dict(os.environ, {"ADW_TEST_STATS_CACHE_PATH": env_path}):
            aggregator = StatsAggregator(cache_path=custom_path)

        assert aggregator.cache_path == custom_path

    def test_custom_pricing(self) -> None:
        """Custom pricing configuration can be specified."""
        from adw.core.stats_aggregator import StatsAggregator, DEFAULT_PRICING

        custom_pricing = {
            "my-model": {"input": 1.00, "output": 2.00},
            "default": {"input": 1.00, "output": 2.00},
        }

        aggregator = StatsAggregator(pricing=custom_pricing)

        assert aggregator.pricing == custom_pricing
        assert aggregator.pricing != DEFAULT_PRICING

    def test_custom_index_manager(self) -> None:
        """Custom IndexManager can be specified."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.core.index_manager import IndexManager

        custom_manager = IndexManager()
        aggregator = StatsAggregator(index_manager=custom_manager)

        assert aggregator.index_manager is custom_manager


class TestGetGlobalStats:
    """Tests for get_global_stats method."""

    def test_returns_global_statistics(self, tmp_path: Path) -> None:
        """get_global_stats returns GlobalStatistics object."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.core.index_manager import IndexManager
        from adw.models.stats import GlobalStatistics

        # Create mock index manager
        index_manager = IndexManager(index_path=tmp_path / "index.jsonl")

        aggregator = StatsAggregator(
            index_manager=index_manager,
            cache_path=tmp_path / "cache.json",
        )

        stats = aggregator.get_global_stats()

        assert isinstance(stats, GlobalStatistics)
        assert stats.generated_at is not None

    def test_empty_index_returns_empty_stats(self, tmp_path: Path) -> None:
        """Empty index returns stats with zero values."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.core.index_manager import IndexManager

        index_manager = IndexManager(index_path=tmp_path / "index.jsonl")

        aggregator = StatsAggregator(
            index_manager=index_manager,
            cache_path=tmp_path / "cache.json",
        )

        stats = aggregator.get_global_stats()

        assert stats.total_runs == 0
        assert stats.runs_this_week == 0
        assert stats.runs_today == 0
        assert stats.success_rate == 0.0
        assert stats.projects == []

    def test_force_refresh_ignores_cache(self, tmp_path: Path) -> None:
        """force_refresh=True skips cache check."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.core.index_manager import IndexManager

        index_manager = IndexManager(index_path=tmp_path / "index.jsonl")
        cache_path = tmp_path / "cache.json"

        # Create a cache file
        cache_data = {
            "generated_at": datetime.now(UTC).isoformat(),
            "ttl_seconds": 300,
            "stats": {
                "generated_at": datetime.now(UTC).isoformat(),
                "total_runs": 999,  # Different from fresh stats
            },
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        aggregator = StatsAggregator(
            index_manager=index_manager,
            cache_path=cache_path,
        )

        # With force_refresh, should get 0 runs (fresh stats from empty index)
        stats = aggregator.get_global_stats(force_refresh=True)

        assert stats.total_runs == 0  # Fresh, not cached 999


class TestGetTokenUsage:
    """Tests for get_token_usage helper method."""

    def test_get_token_usage_for_run(self, tmp_path: Path) -> None:
        """get_token_usage returns token usage for a specific run."""
        from adw.core.stats_aggregator import StatsAggregator

        # Set up run directory structure
        run_id = "01ABC123"
        project_path = tmp_path / "my-project"
        run_dir = project_path / ".adw" / "runs" / run_id / "llm"
        run_dir.mkdir(parents=True)

        # Create response file
        response = {"stats": {"input_tokens": 5000, "output_tokens": 2500}}
        (run_dir / "001_plan_response.json").write_text(json.dumps(response))

        aggregator = StatsAggregator()
        usage = aggregator.get_token_usage(run_id, project_path)

        assert usage is not None
        assert usage.input_tokens == 5000
        assert usage.output_tokens == 2500

    def test_get_token_usage_missing_run(self, tmp_path: Path) -> None:
        """get_token_usage returns None for non-existent run."""
        from adw.core.stats_aggregator import StatsAggregator

        project_path = tmp_path / "my-project"
        project_path.mkdir()

        aggregator = StatsAggregator()
        usage = aggregator.get_token_usage("nonexistent-run", project_path)

        assert usage is None


class TestStatisticsCache:
    """Tests for statistics caching behavior."""

    def test_cache_is_created(self, tmp_path: Path) -> None:
        """Cache file is created after get_global_stats."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.core.index_manager import IndexManager

        cache_path = tmp_path / "cache.json"
        index_manager = IndexManager(index_path=tmp_path / "index.jsonl")

        aggregator = StatsAggregator(
            index_manager=index_manager,
            cache_path=cache_path,
        )

        aggregator.get_global_stats()

        assert cache_path.exists()

    def test_cache_structure(self, tmp_path: Path) -> None:
        """Cache has correct structure."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.core.index_manager import IndexManager

        cache_path = tmp_path / "cache.json"
        index_manager = IndexManager(index_path=tmp_path / "index.jsonl")

        aggregator = StatsAggregator(
            index_manager=index_manager,
            cache_path=cache_path,
        )

        aggregator.get_global_stats()

        with open(cache_path) as f:
            cache_data = json.load(f)

        assert "generated_at" in cache_data
        assert "ttl_seconds" in cache_data
        assert cache_data["ttl_seconds"] == 300
        assert "stats" in cache_data
        assert "index_mtime" in cache_data

    def test_cache_is_used_when_valid(self, tmp_path: Path) -> None:
        """Valid cache is used instead of recalculating."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.core.index_manager import IndexManager
        from adw.models.stats import GlobalStatistics

        cache_path = tmp_path / "cache.json"
        index_path = tmp_path / "index.jsonl"
        index_manager = IndexManager(index_path=index_path)

        # Create a cache with distinctive data
        now = datetime.now(UTC)
        cached_stats = GlobalStatistics(
            generated_at=now,
            total_runs=12345,  # Distinctive value
        )

        cache_data = {
            "generated_at": now.isoformat(),
            "ttl_seconds": 300,
            "index_mtime": None,  # No index file
            "project_name": None,
            "since": None,
            "stats": cached_stats.model_dump(mode="json"),
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        aggregator = StatsAggregator(
            index_manager=index_manager,
            cache_path=cache_path,
        )

        stats = aggregator.get_global_stats()

        assert stats.total_runs == 12345  # From cache, not fresh calculation

    def test_cache_invalidated_on_ttl_expiry(self, tmp_path: Path) -> None:
        """Cache is invalidated when TTL expires."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.core.index_manager import IndexManager

        cache_path = tmp_path / "cache.json"
        index_manager = IndexManager(index_path=tmp_path / "index.jsonl")

        # Create an expired cache
        expired_time = datetime.now(UTC) - timedelta(seconds=600)  # 10 minutes ago
        cache_data = {
            "generated_at": expired_time.isoformat(),
            "ttl_seconds": 300,  # 5 minutes TTL
            "index_mtime": None,
            "project_name": None,
            "since": None,
            "stats": {
                "generated_at": expired_time.isoformat(),
                "total_runs": 99999,
            },
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        aggregator = StatsAggregator(
            index_manager=index_manager,
            cache_path=cache_path,
        )

        stats = aggregator.get_global_stats()

        # Should get fresh stats (0 runs from empty index), not cached 99999
        assert stats.total_runs == 0

    def test_cache_invalidated_on_index_change(self, tmp_path: Path) -> None:
        """Cache is invalidated when index file is modified."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.core.index_manager import IndexManager

        cache_path = tmp_path / "cache.json"
        index_path = tmp_path / "index.jsonl"

        # Create the index file first
        index_path.write_text("")
        original_mtime = datetime.fromtimestamp(
            index_path.stat().st_mtime, tz=UTC
        ).isoformat()

        index_manager = IndexManager(index_path=index_path)

        # Create cache with old mtime
        now = datetime.now(UTC)
        cache_data = {
            "generated_at": now.isoformat(),
            "ttl_seconds": 300,
            "index_mtime": "2020-01-01T00:00:00+00:00",  # Old mtime
            "project_name": None,
            "since": None,
            "stats": {
                "generated_at": now.isoformat(),
                "total_runs": 88888,
            },
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        aggregator = StatsAggregator(
            index_manager=index_manager,
            cache_path=cache_path,
        )

        stats = aggregator.get_global_stats()

        # Should get fresh stats (0 runs from empty index), not cached 88888
        assert stats.total_runs == 0

    def test_cache_invalidated_on_different_filters(self, tmp_path: Path) -> None:
        """Cache is invalidated when filter parameters differ."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.core.index_manager import IndexManager

        cache_path = tmp_path / "cache.json"
        index_manager = IndexManager(index_path=tmp_path / "index.jsonl")

        # Create cache for project "foo"
        now = datetime.now(UTC)
        cache_data = {
            "generated_at": now.isoformat(),
            "ttl_seconds": 300,
            "index_mtime": None,
            "project_name": "foo",  # Cache for project "foo"
            "since": None,
            "stats": {
                "generated_at": now.isoformat(),
                "total_runs": 77777,
            },
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        aggregator = StatsAggregator(
            index_manager=index_manager,
            cache_path=cache_path,
        )

        # Request for project "bar"
        stats = aggregator.get_global_stats(project_name="bar")

        # Should get fresh stats, not cached (different project filter)
        assert stats.total_runs == 0

    def test_force_refresh_bypasses_cache(self, tmp_path: Path) -> None:
        """force_refresh=True bypasses valid cache."""
        from adw.core.stats_aggregator import StatsAggregator
        from adw.core.index_manager import IndexManager

        cache_path = tmp_path / "cache.json"
        index_manager = IndexManager(index_path=tmp_path / "index.jsonl")

        # Create a valid cache
        now = datetime.now(UTC)
        cache_data = {
            "generated_at": now.isoformat(),
            "ttl_seconds": 300,
            "index_mtime": None,
            "project_name": None,
            "since": None,
            "stats": {
                "generated_at": now.isoformat(),
                "total_runs": 66666,
            },
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        aggregator = StatsAggregator(
            index_manager=index_manager,
            cache_path=cache_path,
        )

        # Force refresh should bypass cache
        stats = aggregator.get_global_stats(force_refresh=True)

        assert stats.total_runs == 0  # Fresh, not cached 66666
