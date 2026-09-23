# TASK-005: Close both SSE streams on every terminal status

Depends on: TASK-001
Suggested commit: `fix(dashboard): close sse streams for interrupted runs`

## Goal

`run_events_sse` and `log_stream_sse` share one terminal-status set that includes `interrupted`, so neither stream polls forever for an interrupted run (B21).

## Files

- `src/adw/core/constants.py`: `TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed", "aborted", "interrupted"})`, placed next to the path constants from TASK-001.
- `src/adw/dashboard/routes.py`:
  - `run_events_sse` (~1421) tests `current_status in TERMINAL_STATUSES`. `completed` still emits `run-complete`, and every other terminal status emits `run-failed`.
  - `log_stream_sse` (~1557) tests `ctx.status in TERMINAL_STATUSES`.
- `tests/unit/dashboard/test_active_failed_runs.py`: add `test_run_events_close_on_interrupted` and `test_log_stream_closes_on_interrupted`.

## Acceptance

- [ ] `test_run_events_close_on_interrupted`: `run_events_sse` for a run whose context has `status="interrupted"` yields a `run-failed` event and ends within 2 s.
- [ ] `test_log_stream_closes_on_interrupted`: `log_stream_sse` for an interrupted run, with a `live.log` holding one line, yields that `log-line` and ends within 2 s.
- [ ] `grep -c 'in TERMINAL_STATUSES' src/adw/dashboard/routes.py` prints `2`.
- [ ] `uv run pytest tests/unit/dashboard -o addopts=""` passes.

Evidence:
- the RED run: both tests fail with `TimeoutError` after about 2 s on today's code
- the GREEN run: both pass in well under 1 s

## Steps

### RED
- [ ] Write both tests as `async def`; `asyncio_mode = "auto"`.
  - Patch `adw.dashboard.routes.ContextManager` so `load()` returns a `MagicMock` with `status="interrupted"`, `current_phase="build"`, `phase_history=["plan"]` and `started_at=datetime.now(UTC)`.
  - Patch `adw.dashboard.routes.asyncio.sleep` with an `AsyncMock`, so a non-terminating loop spins instead of sleeping.
  - `resp = await run_events_sse(run_id, index_manager=_mock_index_manager(entries=[entry]))`. For the log test, call `log_stream_sse`, with the entry's `project_path` at `tmp_path` and a `live.log` there.
  - Drain `resp.body_iterator` into a list inside `asyncio.wait_for(…, timeout=2)`. Assert on the event names.
- [ ] Run them and confirm that both raise `TimeoutError`.

### GREEN
- [ ] Add `TERMINAL_STATUSES`, and use it in both loops.
- [ ] Run the tests and confirm they are green.

### REFACTOR
- [ ] Reuse `_make_index_entry`/`_mock_index_manager` from the test module for the index mock, rather than a new helper.
- [ ] `scripts/preflight.sh` passes.

## Notes

- `index_manager` is a `Depends` default. Pass it explicitly when you call the route function directly.
- A spinning loop with a patched sleep burns CPU until `wait_for` cancels it. The cancellation reaches the generator at its next `await asyncio.sleep`, which is the patched `AsyncMock` that yields control, so the timeout fires reliably.
