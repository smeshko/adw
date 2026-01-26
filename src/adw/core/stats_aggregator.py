"""Cross-project statistics aggregator.

This module provides the StatsAggregator class for collecting and
computing statistics across all ADW projects.
"""

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from adw.core.index_manager import IndexManager
from adw.core.project_registry import ProjectRegistryManager
from adw.models.stats import GlobalStatistics, ProjectStatistics, TokenUsage

logger = logging.getLogger(__name__)

__all__ = ["StatsAggregator", "DEFAULT_PRICING", "DEFAULT_CACHE_TTL"]

# Default model pricing (per 1M tokens)
DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "default": {"input": 3.00, "output": 15.00},
}

# Cache TTL in seconds (5 minutes)
DEFAULT_CACHE_TTL = 300


class StatsAggregator:
    """Aggregates statistics across all ADW projects.

    Collects run statistics from the global index and token usage
    from LLM response files in each project's run directories.

    Attributes:
        index_manager: IndexManager for querying runs.
        cache_path: Path to stats cache file.
        pricing: Model pricing configuration.

    Example:
        >>> aggregator = StatsAggregator()
        >>> stats = aggregator.get_global_stats()
        >>> print(f"Total runs: {stats.total_runs}")
        >>> print(f"Cost: ${stats.estimated_cost:.2f}")
    """

    def __init__(
        self,
        index_manager: IndexManager | None = None,
        cache_path: Path | None = None,
        pricing: dict[str, dict[str, float]] | None = None,
        project_registry: ProjectRegistryManager | None = None,
    ) -> None:
        """Initialize the StatsAggregator.

        Args:
            index_manager: Optional IndexManager instance.
            cache_path: Path to cache file. Defaults to ~/.adw/stats-cache.json.
            pricing: Model pricing override.
            project_registry: Optional ProjectRegistryManager instance.
        """
        self.index_manager = index_manager or IndexManager()
        self.project_registry = project_registry or ProjectRegistryManager()

        env_cache_path = os.environ.get("ADW_TEST_STATS_CACHE_PATH")
        if cache_path is not None:
            self.cache_path = cache_path
        elif env_cache_path:
            self.cache_path = Path(env_cache_path)
        else:
            self.cache_path = Path.home() / ".adw" / "stats-cache.json"

        self.pricing = pricing or DEFAULT_PRICING

    def get_token_usage(
        self,
        run_id: str,
        project_path: Path,
    ) -> TokenUsage | None:
        """Get token usage for a specific run.

        Args:
            run_id: The run ID to look up.
            project_path: Path to the project directory.

        Returns:
            TokenUsage for the run, or None if run directory doesn't exist.
        """
        run_dir = project_path / ".adw" / "runs" / run_id
        if not run_dir.exists():
            return None

        return self._parse_llm_response_files(run_dir)

    def calculate_cost(
        self,
        tokens: TokenUsage,
        model: str = "default",
    ) -> float:
        """Calculate estimated cost for token usage.

        Args:
            tokens: Token usage to price.
            model: Model name for pricing lookup.

        Returns:
            Estimated cost in USD.
        """
        pricing = self.pricing.get(model, self.pricing["default"])

        input_cost = (tokens.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (tokens.output_tokens / 1_000_000) * pricing["output"]

        return round(input_cost + output_cost, 2)

    def _parse_llm_response_files(self, run_dir: Path) -> TokenUsage:
        """Parse all LLM response files in a run directory.

        Args:
            run_dir: Path to run directory (e.g., .adw/runs/{run_id}/)

        Returns:
            Aggregated TokenUsage for the run.
        """
        llm_dir = run_dir / "llm"
        if not llm_dir.exists():
            return TokenUsage()

        total_input = 0
        total_output = 0

        for response_file in llm_dir.glob("*_response.json"):
            try:
                with open(response_file) as f:
                    data = json.load(f)

                stats = data.get("stats", {})
                total_input += stats.get("input_tokens", 0)
                total_output += stats.get("output_tokens", 0)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "Failed to parse LLM response file",
                    extra={"file": str(response_file), "error": str(e)},
                )
                continue

        return TokenUsage(input_tokens=total_input, output_tokens=total_output)

    def get_global_stats(
        self,
        project_name: str | None = None,
        since: datetime | None = None,
        force_refresh: bool = False,
    ) -> GlobalStatistics:
        """Get aggregate statistics across all projects.

        Args:
            project_name: Filter to specific project.
            since: Only include runs after this time.
            force_refresh: Ignore cache, recalculate.

        Returns:
            GlobalStatistics with aggregate metrics.
        """
        # Check cache first (unless force_refresh)
        if not force_refresh:
            cached = self._load_cache(project_name, since)
            if cached is not None:
                return cached

        # Collect fresh statistics
        stats = self._collect_statistics(project_name, since)

        # Save to cache
        self._save_cache(stats, project_name, since)

        return stats

    def _collect_statistics(
        self,
        project_name: str | None,
        since: datetime | None,
    ) -> GlobalStatistics:
        """Collect statistics from index and LLM files.

        Only includes runs from registered projects to avoid polluting
        stats with test/temporary directories.

        Args:
            project_name: Filter to specific project.
            since: Only include runs after this time.

        Returns:
            Collected GlobalStatistics.
        """
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get registered project paths for filtering
        registered_projects = self.project_registry.get_all()
        registered_paths = {p.path for p in registered_projects}

        # Get all runs from index
        entries = self.index_manager.get_recent_runs(
            limit=100000,  # Get all
            project_name=project_name,
            since=since,
        )

        # Filter to only registered projects
        if registered_paths:
            entries = [e for e in entries if e.project_path in registered_paths]

        if not entries:
            return GlobalStatistics(generated_at=now)

        # Aggregate statistics
        total_runs = len(entries)
        runs_this_week = sum(1 for e in entries if e.started_at >= week_ago)
        runs_today = sum(1 for e in entries if e.started_at >= today_start)

        completed_runs = sum(1 for e in entries if e.status == "completed")
        failed_runs = sum(1 for e in entries if e.status == "failed")

        # Calculate success rate
        finished_runs = completed_runs + failed_runs
        success_rate = completed_runs / finished_runs if finished_runs > 0 else 0.0

        # Calculate average duration for completed runs
        durations = []
        for e in entries:
            if e.status == "completed" and e.completed_at:
                duration_ms = int((e.completed_at - e.started_at).total_seconds() * 1000)
                durations.append(duration_ms)

        average_duration_ms = (
            int(sum(durations) / len(durations)) if durations else 0
        )

        # Build lookup of registered project names
        registered_names = {
            p.path: p.name for p in registered_projects
        }

        # Collect token usage from LLM files
        total_tokens = TokenUsage()
        project_stats: dict[str, ProjectStatistics] = {}

        for entry in entries:
            project_path = Path(entry.project_path)
            run_dir = project_path / ".adw" / "runs" / entry.run_id

            # Parse LLM files for this run
            run_tokens = self._parse_llm_response_files(run_dir)

            # Add to totals
            total_tokens = TokenUsage(
                input_tokens=total_tokens.input_tokens + run_tokens.input_tokens,
                output_tokens=total_tokens.output_tokens + run_tokens.output_tokens,
            )

            # Update project statistics - use registered name if available
            proj_name = registered_names.get(entry.project_path, entry.project_name)
            if proj_name not in project_stats:
                project_stats[proj_name] = ProjectStatistics(
                    name=proj_name,
                    path=entry.project_path,
                )

            proj = project_stats[proj_name]
            proj.total_runs += 1
            if entry.status == "completed":
                proj.completed_runs += 1
            elif entry.status == "failed":
                proj.failed_runs += 1

            proj.tokens = TokenUsage(
                input_tokens=proj.tokens.input_tokens + run_tokens.input_tokens,
                output_tokens=proj.tokens.output_tokens + run_tokens.output_tokens,
            )

        # Calculate per-project metrics
        for proj in project_stats.values():
            finished = proj.completed_runs + proj.failed_runs
            proj.success_rate = proj.completed_runs / finished if finished > 0 else 0.0
            proj.estimated_cost = self.calculate_cost(proj.tokens)

        # Calculate total estimated cost
        estimated_cost = self.calculate_cost(total_tokens)

        return GlobalStatistics(
            generated_at=now,
            total_runs=total_runs,
            runs_this_week=runs_this_week,
            runs_today=runs_today,
            completed_runs=completed_runs,
            failed_runs=failed_runs,
            success_rate=round(success_rate, 3),
            average_duration_ms=average_duration_ms,
            tokens=total_tokens,
            estimated_cost=estimated_cost,
            projects=list(project_stats.values()),
        )

    def _load_cache(
        self,
        project_name: str | None,
        since: datetime | None,
    ) -> GlobalStatistics | None:
        """Load statistics from cache if valid.

        Args:
            project_name: Project filter (part of cache key).
            since: Time filter (part of cache key).

        Returns:
            Cached GlobalStatistics or None if cache invalid/missing.
        """
        if not self.cache_path.exists():
            return None

        try:
            with open(self.cache_path) as f:
                cache_data = json.load(f)

            # Check TTL
            generated_at = datetime.fromisoformat(cache_data["generated_at"])
            age_seconds = (datetime.now(UTC) - generated_at).total_seconds()

            if age_seconds > cache_data.get("ttl_seconds", DEFAULT_CACHE_TTL):
                return None

            # Check if filters match
            cached_project = cache_data.get("project_name")
            cached_since = cache_data.get("since")

            if cached_project != project_name:
                return None

            if since:
                if cached_since != since.isoformat():
                    return None
            elif cached_since is not None:
                return None

            # Check if index has been modified
            index_path = self.index_manager.index_path
            if index_path.exists():
                index_mtime = datetime.fromtimestamp(
                    index_path.stat().st_mtime, tz=UTC
                ).isoformat()
                if index_mtime != cache_data.get("index_mtime"):
                    return None

            # Parse cached stats
            return GlobalStatistics.model_validate(cache_data["stats"])

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                "Failed to load stats cache",
                extra={"error": str(e), "path": str(self.cache_path)},
            )
            return None

    def _save_cache(
        self,
        stats: GlobalStatistics,
        project_name: str | None,
        since: datetime | None,
    ) -> None:
        """Save statistics to cache.

        Args:
            stats: Statistics to cache.
            project_name: Project filter used.
            since: Time filter used.
        """
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Get index modification time
            index_mtime = None
            index_path = self.index_manager.index_path
            if index_path.exists():
                index_mtime = datetime.fromtimestamp(
                    index_path.stat().st_mtime, tz=UTC
                ).isoformat()

            cache_data = {
                "generated_at": stats.generated_at.isoformat(),
                "ttl_seconds": DEFAULT_CACHE_TTL,
                "index_mtime": index_mtime,
                "project_name": project_name,
                "since": since.isoformat() if since else None,
                "stats": stats.model_dump(mode="json"),
            }

            with open(self.cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)

        except OSError as e:
            logger.warning(
                "Failed to save stats cache",
                extra={"error": str(e), "path": str(self.cache_path)},
            )
