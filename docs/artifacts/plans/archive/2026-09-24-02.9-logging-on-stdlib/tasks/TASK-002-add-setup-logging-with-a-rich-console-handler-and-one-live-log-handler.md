# TASK-002: Add setup_logging with a Rich console handler and one live.log handler

Depends on: TASK-001
Suggested commit: `feat(logging): add setup_logging with stdlib console and live.log handlers`

## Goal

`setup_logging(verbosity, run_dir)` attaches a spinner-aware Rich console handler and one redacted, UTC-stamped `live.log` handler to the `adw` logger. It is added alongside the old transports; nothing calls it yet.

## Files

- `src/adw/logging/console.py`: add, next to `ConsoleTransport` (TASK-003 deletes that):
  - `_LEVEL_STYLES: dict[int, tuple[str, str]]`, mapping DEBUG, INFO, WARNING, ERROR and CRITICAL to `(tag, style)`:
    - `DEBUG`: `dim cyan`
    - `INFO`: `green`
    - `WARN`: `yellow`
    - `ERROR`: `bold red`
    - `FATAL`: `bold white on red`
  - `class ConsoleHandler(logging.Handler)`, built as `ConsoleHandler(console: Console)`. `emit(record)`:
    1. if `get_active_live()` returns a `Live`, call `live.stop()` and `set_active_live(None)`, as `ConsoleTransport.write` does
    2. build a `rich.text.Text`: UTC `HH:MM:SS ` from `record.created` (style `dim`), then `[TAG] ` (the level style), then `self.format(record)`, styled with the level style at ERROR and above
    3. `self.console.print(text)`
    4. wrap the body in `try/except Exception: self.handleError(record)`

    A `Text` is never parsed for markup or highlighted, and a non-terminal `Console` drops the styles, so one path serves TTY and piped output.
- `src/adw/logging/live_stream.py`: add, next to `LiveStreamTransport`:
  - `_LEVEL_TAGS: dict[int, tuple[str, str]]`, mapping each level to `(tag, colour)`: DEBUG `dim`, INFO `green`, WARNING → `WARN` `yellow`, ERROR `red`, CRITICAL → `FATAL` `bold_red`
  - `_utc_stamp(created: float) -> str`, returning `datetime.fromtimestamp(created, UTC).strftime("%Y-%m-%d %H:%M:%S")`
  - `class LiveStreamHandler(logging.FileHandler)`, built as `LiveStreamHandler(path: Path)` → `super().__init__(path, mode="a", encoding="utf-8", delay=True)`:
    - `_open()`: `Path(self.baseFilename).parent.mkdir(parents=True, exist_ok=True)`, then `super()._open()`
    - `format(record)`:
      - `text = super().format(record)`, which includes a traceback when there is one
      - if `getattr(record, "raw", False)`, return `text`
      - otherwise return `[<utc stamp>] <coloured [TAG]><context> <text>`. The context is ` {run=<first 8 chars> phase=<phase>}` (dim) from `record.run_id`/`record.phase` when present.
    - `_write_raw(line: str, levelno: int = logging.INFO)`: `self.handle(logging.makeLogRecord({"msg": line, "levelno": levelno, "levelname": logging.getLevelName(levelno), "raw": True}))`. `handle` runs the handler's filters (redaction), takes `self.lock` and emits.
    - `write_llm_start(phase=None)`, `write_llm_token(content)`, `write_llm_end(token_count=0, duration_ms=0)`, `write_tool_call(tool_name, context=None)`, `write_error(message)`:
      - the same lines as `LiveStreamTransport`'s, but stamped `_utc_stamp(time.time())`
      - each goes through `_write_raw`; `write_error` uses `logging.ERROR`
      - `write_llm_end` keeps its leading `\n`
    - the ANSI helper: reuse `COLORS` and make `_colorize` a module-level function, so both classes can use it until TASK-003
- `src/adw/logging/__init__.py`: add
  - `_CONSOLE_LEVELS: dict[Verbosity, int]`: QUIET→ERROR, NORMAL→INFO, VERBOSE→DEBUG, TRACE→DEBUG
  - `setup_logging(verbosity: Verbosity, run_dir: Path | None = None, *, console: Console | None = None, redaction: RedactionConfig | None = None) -> LiveStreamHandler | None` (`RedactionConfig` under `TYPE_CHECKING`):
    1. `logger = logging.getLogger("adw")`; for each handler on it, `removeHandler` then `close()`
    2. `ConsoleHandler(console or Console())` at `_CONSOLE_LEVELS[verbosity]`
    3. if `run_dir` is given, `LiveStreamHandler(run_dir / LIVE_LOG)` at DEBUG for VERBOSE/TRACE, INFO otherwise
    4. add the handlers to the logger, and set the logger level to the lowest handler level
    5. `redactor = create_redactor_from_config(...)` from `redaction` (defaults when `None`), called **after** the handlers are attached so its "DISABLED" warning prints through them
    6. if `redactor` is not `None`, `addFilter(RedactingFilter(redactor))` on each handler
    7. return the live handler or `None`
  - update the package docstring: stdlib logging, one filter, `setup_logging`. Drop "File locking" and "Category-based organization".
  - import `LIVE_LOG` from `adw.core.constants` at module level; see the Notes for the cycle check
- `src/adw/models/logging.py`: the `Verbosity` docstring says verbosity sets the console level, and `live.log` records INFO, or DEBUG at VERBOSE/TRACE.
- `tests/conftest.py`: add an autouse fixture `_reset_adw_logging` that, after the test, removes and closes every handler on `logging.getLogger("adw")` and resets its level to `NOTSET`.
- `tests/unit/logging/test_setup.py` (new):
  - `test_verbose_console_shows_debug`: `setup_logging(Verbosity.VERBOSE, console=Console(file=buf))`; `logging.getLogger("adw.x").debug("dbg")` → `[DEBUG] dbg` in `buf`. At `NORMAL` the same call prints nothing. This is B8 at the unit level.
  - `test_quiet_console_shows_only_errors`: QUIET → a warning is absent, an error is present
  - `test_live_log_level_follows_verbosity`: parametrized over the four verbosities with `run_dir`. A debug and an info record: the info line is always in `live.log`, and the debug line only at VERBOSE and TRACE. QUIET still writes the info line.
  - `test_redacts_records_on_console_and_live_log`: with `run_dir`, `logger.warning("key %s", "sk-" + "a"*24)` → `[REDACTED]` in the console buffer and in `live.log`, with no `sk-aaaa` in either
  - `test_llm_stream_is_redacted`: the returned handler's `write_llm_token("token=abcdefgh1234")`, `write_tool_call("Bash", "curl -H 'Authorization: Bearer abc.def'")` and `write_error("password=hunter22")` → none of the three secrets appear in `live.log`, and `[REDACTED]` appears three times
  - `test_live_log_timestamps_are_utc`:
    - set `TZ=America/New_York` with `monkeypatch.setenv` and call `time.tzset()`, then call it again on teardown. Local time now differs from UTC even on a CI box that runs in UTC.
    - pass the handler a record built with `logging.makeLogRecord({..., "created": epoch})`
    - patch `adw.logging.live_stream.time.time` to return the same `epoch` and call `write_llm_start("plan")`
    - assert that both lines' `[YYYY-MM-DD HH:MM:SS]` equal `datetime.fromtimestamp(epoch, UTC)`
  - `test_record_lines_keep_the_parsed_shape`: a record with `extra={"phase": "build"}` and one at WARNING. Assert `_load_log_entries` (dashboard) returns both, with levels `INFO` and `WARN`, the first message containing `build`. Assert `cli.logs._parse_log_line` parses both.
  - `test_second_call_replaces_handlers`: two calls with the same `run_dir` → the `adw` logger holds exactly one `ConsoleHandler` and one `LiveStreamHandler`, and the first call's live handler is closed (`stream is None`)
  - `test_disabled_redaction_warns_and_passes_secrets`: `RedactionConfig(enabled=False)` → the console shows the "DISABLED" warning and a secret passes to `live.log` unchanged
  - `test_live_log_needs_no_lock_file`: after a record and an LLM token, the run dir holds only `live.log`
  - `test_console_handler_stops_active_spinner`: `set_active_live(mock_live)`; a record → `mock_live.stop` called once and `get_active_live()` is `None`

## Acceptance

- [ ] At VERBOSE the console handler prints DEBUG records; at NORMAL it doesn't.
- [ ] Records and the LLM text, tool-call and error lines reach `live.log` redacted.
- [ ] Record lines and LLM marker lines in `live.log` carry the same UTC time.
- [ ] Record lines still parse with the dashboard's and `logs follow`'s parsers, with `WARN` as the warning tag.
- [ ] Calling `setup_logging` twice leaves one handler of each kind and closes the old ones; no `live.log.lock` is created.
- [ ] `python -c "import adw.logging"` and `python -c "import adw.core"` both succeed in fresh interpreters.
- [ ] `uv run pytest tests/unit/logging -o addopts=""` and `scripts/preflight.sh` pass.

Evidence: the RED run (`test_setup.py` fails on `ImportError: cannot import name 'setup_logging'`), the GREEN pytest tail, the two import commands' exit codes, and the preflight tail.

## Steps

### RED
- [ ] Add the conftest fixture and `tests/unit/logging/test_setup.py`. Run it: every test fails on the import.

### GREEN
- [ ] Add `ConsoleHandler`, `LiveStreamHandler`, `setup_logging`, and the docstring updates. Run `tests/unit/logging`: green.
- [ ] Run the two fresh-interpreter import checks.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- **Import cycle.** `adw.core/__init__` → `orchestrator` → `phase_runner` → `hooks.runner` → `adw.logging.redactor` executes `adw/logging/__init__.py` while `adw.core` is still initializing. `adw.core.constants` imports nothing from `adw`, so importing it from there works. If either fresh-interpreter import fails anyway, move the `LIVE_LOG` import into `setup_logging`.
- `FileHandler._open` is typed in typeshed (`def _open(self) -> TextIOWrapper`), so the override passes mypy `--strict` without an ignore.
- A raw line carries its own stamp from `_utc_stamp(time.time())`, which is why the UTC test patches `adw.logging.live_stream.time.time`. A normal record's stamp comes from `record.created`.
- `write_llm_token` may be called with multi-line text. `StreamHandler.emit` appends one `\n`, as `_write_line` did.
