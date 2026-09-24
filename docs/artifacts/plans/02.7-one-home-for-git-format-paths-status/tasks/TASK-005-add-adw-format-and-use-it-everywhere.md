# TASK-005: Add adw.format and use it everywhere

Depends on: None
Suggested commit: `refactor(format): one formatter each for duration, tokens, time, cost and size`

## Goal

`adw.format` defines one formatter each for duration, tokens, relative time, cost and file size. The CLI, `task_managers/comments.py`, `live.log` and the dashboard use them, the dashboard registers them as Jinja filters, and every private copy is deleted.

## Files

- `src/adw/format.py` (new):
  - `format_duration(seconds: float | None) -> str`
    - `None` → `—`. Negatives clamp to 0. Truncates to whole seconds.
    - `0s`, `45s`; `5m 32s` (60 s to under 1 h); `1h 2m` (1 h and over, seconds dropped).
  - `format_tokens(count: int) -> str`
    - A negative count gets a leading `-` and the format of its absolute value.
    - `999`; `1.2K` (under 10K, one decimal); `12K` / `340K` (10K and up, no decimal); `1.2M`; `2M` (whole millions); `12.3M`.
    - The unit is chosen after rounding: 9,999 → `10K`, 999,999 → `1M`, 999,499 → `999K`. A trailing `.0` is dropped (`1.0K` → `1K`).
  - `format_relative_time(when: datetime | None, *, now: datetime | None = None) -> str`
    - `None` → `—`. A naive `when` is read as UTC. `now` defaults to `datetime.now(UTC)`.
    - A future time → `just now`; then `Ns ago`, `Nm ago`, `Nh ago`, `Nd ago`.
  - `format_cost(amount: float) -> str` → `$0.00`, `$47.82`, `$1,234.56`, and `-$1.00` for a negative.
  - `format_size(size_bytes: int) -> str` → `512 B`, `1.5 KB`, `2.3 MB`, `1.1 GB`, base 1024, one decimal above bytes.
- CLI callers. Delete each private formatter and call the `adw.format` one:
  - `cli/global_commands.py`:
    - `_format_duration(started_at, completed_at)` (`:86`) → `format_duration(((completed_at or now) - started_at).total_seconds())`
    - `_format_duration_ms` (`:445`) → `format_duration(ms / 1000)`
    - `_format_tokens` (`:402`), `_format_cost` (`:425`) and `_format_relative_time` (`:116`)
    - the stats-cache age at `:553`–`:559` → `format_relative_time`
    - `running {hours}h` at `:937`–`:939` → `running {format_duration(...)}`
  - `cli/list.py:395` `_format_elapsed` → `format_duration(seconds)`.
  - `cli/status_display.py:167` `_format_duration` → `format_duration(((context.completed_at or now) - context.started_at).total_seconds())`.
  - `cli/progress.py`: `_format_duration` (`:189`) → `format_duration(ms / 1000 if ms is not None else None)`; `_format_tokens` (`:204`).
  - `cli/projects.py:139` `_format_relative_time(iso)`: parse with `datetime.fromisoformat` at the call site, keep `unknown` on a `ValueError`, and call `format_relative_time`.
  - `cli/dry_run.py:278` `_format_size` → `format_size`.
  - `cli/logs.py:784` `f"{size / 1024:.1f} KB"` → `format_size(size)`.
- `src/adw/task_managers/comments.py:23`: `CommentFormatter._format_duration` → `format_duration`. The three callers (`:133`, `:189`, `:266`) already pass seconds.
- `src/adw/logging/live_stream.py:235`–`:237`: `f"{seconds:.1f}s"` → `format_duration(duration_ms / 1000)`.
- `src/adw/core/stats_aggregator.py:73`: the docstring example `${stats.estimated_cost:.2f}` becomes `format_cost(stats.estimated_cost)`, so the cost grep holds.
- Dashboard Python:
  - `dashboard/routes.py`:
    - delete `_relative_time` (`:56`), `_format_duration_from_seconds` (`:485`) and `_format_file_size` (`:774`), and call the `adw.format` functions
    - the function-level imports of `partials._format_tokens` (`:519`) and `partials._format_elapsed` (`:1396`) become top-level `adw.format` imports
    - the inline `f"${…:.2f}"` at `:655` and `:686` → `format_cost(x) if x > 0 else "—"`
    - `_build_detail_phase_pipeline`'s inline `Xm Ys` (`:466`–`:471`) → `format_duration`
  - `dashboard/partials.py`:
    - delete `_relative_time` (`:45`), `_format_duration` (`:101`, ms), `_format_tokens` (`:111`) and `_format_elapsed` (`:634`, timedelta)
    - callers pass `ms / 1000` or `delta.total_seconds()`
    - the inline costs at `:202`, `:400`, `:418`, `:450`, `:482` and `:489` (abs), and the literal `"$0.00"` at `:408`, → `format_cost`
    - `:154` and `:163` pass `format_cost(...)`, so `stats_row.html:61`–`:62` drop their literal `$`
- `src/adw/dashboard/server.py`: add `build_templates() -> Jinja2Templates`. It creates `Jinja2Templates(directory=str(_TEMPLATE_DIR))` and registers `env.filters` `duration`, `tokens`, `relative_time`, `cost` and `filesize`. `create_dashboard_app` uses it at `:78`; since #212 it builds a plain `FastAPI()`.
- Templates:
  - `project_breakdown.html:26` and `analytics.html:215` `${{ "%.2f"|format(x) }}` → `{{ x|cost }}`
  - `cost_strip.html:16` `{{ bar.tokens }}` → `{{ bar.tokens|tokens }}`
  - `analytics.html:132` `{{ bar.total_tokens|default(0) }}` → `{{ bar.tokens|tokens }}`. The context key is `tokens` (`partials.py:318`), so the tooltip always said 0.
  - Leave the `{:,}` exact counts in `phase_detail.html:32`, `:38` (see PLAN.md Decisions).
- Docs: these feature docs name the deleted private helpers. Point each at `adw.format`, noting that `format_duration` takes seconds:
  - `docs/features/stat-cards-status-vocabulary.md:87`, plus its token-threshold note at `:85`, which moves to the new rules
  - `docs/features/recent-runs-project-breakdown.md:66`
  - `docs/features/run-detail-page-layout-metadata.md:24`
  - `docs/features/active-runs-phase-pipeline.md:16`
  - `docs/features/budget-section-breakdown-table.md:96`
  - `docs/features/analytics-time-range-stat-cards.md:92`
  - `docs/features/terminal-focus-view-modes.md:110`

  Check with `rg -n "_format_(duration|elapsed|tokens|cost|size|file_size|relative_time)|_relative_time" docs --glob '!docs/artifacts/**'`, which should print nothing.
- Tests:
  - `tests/unit/test_format.py` (new): one parametrized test per formatter, covering every example above plus `None`, 0, a negative, a sub-second value, the 59/60 s and 3599/3600 s boundaries, the 9,999 and 999,999 roll-overs, a naive `when`, a future `when` and GB.
  - `tests/unit/dashboard/test_templates.py` (new, or next to the existing template tests):
    - `test_build_templates_registers_the_format_filters` renders `{{ 1234.5|cost }} {{ 1500|tokens }} {{ 90|duration }} {{ 2048|filesize }}` through `build_templates().env` and gets `$1,234.50 1.5K 1m 30s 2.0 KB`.
    - `test_run_elapsed_renders_the_same_on_load_and_over_sse` covers a running run started 1 h 5 m 30 s ago. The run-detail context's elapsed and the SSE pipeline update's elapsed are the same string (`1h 5m`). Today they are `1h 5m` and `65m 30s`.
  - Delete the per-module formatter tests that now duplicate `test_format.py`:
    - `test_global_stats.py:214`–`:258` (`_format_tokens` / `_format_cost` / `_format_duration_ms`; keep `_format_rate`)
    - `test_list_running.py`'s `_format_elapsed` tests
    - `test_dry_run.py:293`–`:309`
    - `test_comments.py:333`–`:370`
    - `test_navigation.py:558`–`:604` (`_relative_time`)
    - `test_partials.py:763`–`:777`
    - `test_partials_active_runs.py:446`–`:472`
    - `test_run_detail.py:1562`–`:1580` and `:1615`–`:1633`
  - Update the output assertions that change, for example:
    - `65m 30s` → `1h 5m`
    - `progress` `10.5s` → `10s` and `N/A` → `—`
    - `45.7K` → `46K`
    - `just now` → `Ns ago` in `adw global list`

    Run the partial suite to find the rest.
  - `test_stat_cards.py:626`'s `_render_badge` builds a bare `Environment`. Switch it to `build_templates().env`, so macros see the app's filters.

## Acceptance

- [ ] `rg -n 'def _?(format_(duration|elapsed|tokens|cost|size|file_size|relative_time|duration_ms|duration_from_seconds)|relative_time)\b' src` lists exactly the five functions in `src/adw/format.py`.
- [ ] `rg -n ':,?\.2f\}' src` prints only `src/adw/format.py`'s `format_cost`, and `rg -n '"%\.2f"' src/adw/dashboard/templates` prints nothing.
- [ ] The docs `rg` above prints nothing.
- [ ] `test_format.py`, the filter test and the elapsed-consistency test pass.
- [ ] `uv run pytest tests/unit tests/integration -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failures (`ModuleNotFoundError: adw.format`; the elapsed test's `'1h 5m' != '65m 30s'`), then the GREEN tail, the two `rg` outputs and the preflight tail.

## Steps

### RED
- [ ] Write `tests/unit/test_format.py`, the filter test and the elapsed-consistency test; run them: they fail.

### GREEN
- [ ] Write `src/adw/format.py` and `build_templates()`.
- [ ] Switch every caller listed above and delete the private formatters and inline cost formatting; update the templates.
- [ ] Delete the duplicated formatter tests, update the changed assertions, and run the partial suite: green.

### REFACTOR
- [ ] Update the three feature docs; re-run the `rg` checks; `scripts/preflight.sh` passes.

## Notes

- Phase 2.11 will move the pipeline builders and the SSE code. This task only changes which formatter they call.
- `format_relative_time` takes `now` for tests. The dashboard and CLI callers pass nothing.
- Keep `_format_rate` and the percentage templates as they are: percentages are out of scope.
