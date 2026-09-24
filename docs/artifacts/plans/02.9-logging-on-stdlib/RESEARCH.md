# Research: Logging on stdlib with a redaction filter

Curated findings only — no raw conversation transcripts.

## Key Files & Directories

- `src/adw/logging/__init__.py` (61 lines): re-exports `LogManager` and `LogManagerHandler`. Defines `create_redactor_from_config(enabled, patterns, disable_defaults)`, which warns and returns `None` when redaction is disabled, and otherwise calls `configure_redactor`, which also sets the module-level default redactor that `hooks/runner.py` reads.
- `src/adw/logging/manager.py` (285): the `Transport` protocol and `LogManager`. `_log` drops records below `self._level`, redacts the message, builds a `LogEvent` and calls each transport's `write`. Its `level` defaults to INFO and nothing in `src` lowers it: this is B8. Its docstring registers a `StructuredFileTransport(Path("logs.jsonl"))`, which doesn't exist.
- `src/adw/logging/handler.py` (137): `LogManagerHandler(logging.Handler)` maps the stdlib level to `LogLevel` and guesses a `LogCategory` from the logger name (`executor`/`llm` → LLM, `hook` → HOOK, and so on). It keeps only `phase`/`run_id` from `extra`, and calls `LogManager._log`, a private method. Its docstring promises `logs.jsonl`.
- `src/adw/logging/console.py` (241): `set_active_live`/`get_active_live` (a module-level `Live` reference that `cli/progress.py` sets while the spinner runs), `LEVEL_STYLES`, `should_log`, and `ConsoleTransport`. `ConsoleTransport` stops the active `Live` before printing, then prints `HH:MM:SS [LEVEL] [category] message`. It has a Rich path and a plain path for non-TTY output.
- `src/adw/logging/live_stream.py` (299): `LiveStreamTransport`. `write(event)` formats `[ts] [LEVEL] [CATEGORY] {run=…, phase=…} message` from the event's UTC timestamp. `write_llm_start/token/end`, `write_tool_call` and `write_error` use `datetime.now()`, which is local time. `_write_line` does `mkdir`, then `FileLock(live.log.lock)`, then opens, appends and flushes, once per line. `close()` removes the lock file.
- `src/adw/logging/redactor.py` (318): `Redactor.redact`, `should_redact_env`, `redact_env_dict` (used by `hooks/runner.py`), `redact_dict`/`_redact_list` (only `tests/unit/logging/test_redactor.py::TestRedactDict` calls them), and `get_redactor`/`reset_redactor`/`configure_redactor`.
- `src/adw/models/logging.py` (218): `LogLevel`, `Verbosity`, `VERBOSITY_LEVEL_MAP`, `LEVEL_ORDER`, `LogCategory`, `LogContext`, `LogEvent`. Outside the logging package, `src` uses only `Verbosity` (`cli/app.py`, `cli/resume.py`) and `VERBOSITY_LEVEL_MAP`/`LogLevel` (`cli/bootstrap.py`). `models/__init__.py` re-exports `LogCategory`, `LogContext`, `LogEvent` and `LogLevel`; no `src` module imports them from there.
- `src/adw/cli/bootstrap.py`: `create_log_manager(console, verbosity, run_dir, redaction_config)` builds the redactor, `LogManager`, `ConsoleTransport(file=console.file, force_tty=console.is_terminal)` and, given `run_dir`, a `LiveStreamTransport`. It adds a `LogManagerHandler` to the **root** logger, sets the root level to DEBUG, and quiets `httpx`/`httpcore`. `create_orchestrator(…, run_id=…)` builds a **second** `LiveStreamTransport(runs_dir/run_id/live.log)` for `ClaudeCodeExecutor(live_stream=…)`. In mock mode (`ADW_MOCK_EXECUTOR`) the executor is `MockExecutor`, which takes no live stream.
- `src/adw/cli/app.py` `run()`: loads the config (and `config.logging.redaction`), resolves the input through `InputResolver`, shows the header, and **returns on `--dry-run` before `create_log_manager`**. For a real run it calls `create_log_manager(console, verbosity, run_dir, redaction_config)`, then `create_orchestrator(console, run_id=run_id, …)`. `-v`/`-q`/`--trace` are options on the root callback `main()`, stored in `ctx.obj["verbosity"]`.
- `src/adw/cli/resume.py`: at VERBOSE/TRACE it calls `logging.basicConfig(level=DEBUG)`, which puts a root `StreamHandler` next to the `LogManagerHandler` that `create_log_manager(console, verbosity)` adds later. It passes no `run_dir`, and calls `create_orchestrator(console)` with no `run_id`, so a resume writes no `live.log`.
- `src/adw/executors/claude_code.py`: `execute` writes `write_llm_start(phase)` and `write_llm_end(tokens, ms)`. `read_stdout` writes `write_llm_token(display_text)` and `write_tool_call(name, context)` per stream-json line. A non-zero exit writes `write_error(message)`.
- `src/adw/task_managers/resolver.py`: `InputResolver.resolve` logs "Input treated as feature (--no-task-manager)", "Input resolved as task ID" and "Input treated as feature string" at INFO. The console handler isn't attached yet at that point, so the lines never print today.
- `live.log` readers:
  - `dashboard/routes.py::_load_log_entries` and `dashboard/partials.py::terminal_logs` use `^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+\[(\w+)\]\s+(.*)` after stripping ANSI. `{ERROR, FATAL}` map to error, `{WARN, WARNING}` to warn, anything else to INFO.
  - `cli/logs.py::_parse_log_line`/`LogRenderer` (`adw logs follow`) use the same leading shape. They also accept `[ts] [LEVEL] [COMPONENT] …` and treat unstructured lines as LLM text.
- Tests that build logs through the old API:
  - `tests/unit/logging/test_manager.py`, `test_handler.py`, `test_console.py` and `tests/unit/models/test_logging.py`
  - `tests/integration/cli/test_logs_integration.py` (all three tests use `create_log_manager` and `LogCategory`)
  - `tests/unit/dashboard/test_log_viewer.py::test_reads_log_written_by_run`
  - `tests/unit/cli/test_logs.py`: the export test writes a `logs.jsonl` from `LogEvent`s. The export only tars the run directory, so any file serves.
  - `tests/unit/executors/test_claude_code.py::test_outputs_to_live_stream_when_configured` (`LiveStreamTransport`)
- `docs/architecture/deep-dive/plan-phase.md` "Output Directory Structure" lists `logs/logs.jsonl` and `logs/raw.log`. Runs write `live.log` at the run directory's root (B4).

## Architecture Facts

- Every `src` logger is `logging.getLogger(__name__)` under `adw.*`. No `src` module names another logger except `bootstrap.py`'s `httpx`/`httpcore` overrides.
- `src` has 87 `logger.debug`, 44 `logger.info` and no `logger.critical` calls. 27 calls pass `extra={"phase": …}`.
- Stdlib consults a logger's filters only for records created on that logger, not for records propagated from child loggers. Handler filters run for every record the handler receives.
- `logging.Handler.handle(record)` runs the filters, then `emit` under `self.lock` (an `RLock`). It does not check the handler's level; `Logger.callHandlers` does that. `FileHandler(delay=True)` opens the stream on the first `emit`, and `StreamHandler.emit` flushes after each record.
- Rich's `Console()` with no `file` resolves `sys.stdout` when it prints, so under `CliRunner` it writes into the captured output. app.py's module-level `console = Console()` is one of these.
- `filelock` stays a dependency: `core/context_manager.py` and `core/run_directory.py` use it.
- Only `cli/progress.py` calls `set_active_live`. It registers the spinner's `Live` in `on_llm_start` and clears it on completion.

## Constraints

- `live.log` must keep `[YYYY-MM-DD HH:MM:SS] [TAG] message`, the `WARN`/`FATAL` tags, the `[LLM] ▶ Token stream begins (phase)` / `[LLM] ◀ Token stream ends (…)` markers and `[TOOL] name: context`, so the three parsers above keep working. `write_llm_end` starts with a newline, which closes an unterminated token stream.
- Tests reach `~/.adw` only through the per-test `HOME` (`isolated_home`). CLI tests under `tests/unit/cli/` run inside `tmp_path` (`isolated_cwd`).
- mypy `--strict` covers `src/adw` only. ruff covers `src/` and `tests/`.

## Useful Commands

```bash
# Reproduce B8 and the -v placement (scratch dir, this worktree's binary)
cd "$(mktemp -d)" && git init -q
ADW_MOCK_EXECUTOR=1 <worktree>/.venv/bin/adw run -v --dry-run "x"   # "No such option: -v"
ADW_MOCK_EXECUTOR=1 <worktree>/.venv/bin/adw -v run --dry-run "x"   # no DEBUG lines today

# Import-cycle check after TASK-002
.venv/bin/python -c "import adw.logging" && .venv/bin/python -c "import adw.core"

# Partial run for the logging tests
uv run pytest tests/unit/logging tests/unit/cli tests/integration/cli -o addopts=""
```

## Uncertainty

- **Where `setup_logging` lives.** The epic says the package holds `redactor.py`, `console.py`, `live_stream.py` "and the setup function". Resolved: `setup_logging` lives in `logging/__init__.py`, so the package has exactly those three modules plus `__init__.py`.
- **`adw run -v`.** The epic's criterion writes the flag after `run`, which Typer rejects. Resolved: the root-level `adw -v run …` is the supported spelling (PLAN.md, Decisions).
- **Whether `live.log` should always record DEBUG.** `Verbosity`'s docstring says "file logs always capture everything", but the old handler level followed the verbosity for both outputs. Resolved: `live.log` records INFO, or DEBUG at `-v`/`--trace`. The docstring changes to match.

## References

- Epic 02, phase 2.9: `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`
- Simplification audit, item #7 and bug B8 (private artifact linked from the epic)
- `docs/features/llm-interaction-log-viewer.md`: the dashboard's `live.log` parsing
