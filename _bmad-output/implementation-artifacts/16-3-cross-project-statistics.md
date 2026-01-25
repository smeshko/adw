# Story 16.3: Cross-Project Statistics

Status: ready
Linear Issue: not-configured
Epic: 16 - Cross-Project Dashboard
Created: 2026-01-25

---

## Story

As a user,
I want to see aggregate statistics across all my projects,
so that I can understand my overall ADW usage patterns.

## Acceptance Criteria

**Given** command `adw global stats`
**When** executed
**Then** displays aggregate metrics across all projects

**Given** the statistics output
**When** displayed
**Then** includes:
- Total runs (all time, this week, today)
- Success rate overall and per project
- Average run duration
- Total token usage (from LLM response files)
- Estimated cost (based on model pricing)

**Given** command `adw global stats --project my-api`
**When** executed
**Then** shows statistics for that project only

**Given** command `adw global stats --format json`
**When** executed
**Then** outputs machine-readable JSON for integration

## Tasks / Subtasks

### Task 1: Create Statistics Models
- [x] Create `src/adw/models/stats.py` with:
  - `TokenUsage` model: `input_tokens: int`, `output_tokens: int`, `total_tokens: int`
  - `RunStatistics` model: aggregate run metrics
  - `ProjectStatistics` model: per-project breakdown
  - `GlobalStatistics` model: all stats combined
- [x] Export from `src/adw/models/__init__.py`
- [x] Write unit tests in `tests/unit/models/test_stats.py`

### Task 2: Create Model Pricing Configuration
- [ ] Define default pricing table for models in `src/adw/core/stats_aggregator.py`:
  - `claude-3-5-sonnet`: $3.00 / 1M input, $15.00 / 1M output
  - `claude-3-opus`: $15.00 / 1M input, $75.00 / 1M output
  - `claude-3-haiku`: $0.25 / 1M input, $1.25 / 1M output
  - Allow override via `~/.adw/config.yaml` under `pricing` key
- [ ] Create `ModelPricing` model for pricing configuration
- [ ] Write unit tests for cost calculation

### Task 3: Create StatsAggregator Core Class
- [ ] Create `src/adw/core/stats_aggregator.py` with `StatsAggregator` class
- [ ] Implement methods:
  - `get_global_stats(project_name: str | None = None) -> GlobalStatistics`
  - `get_token_usage(run_id: str, project_path: Path) -> TokenUsage | None`
  - `calculate_cost(tokens: TokenUsage, model: str) -> float`
  - `_collect_llm_stats(project_path: Path, run_id: str) -> dict`
- [ ] Support `ADW_TEST_STATS_CACHE_PATH` env var for testing
- [ ] Write unit tests in `tests/unit/core/test_stats_aggregator.py`

### Task 4: Implement LLM Response File Parsing
- [ ] Create method `_parse_llm_response_files(run_dir: Path) -> TokenUsage`
- [ ] Read `*.json` files from `{project_path}/.adw/runs/{run_id}/llm/` directory
- [ ] Extract `stats.input_tokens`, `stats.output_tokens`, `stats.duration_ms` from each response
- [ ] Handle missing stats gracefully (some responses may not have stats)
- [ ] Sum tokens across all response files for a run
- [ ] Write unit tests with fixture files

### Task 5: Implement Statistics Cache
- [ ] Create cache file at `~/.adw/stats-cache.json`
- [ ] Cache structure:
  ```json
  {
    "generated_at": "2026-01-25T10:00:00Z",
    "ttl_seconds": 300,
    "stats": { ... }
  }
  ```
- [ ] Invalidate cache when:
  - TTL expired (default 5 minutes)
  - `~/.adw/index.jsonl` modified time changed
  - `--force` flag used
- [ ] Create `_load_cache()` and `_save_cache()` methods
- [ ] Write unit tests for cache behavior

### Task 6: Implement `adw global stats` Command
- [ ] Add `stats` command to `src/adw/cli/global_commands.py`
- [ ] Accept options:
  - `--project, -p NAME` - Filter to specific project
  - `--format FORMAT` - Output format: `table` (default) or `json`
  - `--force` - Ignore cache, recalculate stats
  - `--since DURATION` - Only include runs from this period (e.g., 7d, 30d)
- [ ] Display Rich formatted output with panels
- [ ] Write unit tests in `tests/unit/cli/test_global_commands.py`

### Task 7: Create StatsDisplay Helper Class
- [ ] Create display helper in `src/adw/cli/global_commands.py`:
  - `show_global_stats(stats: GlobalStatistics)` - Rich panels/tables
  - `_format_tokens(count: int) -> str` - e.g., "1.2M", "450K"
  - `_format_cost(amount: float) -> str` - e.g., "$12.45"
  - `_format_duration(ms: int) -> str` - e.g., "4m 32s"
  - `_format_rate(rate: float) -> str` - e.g., "94.3%"
- [ ] Create summary panel with key metrics
- [ ] Create per-project breakdown table
- [ ] Write unit tests for display formatting

### Task 8: Implement JSON Output Format
- [ ] Add `--format json` support
- [ ] Output structure:
  ```json
  {
    "generated_at": "2026-01-25T10:30:00Z",
    "period": "all_time",
    "total_runs": 1247,
    "runs_this_week": 89,
    "runs_today": 12,
    "success_rate": 0.943,
    "average_duration_ms": 263000,
    "total_tokens": {
      "input": 2400000,
      "output": 148000,
      "total": 2548000
    },
    "estimated_cost": 47.82,
    "projects": [
      {
        "name": "my-api",
        "path": "/path/to/my-api",
        "runs": 423,
        "success_rate": 0.962,
        "tokens": { ... },
        "cost": 18.24
      }
    ]
  }
  ```
- [ ] Write tests for JSON output format

### Task 9: Write Integration Tests
- [ ] Test full flow: create runs with LLM files -> `adw global stats` -> verify output
- [ ] Test `--project` filter
- [ ] Test `--format json` output
- [ ] Test cache behavior (fresh, cached, invalidated)
- [ ] Test with missing LLM files (graceful degradation)
- [ ] Test with empty index
- [ ] Create integration tests in `tests/integration/cli/test_global_stats_integration.py`

### Task 10: Update Documentation
- [ ] Add docstrings to all new classes and methods
- [ ] Update `adw global stats --help` with examples
- [ ] Document pricing configuration in `~/.adw/config.yaml`

---

## Dependencies

- **Depends On:** Story 16.1 (Project Registry), Story 16.2 (Global Run List)
- **Blocks:** 16.5 (TUI Dashboard)
- **Can Parallel With:** None

### Dependency Rationale
- Story 16.1 provides `ProjectRegistryManager` for project discovery
- Story 16.2 provides `IndexManager` query extensions (`project_name`, `since` filters)
- Story 16.2 provides the `global_app` Typer subapp where `stats` command will be added
- Story 16.5 dashboard will use `StatsAggregator` for statistics panels

---

## Relevant Feature Documentation

**Related Patterns:**
- CLI subapp commands: See `src/adw/cli/global_commands.py` (from Story 16.2)
- Index querying: See `src/adw/core/index_manager.py` - `get_recent_runs()` method
- LLM response structure: See `src/adw/models/llm.py` - `LLMResult` model
- Rich display: See `src/adw/cli/list.py` - `_display_index_entries()` function

**Key Files to Reference:**
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/core/index_manager.py` - Query patterns
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/models/llm.py` - LLMResult with tokens_used, duration_ms
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/cli/list.py` - CLI display patterns
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/cli/list_display.py` - Display helper pattern
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/models/index.py` - IndexEntry model

---

## Developer Context

### Technical Requirements

1. **LLM Response File Structure**
   Location: `{project_path}/.adw/runs/{run_id}/llm/*_response.json`

   Example from real run file:
   ```json
   {
     "timestamp": "2026-01-17T14:00:30.272088Z",
     "content": "...",
     "phase": "build",
     "tool_calls": [...],
     "stats": {
       "input_tokens": 0,
       "output_tokens": 13266,
       "duration_ms": 156671
     }
   }
   ```

   Note: The `input_tokens` may be 0 in some responses (streaming scenario). Actual token counts should be summed from all response files in the run's `llm/` directory.

2. **Statistics Calculation Logic**
   ```python
   # Total runs: count from IndexManager
   total_runs = len(index_manager.get_recent_runs(limit=99999))

   # Runs this week: filter by started_at >= 7 days ago
   week_ago = datetime.now(UTC) - timedelta(days=7)
   runs_this_week = len([r for r in all_runs if r.started_at >= week_ago])

   # Success rate: completed / (completed + failed)
   success_rate = completed_count / (completed_count + failed_count)

   # Average duration: mean of (completed_at - started_at) for completed runs
   avg_duration = sum(durations) / len(durations)

   # Token usage: sum from LLM response files
   # Cost: tokens * pricing[model]
   ```

3. **Pricing Configuration (in `~/.adw/config.yaml`)**
   ```yaml
   pricing:
     # Price per 1M tokens (input/output)
     claude-3-5-sonnet:
       input: 3.00
       output: 15.00
     claude-3-opus:
       input: 15.00
       output: 75.00
     claude-3-haiku:
       input: 0.25
       output: 1.25
     default:
       input: 3.00
       output: 15.00
   ```

4. **Cache File Structure (`~/.adw/stats-cache.json`)**
   ```json
   {
     "generated_at": "2026-01-25T10:00:00Z",
     "index_mtime": "2026-01-25T09:55:00Z",
     "ttl_seconds": 300,
     "global_stats": { ... },
     "project_stats": { ... }
   }
   ```

### Architecture Compliance

**File Locations:**
```
src/adw/
├── models/
│   └── stats.py              # NEW: Statistics models
├── core/
│   └── stats_aggregator.py   # NEW: StatsAggregator class
└── cli/
    └── global_commands.py    # MODIFY: Add stats command
tests/
├── unit/
│   ├── models/
│   │   └── test_stats.py     # NEW: Model tests
│   ├── core/
│   │   └── test_stats_aggregator.py  # NEW: Aggregator tests
│   └── cli/
│       └── test_global_commands.py   # MODIFY: Add stats tests
└── integration/cli/
    └── test_global_stats_integration.py  # NEW: Integration tests
```

**Model Pattern (from models/index.py):**
```python
# src/adw/models/stats.py
from datetime import datetime
from pydantic import BaseModel, Field

class TokenUsage(BaseModel):
    """Token usage statistics for a run or aggregate."""
    input_tokens: int = Field(default=0, description="Input tokens consumed")
    output_tokens: int = Field(default=0, description="Output tokens generated")

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        return self.input_tokens + self.output_tokens


class ProjectStatistics(BaseModel):
    """Statistics for a single project."""
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
    """Aggregate statistics across all projects."""
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
```

**StatsAggregator Pattern:**
```python
# src/adw/core/stats_aggregator.py
"""Cross-project statistics aggregator.

This module provides the StatsAggregator class for collecting and
computing statistics across all ADW projects.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from adw.core.index_manager import IndexManager
from adw.models.stats import GlobalStatistics, ProjectStatistics, TokenUsage

logger = logging.getLogger(__name__)

__all__ = ["StatsAggregator"]

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
    ) -> None:
        """Initialize the StatsAggregator.

        Args:
            index_manager: Optional IndexManager instance.
            cache_path: Path to cache file. Defaults to ~/.adw/stats-cache.json.
            pricing: Model pricing override.
        """
        import os

        self.index_manager = index_manager or IndexManager()

        env_cache_path = os.environ.get("ADW_TEST_STATS_CACHE_PATH")
        if cache_path is not None:
            self.cache_path = cache_path
        elif env_cache_path:
            self.cache_path = Path(env_cache_path)
        else:
            self.cache_path = Path.home() / ".adw" / "stats-cache.json"

        self.pricing = pricing or DEFAULT_PRICING

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
        """Collect statistics from index and LLM files."""
        # Implementation details...
        pass

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
```

**CLI Command Pattern (add to global_commands.py):**
```python
@global_app.command(name="stats")
def stats_command(
    project: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Filter to specific project name",
    ),
    format_output: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table or json",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Ignore cache, recalculate statistics",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Only include runs from this period (e.g., 7d, 30d)",
    ),
) -> None:
    """Show aggregate statistics across all projects.

    Displays run counts, success rates, token usage, and estimated costs
    for all registered ADW projects.

    Examples:
        adw global stats                    # Show all statistics
        adw global stats --project my-api   # Stats for one project
        adw global stats --format json      # JSON output
        adw global stats --since 30d        # Last 30 days only
        adw global stats --force            # Ignore cache
    """
    # Implementation here
    ...
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| Typer | 0.21.0 | CLI commands |
| Rich | 14.1.0 | Panels, tables, formatting |
| Pydantic | 2.12+ | Statistics models |
| PyYAML | 6.0+ | Pricing config |

**No New Dependencies Required**

### File Structure Requirements

**New Files:**
- `src/adw/models/stats.py` - Statistics models
- `src/adw/core/stats_aggregator.py` - StatsAggregator class
- `tests/unit/models/test_stats.py` - Model tests
- `tests/unit/core/test_stats_aggregator.py` - Aggregator tests
- `tests/integration/cli/test_global_stats_integration.py` - Integration tests

**Modified Files:**
- `src/adw/models/__init__.py` - Export TokenUsage, ProjectStatistics, GlobalStatistics
- `src/adw/cli/global_commands.py` - Add `stats` command

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/models/test_stats.py
class TestTokenUsage:
    def test_total_tokens_property(self):
        """total_tokens returns sum of input and output."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150

    def test_default_values(self):
        """Default values are zero."""
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0


class TestProjectStatistics:
    def test_success_rate_calculation(self): ...
    def test_default_tokens(self): ...


class TestGlobalStatistics:
    def test_includes_projects_list(self): ...
    def test_generated_at_required(self): ...


# tests/unit/core/test_stats_aggregator.py
class TestStatsAggregator:
    def test_get_global_stats_returns_statistics(self, mock_index): ...
    def test_project_filter(self, mock_index): ...
    def test_since_filter(self, mock_index): ...
    def test_force_refresh_ignores_cache(self): ...
    def test_cache_is_used_when_valid(self): ...
    def test_cache_invalidated_on_index_change(self): ...


class TestParseLLMResponseFiles:
    def test_parses_response_files(self, tmp_path):
        """Parses token stats from response files."""
        llm_dir = tmp_path / "llm"
        llm_dir.mkdir()

        # Create test response file
        response = {
            "timestamp": "2026-01-25T10:00:00Z",
            "stats": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "duration_ms": 5000
            }
        }
        (llm_dir / "001_plan_response.json").write_text(json.dumps(response))

        aggregator = StatsAggregator()
        usage = aggregator._parse_llm_response_files(tmp_path)

        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500

    def test_handles_missing_llm_dir(self, tmp_path):
        """Returns empty TokenUsage when llm/ doesn't exist."""
        aggregator = StatsAggregator()
        usage = aggregator._parse_llm_response_files(tmp_path)

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_handles_corrupted_files(self, tmp_path):
        """Skips corrupted files gracefully."""
        llm_dir = tmp_path / "llm"
        llm_dir.mkdir()
        (llm_dir / "001_plan_response.json").write_text("invalid json")

        aggregator = StatsAggregator()
        usage = aggregator._parse_llm_response_files(tmp_path)

        assert usage.input_tokens == 0


class TestCalculateCost:
    def test_default_pricing(self):
        """Uses default pricing when model not found."""
        aggregator = StatsAggregator()
        tokens = TokenUsage(input_tokens=1_000_000, output_tokens=100_000)

        cost = aggregator.calculate_cost(tokens)

        # default: $3/1M input, $15/1M output
        # 1M input = $3, 0.1M output = $1.50
        assert cost == 4.50

    def test_specific_model_pricing(self):
        """Uses model-specific pricing."""
        aggregator = StatsAggregator()
        tokens = TokenUsage(input_tokens=1_000_000, output_tokens=100_000)

        cost = aggregator.calculate_cost(tokens, model="claude-3-haiku")

        # haiku: $0.25/1M input, $1.25/1M output
        # 1M input = $0.25, 0.1M output = $0.125
        assert cost == 0.38  # rounded


# tests/unit/cli/test_global_commands.py - additions
class TestGlobalStatsCommand:
    def test_stats_default_output(self, mock_aggregator): ...
    def test_stats_project_filter(self, mock_aggregator): ...
    def test_stats_json_format(self, mock_aggregator): ...
    def test_stats_force_flag(self, mock_aggregator): ...
    def test_stats_since_filter(self, mock_aggregator): ...
```

**Test Coverage Target:** >80%

---

## Previous Story Intelligence

**From Story 16.1 (Project Registry):**
- Registry file location: `~/.adw/projects.yaml`
- `ProjectRegistryManager.get_all()` returns registered projects
- Projects have `path`, `name`, `registered_at` fields
- Environment variable pattern: `ADW_TEST_REGISTRY_PATH`

**From Story 16.2 (Global Run List):**
- `global_app` Typer subapp established in `src/adw/cli/global_commands.py`
- Duration parsing: `parse_duration("7d")` returns datetime threshold
- IndexManager extended with `project_name` and `since` filters
- Status color mapping: running=blue, completed=green, failed=red

**LLM Response File Structure (from codebase analysis):**
- Files located at: `{project}/.adw/runs/{run_id}/llm/*_response.json`
- Each response contains: `timestamp`, `content`, `phase`, `tool_calls`, `stats`
- Stats object contains: `input_tokens`, `output_tokens`, `duration_ms`
- Multiple response files per run (one per phase): `001_plan_response.json`, `002_build_response.json`, etc.

---

## Git Intelligence

**Recent Relevant Commits:**
- Story 16.2: Global run list command with filters
- Story 16.1: Project registry and CLI commands
- Story 7.0: IndexManager with JSONL index

**Established Patterns:**
- Subapp commands in `global_commands.py`
- Environment variables for test path overrides: `ADW_TEST_*_PATH`
- Cache files in `~/.adw/` directory
- Rich panels and tables for CLI output
- JSON output via `--format json` or `--json` flag

---

## Latest Technical Information

**Rich Panels and Tables (2025):**
- Use `Panel(Columns([...]))` for summary cards
- Use `Table()` for tabular data
- Use `Text()` with markup for formatted numbers
- Use `Panel(Group(...))` for nested layouts

**Token Pricing (2025):**
- Claude 3.5 Sonnet: $3/1M input, $15/1M output (best value)
- Claude 3 Opus: $15/1M input, $75/1M output (highest capability)
- Claude 3 Haiku: $0.25/1M input, $1.25/1M output (fastest)
- Prices may change; allow configuration override

**Statistics Best Practices:**
- Cache expensive calculations with TTL
- Graceful degradation when data unavailable
- Show "N/A" or "—" for missing metrics
- Include timestamp of last calculation

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **All models in models/**: TokenUsage, ProjectStatistics, GlobalStatistics go in `models/`
- **Type annotations required**: All functions fully typed
- **Rich for CLI output**: Use Rich Console, Panels, Tables
- **Structured logging**: Use logger with structured fields
- **Exception hierarchy**: Use ADWError if stats operations fail
- **Context managers**: Use for file operations

---

## Dev Notes

### Implementation Approach

1. **Create statistics models** - Foundation for data structures
2. **Implement LLM file parsing** - Core data collection
3. **Create StatsAggregator** - Main orchestration class
4. **Add cache mechanism** - Performance optimization
5. **Implement CLI command** - User interface
6. **Add display formatting** - Rich output
7. **Write comprehensive tests** - Ensure reliability

### Key Design Decisions

1. **Cache with TTL**: Statistics are expensive to compute (reading many files). Cache for 5 minutes by default, invalidate when index changes.

2. **Graceful Degradation**: If LLM files are missing or unreadable, show "—" for token/cost metrics rather than failing.

3. **Default Pricing**: Include sensible defaults so stats work out-of-box. Allow override in `~/.adw/config.yaml` for users who want custom rates.

4. **Per-Project Breakdown**: Always show both aggregate and per-project stats. Users want to see which projects consume most resources.

5. **Environment Variable Override**: Follow `ADW_TEST_*_PATH` pattern for cache path to enable isolated testing.

### CLI Output Examples

**`adw global stats` output:**
```
╭──────────────────────── ADW Global Statistics ─────────────────────────╮
│                                                                        │
│  ╭─────────────╮  ╭─────────────╮  ╭─────────────╮  ╭─────────────╮   │
│  │ TOTAL RUNS  │  │ THIS WEEK   │  │    TODAY    │  │SUCCESS RATE │   │
│  │             │  │             │  │             │  │             │   │
│  │    1,247    │  │     89      │  │     12      │  │   94.3%     │   │
│  ╰─────────────╯  ╰─────────────╯  ╰─────────────╯  ╰─────────────╯   │
│                                                                        │
│  AVG DURATION: 4m 23s    TOTAL TOKENS: 2.4M    EST. COST: $47.82      │
│                                                                        │
╰────────────────────────────────────────────────────────────────────────╯

                        Per-Project Breakdown
┌───────────────┬────────────────────────────────┬───────┬─────────┬──────────┬─────────┐
│ Project       │ Path                           │ Runs  │ Success │ Tokens   │ Cost    │
├───────────────┼────────────────────────────────┼───────┼─────────┼──────────┼─────────┤
│ adw-final     │ ~/Developer/Projects/adw/adw-… │   423 │  96.2%  │    892K  │  $18.24 │
│ myapp-backend │ ~/Developer/Projects/myapp-b…  │   512 │  93.8%  │    1.1M  │  $21.45 │
│ frontend-ui   │ ~/Developer/Projects/frontend… │   312 │  91.7%  │    412K  │   $8.13 │
└───────────────┴────────────────────────────────┴───────┴─────────┴──────────┴─────────┘

  Generated: 2 minutes ago (cached)
```

**`adw global stats --project my-api` output:**
```
╭──────────────────── Statistics: my-api ────────────────────╮
│                                                            │
│  Path: /Users/dev/projects/my-api                          │
│                                                            │
│  ╭───────────╮ ╭───────────╮ ╭───────────╮ ╭───────────╮  │
│  │   RUNS    │ │ THIS WEEK │ │   TODAY   │ │  SUCCESS  │  │
│  │    512    │ │    34     │ │     5     │ │   93.8%   │  │
│  ╰───────────╯ ╰───────────╯ ╰───────────╯ ╰───────────╯  │
│                                                            │
│  AVG DURATION: 5m 12s                                      │
│  TOKENS: 1.1M (input: 920K / output: 180K)                 │
│  ESTIMATED COST: $21.45                                    │
│                                                            │
│  ╭─────────────── Status Breakdown ───────────────╮       │
│  │ ✓ COMPLETED   480  ████████████████████  93.8% │       │
│  │ ✗ FAILED       22  █░░░░░░░░░░░░░░░░░░░   4.3% │       │
│  │ ⊘ INTERRUPTED  10  ░░░░░░░░░░░░░░░░░░░░   1.9% │       │
│  ╰────────────────────────────────────────────────╯       │
│                                                            │
╰────────────────────────────────────────────────────────────╯
```

**Empty/No Data State:**
```
╭──────────────────── ADW Global Statistics ────────────────────╮
│                                                               │
│                      No statistics available                  │
│                                                               │
│   No runs found in the global index.                          │
│                                                               │
│   Get started:                                                │
│   1. Run 'adw init' in a project directory                    │
│   2. Run 'adw run "your feature"' to create runs              │
│   3. Run 'adw global stats' to see statistics                 │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
```

### Token/Cost Formatting

```python
def _format_tokens(count: int) -> str:
    """Format token count for display.

    Examples:
        1234 -> "1.2K"
        1234567 -> "1.2M"
        123456789 -> "123.5M"
    """
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)


def _format_cost(amount: float) -> str:
    """Format cost for display.

    Examples:
        47.82 -> "$47.82"
        0.05 -> "$0.05"
        1234.56 -> "$1,234.56"
    """
    if amount >= 1000:
        return f"${amount:,.2f}"
    return f"${amount:.2f}"
```

### References

- [Source: _bmad-output/epics/epic-16-cross-project-dashboard.md#Story 16.3]
- [Source: src/adw/core/index_manager.py - Query patterns]
- [Source: src/adw/models/llm.py - LLMResult model with tokens_used]
- [Source: .adw/runs/*/llm/*_response.json - LLM response file structure]
- [Source: _bmad-output/implementation-artifacts/16-2-global-run-list.md - global_app pattern]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

---

## Dev Agent Record

### Context Reference

Epic 16: Cross-Project Dashboard - Story 16.3

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

- Task 1: Created TokenUsage, ProjectStatistics, GlobalStatistics models in src/adw/models/stats.py. Exported from models package. Added 14 unit tests covering all model functionality.

### File List

- src/adw/models/stats.py (NEW)
- src/adw/models/__init__.py (MODIFIED)
- tests/unit/models/test_stats.py (NEW)

---

## Dependencies

- **Depends On:** Story 16.1, Story 16.2
- **Blocks:** Story 16.5
- **Can Parallel With:** None

### Dependency Rationale
- Story 16.1: Needs project registry for project-level statistics filtering
- Story 16.2: Builds on global CLI infrastructure and IndexManager extensions
- Story 16.5: Dashboard summary panel displays statistics data from StatsAggregator
