# TASK-005: Report honestly whether files were written

Depends on: TASK-004
Suggested commit: `fix(wizard): report whether files were written and exit non-zero on cancel`

## Goal

`adw init --wizard` says the files were written only after it writes them, and a decline, a write failure, the end of input or Ctrl+C says nothing was written and exits non-zero.

## Files

- `src/adw/cli/wizard/summary.py`:
  - `run_summary_step(cfg, console, root) -> bool`
  - on a "no" to "Create configuration?", print `Setup cancelled. Nothing was written.` and return `False`
  - delete `_prompt_start_over_or_cancel` and the start-over branch
  - on `ConfigWriteError`, keep the error and suggestion lines, change `No files were created.` to `No files were written.`, and return `False`
  - add `_hold_interrupts()`, a `contextmanager` that sets `signal.SIGINT` to `signal.SIG_IGN` and restores the previous handler in `finally`; run `atomic_write_config`, `_register_in_global_dashboard` and the success message inside it, so Ctrl+C cannot interrupt them or land between the write and the message that reports it (PLAN.md, Decisions)
  - on success, register in the dashboard as today, print the success message, and return `True`. The success message becomes `✓ Configuration written to <root>/.adw` followed by today's next steps; it is the only place the wizard claims a write.
- `src/adw/cli/wizard/flow.py` (`run_wizard`):
  - the welcome panel drops the `n`/`b`/`c` navigation lines. It says the wizard asks a few questions, shows a summary, and writes nothing until the user confirms, and that Ctrl+C cancels.
  - return `run_summary_step(...)`'s result; delete the "Wizard Complete!" panel
  - wrap the step loop and summary in `try/except EOFError`: print `Setup cancelled (no more input). Nothing was written.` and return `False`
- `src/adw/cli/init.py`:
  - `_run_wizard_setup`: `if not run_wizard(project_root): raise SystemExit(1)`
  - `_interrupt_handler`: `raise SystemExit(130)` instead of `0`
- `tests/unit/cli/wizard/test_flow.py`: add the stdin-driven transcript tests. Each runs `git init -q` in the autouse `tmp_path` cwd and invokes `CliRunner().invoke(app, ["init", "--wizard"], input=…)`:
  - `test_accept_defaults_writes_files_that_validate`: input is 40 newlines. Assert exit 0; `.adw/project.yaml` and every `commands/<phase>/config.yaml` exist; the step headers appear in order, `Step 1/7: Project Basics` through `Step 7/7: Configuration Summary`, which pins the sequence; the output contains `Configuration written` exactly once and none of `LLM Retry`, `b - Go back`, `c - Cancel wizard` or `Wizard Complete`; and `CliRunner().invoke(app, ["validate"])` exits 0 with `0 errors`.
  - `test_decline_at_summary_writes_nothing`: patch `adw.cli.wizard.summary._prompt_confirmation` to return `False`, input 40 newlines. (Patching `summary.Confirm.ask` would patch Rich's shared `Confirm` class for every step.) Assert exit code 1, `.adw` does not exist, `Nothing was written` is in the output, and `Configuration written` is not.
  - `test_write_failure_exits_non_zero`: patch `adw.cli.wizard.summary.atomic_write_config` to raise `ConfigWriteError(message="Failed to write config: disk full")`. Assert exit 1, `disk full` and `No files were written` in the output, `Configuration written` not in it.
  - `test_end_of_input_cancels`: input `"\n"` only. Assert exit 1, `.adw` does not exist, and `Nothing was written` in the output. Today the exit code already is 1 (Typer's `Aborted.`); the message is what's RED.
- `tests/unit/cli/wizard/test_summary.py`: add `test_write_holds_off_ctrl_c`: give it `cfg["global_registry"] = {"global_registry_enabled": True, "global_registry_name": "p"}` so registration runs, and patch `atomic_write_config`, `_register_in_global_dashboard` and `_show_success_message` with side effects that record `signal.getsignal(signal.SIGINT)`; after `run_summary_step` confirms, exactly three recordings exist, all `signal.SIG_IGN`, and `signal.getsignal(signal.SIGINT)` is back to the handler installed before the call. `TestRunSummaryStep` asserts the bool return: `True` with files on confirm, `False` and no `.adw` on decline. Delete the start-over test.
- `tests/unit/cli/test_init.py`: `test_wizard_flag_forces_wizard_mode` additionally asserts `result.exit_code == 1` and no `.adw`.

## Acceptance

- [ ] Accepting every default in a fresh git repo writes files that `adw validate` accepts, and prints `Configuration written` once.
- [ ] Declining at the summary exits 1, creates no `.adw`, and prints `Nothing was written`.
- [ ] A write failure exits 1, prints the error and `No files were written`, and no success line.
- [ ] Running out of input exits 1 and says nothing was written.
- [ ] SIGINT is `SIG_IGN` during the write, the dashboard registration and the success message, and the previous handler is back afterwards.
- [ ] The welcome panel mentions no `b`/`c` keys.
- [ ] `uv run pytest tests/unit/cli tests/unit/config -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failures (the accept test finds `Wizard Complete!` and `b - Go back`; the decline and write-failure tests exit 0; the end-of-input test lacks the message; the hold-off test records the `init` handler, not `SIG_IGN`), the GREEN pytest tail, the preflight tail, and a scratch-repo transcript of the accept and decline paths with `echo $?`, run with this worktree's `.venv/bin/adw` (for TASK-006 and the PR).

## Steps

### RED
- [ ] Add the four transcript tests, `test_write_holds_off_ctrl_c` and the bool-return summary asserts; run them: the accept test (prints `Configuration created!`, `Wizard Complete!` and `b - Go back`), the decline, write-failure, end-of-input and hold-off tests fail.

### GREEN
- [ ] Make `run_summary_step` return a bool, drop start-over, move the success claim after the write, and wrap the write, the registration and the success message in `_hold_interrupts()`.
- [ ] Update the welcome panel, return the summary result, catch `EOFError`, and exit 1/130 in `init.py`.
- [ ] Run the partial suite: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- The accept path registers the project in `~/.adw` (the registry step defaults to yes). The root `isolated_home` fixture keeps that inside the test's `HOME`.
- 40 newlines exceeds the accept path's prompt count with room to spare; unread lines are ignored. If a step later adds prompts past 40, the accept test fails loudly on `EOFError` → exit 1, not silently.
- The SIGINT exit code is not unit-tested: sending a real SIGINT inside the pytest process is fragile. The TASK-006 transcript demonstrates it by running `adw init --wizard` in a scratch repo and sending SIGINT to the process at a prompt.
- `signal.signal` works only in the main thread. The wizard runs only from the CLI's main thread, and `CliRunner` invokes in the main thread too.
