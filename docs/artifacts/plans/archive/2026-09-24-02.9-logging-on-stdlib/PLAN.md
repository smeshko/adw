# Plan: Logging on stdlib with a redaction filter

Status: done
Branch: feature/adw-25
Risk: medium
Epic: 02 — Cleanup: remove inert features and consolidate ([epic](../../../epics/02-cleanup-remove-and-consolidate.md))
Phase: 2.9 — Logging on stdlib with a redaction filter
Linear: ADW-25
Created: 2026-09-24

## Goal

After this phase:

- Every log record goes through stdlib logging: the `adw` logger carries a Rich console handler and, during a run, one `live.log` handler. Both handlers share one redacting `logging.Filter`. `LogManager`, `LogManagerHandler`, the `Transport` protocol and the `LogEvent`/`LogContext`/`LogCategory`/`LogLevel` models are gone.
- `-v` shows DEBUG lines (B8), including on `adw -v run --dry-run "x"`.
- One writer owns `live.log` for the whole run. The executor's LLM text, tool-call lines and error lines go through that writer and its redaction filter. There is no per-line file lock and no `live.log.lock` file.
- `live.log` timestamps are UTC.

## Scope

- **Redaction filter.** `redactor.py` gains `RedactingFilter(logging.Filter)`. It rewrites a record's message and its exception text through a `Redactor`. `Redactor.redact_dict` and `_redact_list` are deleted with their tests; only tests call them (TASK-001).
- **New handlers and `setup_logging`.** `console.py` gains `ConsoleHandler(logging.Handler)`, which stops the spinner registered through `set_active_live` before it prints. `live_stream.py` gains `LiveStreamHandler(logging.FileHandler)`: it holds one lazily opened stream, writes UTC timestamps, and sends the LLM stream lines through `Handler.handle()` so the handler's filters apply to them. `logging/__init__.py` gains `setup_logging(verbosity, run_dir=None, *, console=None, redaction=None) -> LiveStreamHandler | None`, which replaces whatever handlers a previous call put on the `adw` logger. This task adds code only, with tests; nothing calls it yet (TASK-002).
- **Switch and delete.** `adw run` and `adw resume` call `setup_logging` instead of `create_log_manager`. `resume` also drops its `logging.basicConfig` call, which doubled every line at `-v`. `create_orchestrator` takes the `live_stream` that `setup_logging` returned instead of building a second writer from `run_id`. Then delete `logging/manager.py`, `logging/handler.py`, `ConsoleTransport`, `should_log`, `LiveStreamTransport`, `create_log_manager`, and everything in `models/logging.py` except `Verbosity`. Rewrite the tests that built logs through `LogManager`. Fix `docs/architecture/deep-dive/plan-phase.md`, which lists a `logs/logs.jsonl` and `raw.log` that runs never write (TASK-003).
- **`-v` on dry runs.** `adw run` attaches the console handler right after it loads the config, so the input resolution and dry-run path log through it. The resolver's three "input treated as …" lines drop from INFO to DEBUG, so a normal run prints nothing new (TASK-004).

## Out of Scope

- **`adw run -v …` as an alternative spelling.** `-v`, `-q` and `--trace` are options of the root command, so the flag goes before the subcommand: `adw -v run --dry-run "x"`. `adw run -v` has always failed with "No such option: -v", and adding per-command copies of the flags runs against phase 2.12 (thin the CLI). The epic's criterion is checked with the root-level flag (see Decisions).
- **A `live.log` for resumed runs.** `adw resume` writes no `live.log` today (`create_orchestrator(console)` gets no run id), and it stays console-only here. Giving it the resumed run's `live.log` is a behaviour change for the run-loop work in Epic 03.
- **Console logging for commands other than `run` and `resume`.** They configure no handler today, so their warnings reach stderr through stdlib's last-resort handler. Attaching the console handler globally would start printing their INFO lines, and every command's output would change.
- **The `live.log` line grammar that readers depend on.** The dashboard (`_load_log_entries`, `terminal_logs`) and `adw logs follow` (`LogRenderer`) parse `[YYYY-MM-DD HH:MM:SS] [TAG] message`. That shape, the `WARN`/`FATAL` tags, the `[LLM] ▶`/`◀` markers and the `[TOOL]` lines stay as they are. Only the `[category]` tag after the level goes, together with `LogCategory`.
- **`Redactor.redact_env_dict`, `get_redactor` and `configure_redactor`.** `hooks/runner.py` uses them.
- **The two tests in `tests/integration/cli/test_run_integration.py::TestVerbosityIntegration`.** They re-implement a `show_llm_output` expression inside the test and exercise no product code. Deleting them is test-suite cleanup for another phase.

## Research Summary

See [RESEARCH.md](./RESEARCH.md). In short:

- **The layers.** A record from `logging.getLogger(__name__)` goes: root handler `LogManagerHandler` → `LogManager._log` → `ConsoleTransport` and `LiveStreamTransport`. The handler guesses a `LogCategory` from the logger name just to print a tag, and drops `extra={}` apart from `phase`/`run_id`. Nothing in `src` calls `LogManager.info/warn/child/set_*` directly.
- **B8.** At `-v`, `create_log_manager` sets the root handler to DEBUG, but `LogManager(level=INFO)` is never lowered, so `_should_log` drops every DEBUG record. On top of that, `adw run --dry-run` returns before `create_log_manager` runs at all, so a dry run has no handler.
- **Two writers.** `create_log_manager` builds one `LiveStreamTransport(run_dir/live.log)` for records, and `create_orchestrator` builds a second for the executor's LLM stream. That is why every line takes a `FileLock` and leaves a `live.log.lock` behind.
- **Redaction gaps.** `LogManager._log` redacts record messages. `write_llm_token`, `write_tool_call` and `write_error` write straight to the file, so a secret in Claude's output or in a Bash tool call lands in `live.log` as is.
- **Mixed clocks.** Record lines use `LogEvent.timestamp` (UTC). The LLM markers, tool calls and errors use `datetime.now()` (local time).
- **Readers.** Three parsers read `live.log`: the dashboard's `_load_log_entries` and `terminal_logs`, and `LogRenderer`. All three key on `^\[ts\] \[TAG\] …`. The dashboard maps `ERROR`/`FATAL` to error and `WARN`/`WARNING` to warn.
- **Baseline.** `uv run pytest` on `7b61e72a`: 2982 passed, 5 skipped, coverage 84.77% (gate 80%).

## Decisions

- **The redacting filter is attached to each handler, not to the `adw` logger.** Stdlib consults a logger's filters only for records logged on that logger itself, not for records that propagate up from `adw.core.orchestrator` and the like. Handler filters see every record the handler emits. The filter is idempotent (`[REDACTED]` matches no default pattern), so running it once per handler is safe.
- **The LLM stream goes through `Handler.handle()`.** `write_llm_start/token/end`, `write_tool_call` and `write_error` build their line and pass it to `handle()` as a record marked `raw`. `handle()` applies the handler's filters, takes the handler's lock and calls `emit`, and `format` returns a raw record's text without a prefix. So the redaction filter covers the LLM stream by construction, and records and tokens share one lock and one stream. The alternative, giving the handler its own `Redactor` for direct writes, would be a second redaction path to keep in step with the filter.
- **`LiveStreamHandler` subclasses `logging.FileHandler` with `delay=True`.** It opens `live.log` once, on the first write, appends, and flushes after every line, which is what `logs follow` and the dashboard tail need. It overrides `_open` to create the run directory first, as `_write_line` does today. `delay=True` means a run that logs nothing creates no file.
- **Level names stay `DEBUG`/`INFO`/`WARN`/`ERROR`/`FATAL`.** Both handlers map stdlib's `WARNING` to `WARN` and `CRITICAL` to `FATAL`. The dashboard treats a `CRITICAL` tag as INFO, and `LogRenderer` colours only `WARN`. Keeping the tags keeps `live.log` readable by the current parsers, and by the runs already on disk.
- **Verbosity maps to handler levels.** Console: QUIET→ERROR, NORMAL→INFO, VERBOSE→DEBUG, TRACE→DEBUG (stdlib has no TRACE). `live.log`: INFO, or DEBUG at VERBOSE/TRACE. `-q` quiets the console only, never the run's record. `live.log` stays at INFO on a normal run because the dashboard shows it and `src` has 87 `logger.debug` calls. The `adw` logger's own level is the lowest handler level, so DEBUG records aren't built on a normal run. The `Verbosity` docstring is updated to say this.
- **The `adw` logger, not root.** Handlers go on `logging.getLogger("adw")`, which every `src` module logs under. Third-party loggers such as httpx no longer reach ADW's console, so the `httpx`/`httpcore` WARNING overrides go too. `propagate` stays `True`, so pytest's `caplog`, which hooks the root logger, still sees ADW's records. In production root has no handlers, so nothing prints twice.
- **`setup_logging` is idempotent.** Each call removes and closes the handlers already on the `adw` logger, then attaches new ones. `adw run` calls it twice: console-only right after loading the config, then with the run directory right before building the orchestrator, where `create_log_manager` runs today. A single early call with the run directory would create `.adw/runs/<id>/live.log` for invocations that fail during input resolution, such as `--task-id` with a bad id at `-v`. A root `tests/conftest.py` autouse fixture removes and closes the `adw` handlers after each test, so a CLI test's handler never outlives it.
- **`setup_logging` returns the live handler, and `create_orchestrator(…, live_stream=…)` takes it.** `create_orchestrator`'s `run_id` parameter existed only to build the second writer, so it goes. Passing the handler explicitly keeps "one writer" checkable: a test asserts that the executor's `live_stream` is the handler on the `adw` logger.
- **`create_redactor_from_config` stays** in `logging/__init__.py`. `setup_logging` calls it, and `test_package.py` keeps testing it. `setup_logging` builds its handlers first and the redactor second, so the "redaction is DISABLED" warning reaches the new console handler instead of stdlib's last-resort handler.
- **The epic's `adw run -v --dry-run "x"` is checked as `adw -v run --dry-run "x"`.** The flag belongs to the root command, as Out of Scope explains. The final-validation task ticks the epic's criterion and adds a sub-bullet recording the spelling, the way epic 02 annotates the `cli/dashboard.py` criterion.
- **Console lines lose the `[category]` tag and use UTC `HH:MM:SS`.** The tag came from `LogCategory`'s logger-name guess. The old console already printed `LogEvent.timestamp`, which is UTC. The audit flagged "console formatting changes slightly" as the accepted risk.
- **Record context in `live.log` is kept.** A record with `extra={"phase": …}` (27 call sites) or `run_id` is written `[ts] [INFO] {phase=build} message`, as the old transport wrote it minus the category. The dashboard's phase filter matches `\bbuild\b` in that text.
- **Task order keeps every commit green.** TASK-002 adds the new handlers alongside the old transports. TASK-003 switches the callers and deletes the old code in one commit, because `LogManager` can't drive a `logging.Handler`. TASK-004 then moves the console attach earlier, which is the change the `-v` dry-run criterion needs.

## Risks

- **An import cycle once `adw.logging` imports `adw.core.constants`.** `adw.core` → `phase_runner` → `hooks.runner` → `adw.logging.redactor` already runs `adw/logging/__init__.py`. Mitigation: `constants.py` imports nothing from `adw`, so importing it from a partly initialized `adw.core` works. TASK-002 runs `python -c "import adw.logging"` and `python -c "import adw.core"` in fresh interpreters. If either fails, `setup_logging` imports `LIVE_LOG` inside the function.
- **The console handler prints to a stream a finished `CliRunner` has closed.** The old code bound a new `Console` to `console.file` at setup and leaked it on the root logger. Mitigation: `ConsoleHandler` prints through the `Console` it is given; app.py's module-level console resolves `sys.stdout` at print time. The conftest fixture removes the handlers after every test.
- **Output changes a user notices.** Mitigation: the only change on a normal run is the dropped `[category]` tag, and console times were already UTC. The resolver lines move to DEBUG before the console attaches earlier (TASK-004). `live.log` keeps its line grammar, checked by the existing dashboard and `logs follow` parser tests, which stay unchanged.
- **Parallel epic-02 phases touch `bootstrap.py` and `app.py`** (2.7 paths, 2.8 config loading, 2.12 CLI). Mitigation: fetch and rebase before marking the PR ready. `create_log_manager` and its callers are the only lines this phase changes there.

## Acceptance Criteria

- [x] `adw -v run --dry-run "x"` prints DEBUG lines (B8). Evidence: `test_verbose_dry_run_prints_debug_lines`, RED then GREEN, and a scratch-repo transcript run with this worktree's `.venv/bin/adw`.
- [x] A value matching a redaction pattern in mocked LLM output shows up as `[REDACTED]` in `live.log`. Evidence: `test_llm_output_secrets_are_redacted_in_live_log` (RED then GREEN): `ClaudeCodeExecutor` on a mocked subprocess whose text and Bash tool call carry an `sk-ant-…` key and a `ghp_…` token. Plus a `live.log` excerpt from a scratch-repo `adw run --phase plan --no-worktree` whose `llm.path` points at a fake `claude` script that prints a planted secret.
- [x] Exactly one writer holds `live.log` during a run, and the per-line file lock is gone. Evidence: `test_run_hands_the_one_live_log_handler_to_the_orchestrator` and `test_executor_writes_through_the_given_live_stream`, RED then GREEN. `grep -rn "FileLock\|filelock" src/adw/logging` prints nothing. `ls` of the scratch run's directory shows `live.log` and no `live.log.lock`.
- [x] `src/adw/logging/` contains only `__init__.py` (holding `setup_logging`), `redactor.py`, `console.py` and `live_stream.py`. Evidence: `ls src/adw/logging`, and `grep -rn -I --exclude-dir=__pycache__ "LogManager\|LogManagerHandler\|LogEvent\|LogContext\|LogCategory\|LogLevel\|ConsoleTransport\|LiveStreamTransport\|create_log_manager\|StructuredFileTransport\|logs\.jsonl\|redact_dict" src tests docs/architecture` prints nothing.
- [x] `live.log` timestamps are UTC. Evidence: `test_live_log_timestamps_are_utc` (RED then GREEN), which pins the clock and compares a record line and an LLM marker line against UTC.
- [x] Lint and tests pass. Evidence: `scripts/preflight.sh` and the tail of `uv run pytest`, coverage ≥ 80%.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Add a redacting logging filter and drop the test-only dict redaction
- [x] TASK-002: Add setup_logging with a Rich console handler and one live.log handler (depends on TASK-001)
- [x] TASK-003: Route run, resume and the executor through setup_logging and delete LogManager (depends on TASK-002)
- [x] TASK-004: Show DEBUG lines for adw -v run --dry-run (depends on TASK-003)
- [x] TASK-005: Final Validation
