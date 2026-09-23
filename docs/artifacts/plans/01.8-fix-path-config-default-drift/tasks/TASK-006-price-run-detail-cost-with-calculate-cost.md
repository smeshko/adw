# TASK-006: Price run-detail cost with calculate_cost

Depends on: TASK-001
Suggested commit: `fix(dashboard): price run detail with the analytics cost model`

## Goal

Run detail prices the run total and each phase through `StatsAggregator.calculate_cost`, using the same parsed llm response files as analytics. For one run, both pages show the same cost.

## Files

- `src/adw/core/stats_aggregator.py`:
  - New `get_phase_token_usage(self, run_dir: Path) -> dict[str, TokenUsage]`. It globs `run_dir / "llm" / "*_response.json"` and takes the phase from the filename (`NNN_<phase>_response.json`: drop the leading `NNN_` and the trailing `_response.json`). It sums `stats.input_tokens`, `stats.output_tokens` and `stats.total_cost_usd` per phase, keeps today's warning on unreadable files, and returns `{}` when `llm/` is missing.
  - `_parse_llm_response_files(run_dir)` becomes the field-wise sum of `get_phase_token_usage(run_dir).values()`, and keeps its debug logs.
- `src/adw/dashboard/routes.py`:
  - `run_detail` gains `stats_aggregator: StatsAggregator = Depends(get_stats_aggregator)` and passes it to `_build_run_detail_context`.
  - `_build_run_detail_context(run_entry, request, name_map, stats_aggregator)` calls `phase_usage = stats_aggregator.get_phase_token_usage(runs_dir / run_id)`.
  - `estimated_cost = stats_aggregator.calculate_cost(<sum of phase_usage>)`.
  - Per-phase `cost = stats_aggregator.calculate_cost(phase_usage.get(phase_key, TokenUsage()))`.
  - Delete both `0.000009` lines and their comment.
- `tests/unit/core/test_stats_aggregator.py`: add `TestPhaseTokenUsage`.
- `tests/unit/dashboard/test_run_detail.py`:
  - Rewrite `test_phases_detail_shows_cost_estimates` against a real `StatsAggregator` and llm files in `tmp_path`.
  - Add `test_run_detail_cost_matches_analytics`.

## Acceptance

- [ ] `TestPhaseTokenUsage::test_groups_response_files_by_phase` covers files `001_plan_response.json`, `002_build_response.json` and `006_build_response.json`, the last being a retry: it returns `plan` and `build`, with `build` summed.
- [ ] `TestPhaseTokenUsage::test_missing_llm_dir_returns_empty`.
- [ ] `test_phases_detail_shows_cost_estimates`:
  - Setup: plan `{input 1_000_000, output 0}` and build `{input 0, output 100_000}` under `DEFAULT_PRICING["default"]`.
  - It shows `$3.00` and `$1.50`: `DEFAULT_PRICING["default"]` is $3/$15 per 1M input/output tokens.
- [ ] `test_run_detail_cost_matches_analytics`:
  - Setup: one registered project in `tmp_path` with one run. The run has two response files, a `context.json` and an index entry.
  - `GET /runs/{id}` and `GET /analytics` (with `HX-Request`) both contain the same `$N.NN`. The value is `calculate_cost` of the summed usage.
  - Both pages use a real `StatsAggregator(index_manager=…, project_registry=…, cache_path=tmp_path / "cache.json")`.
- [ ] `grep -rn "0.000009" src` returns nothing.
- [ ] The existing `TestStatsAggregator`/analytics tests still pass, so `_parse_llm_response_files` still totals the same numbers.
- [ ] `uv run pytest tests/unit/core/test_stats_aggregator.py tests/unit/dashboard -o addopts=""` passes.

Evidence:
- the RED run: `test_run_detail_cost_matches_analytics` and the rewritten cost test fail on the `0.000009` pricing, and `TestPhaseTokenUsage` fails with `AttributeError`
- the GREEN run
- the empty grep

## Steps

### RED
- [ ] Add `TestPhaseTokenUsage`, with 2 tests.
- [ ] Rewrite `test_phases_detail_shows_cost_estimates`:
  - Write `context.json` through `ContextManager`, or keep the `ContextManager` patch, and put the llm files under `tmp_path/.adw/runs/<id>/llm/`.
  - Point the index entry's `project_path` at `tmp_path`.
  - Override `get_stats_aggregator` with a real aggregator.
- [ ] Add `test_run_detail_cost_matches_analytics`:
  - Register the project through a mocked `ProjectRegistryManager.get_all()` that returns one project with `path=str(tmp_path)`.
  - The index mock's `get_recent_runs` returns the single entry.
  - Parse `$N.NN` from both responses.
- [ ] Run them and confirm they fail.

### GREEN
- [ ] Add `get_phase_token_usage`, and re-express `_parse_llm_response_files` as its sum.
- [ ] Wire `stats_aggregator` into `run_detail` → `_build_run_detail_context`, and price with `calculate_cost`.
- [ ] Run the tests and confirm they are green.

### REFACTOR
- [ ] Other `test_run_detail.py` tests that render the detail page with `MagicMock` aggregators:
  - Configure `sa.get_phase_token_usage.return_value = {}` and `sa.calculate_cost.return_value = 0.0` in `_make_client_with_mocks`, so they keep passing without disk fixtures.
  - The cost display then shows `—`, as today for zero cost.
- [ ] `scripts/preflight.sh` passes.

## Notes

- Summing `TokenUsage` field by field matches the existing style in `get_global_stats`. Don't add `TokenUsage.__add__` in this task.
- `StatsAggregator.get_token_usage` stays untouched and unused. Phase 1.2 deletes it.
- A file whose name doesn't match `NNN_<phase>_response.json` goes under the key it strips to, or is skipped if it doesn't parse. It must not crash the page.
