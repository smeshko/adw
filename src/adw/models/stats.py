"""Statistics models for cross-project analytics.

This module provides Pydantic models for representing aggregate
statistics across all ADW projects.

Models:
    TokenUsage: Token counts for input and output tokens.
    ProjectStatistics: Statistics for a single project.
    GlobalStatistics: Aggregate statistics across all projects.
"""

from datetime import datetime

from pydantic import BaseModel, Field

__all__ = [
    "GlobalStatistics",
    "ProjectStatistics",
    "TokenUsage",
]


class TokenUsage(BaseModel):
    """Token usage statistics for a run or aggregate.

    Attributes:
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.

    Example:
        >>> usage = TokenUsage(input_tokens=1000, output_tokens=500)
        >>> usage.total_tokens
        1500
    """

    input_tokens: int = Field(default=0, description="Input tokens consumed")
    output_tokens: int = Field(default=0, description="Output tokens generated")
    actual_cost_usd: float = Field(
        default=0.0, description="Actual cost in USD from Claude Code"
    )

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        return self.input_tokens + self.output_tokens


class ProjectStatistics(BaseModel):
    """Statistics for a single project.

    Attributes:
        name: Project name (typically directory name).
        path: Absolute path to the project.
        total_runs: Total number of runs for this project.
        completed_runs: Number of successfully completed runs.
        failed_runs: Number of failed runs.
        success_rate: Ratio of completed to total finished runs (0.0-1.0).
        average_duration_ms: Average run duration in milliseconds.
        tokens: Aggregate token usage for this project.
        estimated_cost: Estimated cost in USD based on token usage.

    Example:
        >>> stats = ProjectStatistics(
        ...     name="my-api",
        ...     path="/path/to/my-api",
        ...     total_runs=100,
        ...     success_rate=0.95,
        ... )
    """

    name: str
    path: str
    total_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    success_rate: float = 0.0
    average_duration_ms: int = 0
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    estimated_cost: float = 0.0


class GlobalStatistics(BaseModel):
    """Aggregate statistics across all projects.

    Attributes:
        generated_at: When these statistics were calculated.
        total_runs: Total number of runs across all projects.
        runs_this_week: Runs started in the last 7 days.
        runs_today: Runs started today.
        completed_runs: Total successfully completed runs.
        failed_runs: Total failed runs.
        success_rate: Overall success rate (0.0-1.0).
        average_duration_ms: Average run duration in milliseconds.
        tokens: Aggregate token usage across all projects.
        estimated_cost: Total estimated cost in USD.
        projects: Per-project breakdown of statistics.

    Example:
        >>> from datetime import datetime, UTC
        >>> stats = GlobalStatistics(
        ...     generated_at=datetime.now(UTC),
        ...     total_runs=1247,
        ...     runs_this_week=89,
        ...     success_rate=0.943,
        ... )
    """

    generated_at: datetime
    total_runs: int = 0
    runs_this_week: int = 0
    runs_today: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    success_rate: float = 0.0
    average_duration_ms: int = 0
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    estimated_cost: float = 0.0
    projects: list[ProjectStatistics] = Field(default_factory=list)

    # Trend comparison fields (previous week = 7–14 days ago)
    previous_week_total_runs: int = 0
    previous_week_success_rate: float = 0.0
    previous_week_average_duration_ms: int = 0
    tokens_this_week: TokenUsage = Field(default_factory=TokenUsage)
    cost_this_week: float = 0.0
