# TASK-003: Route run, resume and the executor through setup_logging and delete LogManager

Depends on: TASK-002
Suggested commit: `refactor(logging): route runs through setup_logging and delete LogManager`

## Goal

`adw run` and `adw resume` log through `setup_logging`, the executor writes the LLM stream through the same `live.log` handler, and `LogManager`, its handler, the transports and the logging models other than `Verbosity` are deleted.

## Files

- `src/adw/cli/bootstrap.py`:
  - delete `create_log_manager`
  - delete the imports that only it used: `logging`, `TextIO`/`cast`, `LIVE_LOG`, `LogManager`, `LogManagerHandler`, `create_redactor_from_config`, `ConsoleTransport`, `LiveStreamTransport`, `RedactionConfig`, `VERBOSITY_LEVEL_MAP`, `LogLevel`, `Verbosity`
  - `create_orchestrator`: replace `run_id: str | None = None` with `live_stream: LiveStreamHandler | None = None` and pass it to `ClaudeCodeExecutor(config=llm_config, live_stream=live_stream)`. Delete the block that built a second `LiveStreamTransport`. In the docstring, `run_id` becomes `live_stream`: "the run's `live.log` handler from `setup_logging`; the executor writes the LLM stream through it".
- `src/adw/cli/app.py` `run()`:
  - replace `create_log_manager(console, verbosity=…, run_dir=…, redaction_config=…)` with `live_stream = setup_logging(verbosity, run_dir, console=console, redaction=redaction_config)`, in the same place, before the orchestrator is built
  - pass `live_stream=live_stream` to `create_orchestrator` instead of `run_id=run_id`
  - update the comment above the call: "Attach the console and the run's live.log handler to the `adw` logger. The executor writes the LLM stream through the same handler."
  - the import becomes `from adw.cli.bootstrap import create_orchestrator` plus `from adw.logging import setup_logging`
- `src/adw/cli/resume.py`:
  - replace the `if verbosity in (VERBOSE, TRACE): logging.basicConfig(...)` block with `setup_logging(verbosity, console=console)` right after `verbosity` is read, and delete the `logger.debug("Verbose mode enabled")` that went with it
  - delete the later `log_manager = create_log_manager(...)` and `_ = log_manager` lines
  - drop the `create_log_manager` import, and `import logging` if nothing else uses it (`logger = logging.getLogger(__name__)` stays)
- `src/adw/executors/claude_code.py`:
  - the `TYPE_CHECKING` import becomes `from adw.logging.live_stream import LiveStreamHandler`
  - `live_stream: "LiveStreamHandler | None"`
  - the docstrings say "live.log handler" instead of "transport"
- `src/adw/logging/__init__.py`: drop the `LogManager`/`LogManagerHandler` imports; `__all__ = ["create_redactor_from_config", "setup_logging"]`.
- Delete `src/adw/logging/manager.py` and `src/adw/logging/handler.py`.
- `src/adw/logging/console.py`:
  - delete `ConsoleTransport`, `should_log`, the old `LEVEL_STYLES`, and the `adw.models.logging` import
  - the module docstring describes `ConsoleHandler` and the spinner hand-off
- `src/adw/logging/live_stream.py`:
  - delete `LiveStreamTransport`, `LEVEL_COLORS`, `CATEGORY_COLORS`, the `FileLock` import and the `adw.models.logging` import
  - in the module docstring's format example, drop the category and say UTC
- `src/adw/models/logging.py`: keep only `Verbosity`, and update the module docstring.
- `src/adw/models/__init__.py`: delete the `adw.models.logging` import block, the `- logging: …` docstring line and the four `__all__` entries.
- `docs/architecture/deep-dive/plan-phase.md` "Output Directory Structure": replace the `logs/` subtree (`logs.jsonl`, `raw.log`) with `live.log  # Log records, LLM output and tool calls (redacted, UTC)` at the run directory's root.
- Tests:
  - delete `tests/unit/logging/test_manager.py`, `tests/unit/logging/test_handler.py`, `tests/unit/logging/test_console.py` (`ConsoleTransport` formatting; `test_setup.py` covers `ConsoleHandler`), `tests/unit/models/test_logging.py` and `tests/integration/cli/test_logs_integration.py` (`LogManager`/`child`; `test_setup.py` covers `live.log` creation and levels)
  - `tests/unit/dashboard/test_log_viewer.py::test_reads_log_written_by_run`:
    - `setup_logging(Verbosity.NORMAL, run_dir, console=Console(file=io.StringIO()))`, then `logging.getLogger("adw.core.orchestrator").info("phase plan started", extra={"phase": "plan"})`
    - drop the root-handler bookkeeping; the conftest fixture cleans up
    - also assert `_load_log_entries(runs_dir, run_id, phase="plan")` returns the entry
  - `tests/unit/cli/test_logs.py` export test: write a plain `live.log` line instead of `logs.jsonl` built from `LogEvent`s, and drop the `adw.models.logging` import
  - `tests/unit/executors/test_claude_code.py`:
    - `test_outputs_to_live_stream_when_configured` builds a `LiveStreamHandler`
    - add `test_llm_output_secrets_are_redacted_in_live_log`: `handler = setup_logging(Verbosity.NORMAL, tmp_path, console=Console(file=io.StringIO()))` and `ClaudeCodeExecutor(LLMConfig(path="claude"), live_stream=handler)`. The mocked stdout (same `patch("adw.executors.claude_code.asyncio")` setup as the test above) yields:
      - an `assistant` message whose text block reads `Use sk-ant-api03-` + 24 × `a`
      - a `tool_use` block `Bash` whose `command` carries `ghp_` + 36 × `b`

      Then assert that `live.log` contains `[REDACTED]` and neither `sk-ant-api03-aaaa` nor `ghp_bbbb`.
  - `tests/unit/cli/test_bootstrap.py`: add `test_executor_writes_through_the_given_live_stream`: `monkeypatch.delenv("ADW_MOCK_EXECUTOR")`, `handler = LiveStreamHandler(tmp_path / "live.log")`, `create_orchestrator(with_progress=False, live_stream=handler)`, then assert `orchestrator._phase_runner.executor.live_stream is handler`
  - `tests/unit/cli/test_run.py`: add `test_run_hands_the_one_live_log_handler_to_the_orchestrator`:
    - patch `adw.cli.app.create_orchestrator` with `MagicMock(wraps=create_orchestrator)` and invoke `run --phase plan "Add feature" --no-worktree` in the autouse `git_repo`
    - assert that the captured `live_stream` kwarg is the only `LiveStreamHandler` on `logging.getLogger("adw")`, and that its file sits under `.adw/runs/<run id>/`
    - assert that no `live.log.lock` exists under `.adw/runs`

## Acceptance

- [ ] The executor's `live_stream` is the `live.log` handler that `setup_logging` put on the `adw` logger. No second writer exists and no lock file is written.
- [ ] Secrets in mocked LLM text and in a Bash tool call reach `live.log` as `[REDACTED]`.
- [ ] `adw -v resume` prints each DEBUG line once (no `basicConfig` duplicate).
- [ ] `ls src/adw/logging` lists `__init__.py`, `console.py`, `live_stream.py` and `redactor.py` only (plus `__pycache__`).
- [ ] `grep -rn -I --exclude-dir=__pycache__ "LogManager\|LogManagerHandler\|LogEvent\|LogContext\|LogCategory\|LogLevel\|ConsoleTransport\|LiveStreamTransport\|create_log_manager\|StructuredFileTransport\|logs\.jsonl\|VERBOSITY_LEVEL_MAP\|LEVEL_ORDER" src tests docs/architecture` prints nothing.
- [ ] `uv run pytest tests/unit/logging tests/unit/cli tests/unit/executors tests/unit/dashboard tests/unit/models tests/integration -o addopts=""` and `scripts/preflight.sh` pass.

Evidence: the RED run (the three new tests fail: `create_orchestrator` has no `live_stream` parameter, and the executor test finds the secrets in `live.log` because the old transport wrote tokens unredacted); the GREEN pytest tail; `ls src/adw/logging`; the empty grep; the preflight tail.

## Steps

### RED
- [ ] Add the three new tests and switch the existing live-stream test to `LiveStreamHandler`. Run them: the three new tests fail.

### GREEN
- [ ] Switch `bootstrap.py`, `app.py`, `resume.py` and `claude_code.py`. Delete the old modules, classes and models, and trim `models/__init__.py`.
- [ ] Delete and rewrite the old tests listed above, and fix `plan-phase.md`.
- [ ] Run the partial suite: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes. Run the grep and the `ls`.

## Notes

- The bootstrap test must drop `ADW_MOCK_EXECUTOR`, which `tests/conftest.py` sets, or `create_orchestrator` builds a `MockExecutor`, which has no `live_stream`. `monkeypatch.delenv` restores the variable afterwards. Building a `ClaudeCodeExecutor` runs no subprocess.
- The redaction test's stream-json lines must match what `_extract_display_text` and `_extract_tool_call` parse. Copy the shapes from `TestOutputParsing::test_parses_assistant_message_text` and `test_parses_tool_calls`.
- The run test goes through `--phase plan --no-worktree`, the shortest real path to `create_orchestrator` in the mocked pipeline. `plan/pre.sh` may switch branches, which is safe inside `git_repo`.
