# TASK-004: Show DEBUG lines for adw -v run --dry-run

Depends on: TASK-003
Suggested commit: `fix(cli): show debug logs on verbose dry runs`

## Goal

`adw -v run --dry-run "x"` prints DEBUG lines (B8), and a normal `adw run` prints nothing new.

## Files

- `src/adw/cli/app.py` `run()`: right after the `try: config = ConfigLoader().load() … except ConfigError` block, add `setup_logging(verbosity, console=console, redaction=redaction_config)`. It attaches the console handler, with no `live.log`, before input resolution and the dry-run branch. Read `verbosity` from `ctx.obj` there, moving today's later read up. The later `setup_logging(verbosity, run_dir, …)` call from TASK-003 stays and replaces these handlers for the real run.
- `src/adw/task_managers/resolver.py`: the three `logger.info` calls in `InputResolver.resolve` become `logger.debug`. They are diagnostics of the task-id guess, and with the console attached earlier they would otherwise print on every run.
- `tests/unit/cli/test_verbosity.py`: add
  - `test_verbose_dry_run_prints_debug_lines`: `runner.invoke(app, ["-v", "run", "--dry-run", "x"])` → exit 0, `[DEBUG]` and `Input treated as feature string` in the output
  - `test_default_dry_run_prints_no_debug_lines`: the same without `-v` → exit 0, no `[DEBUG]` and no `Input treated as` in the output
- `tests/unit/task_managers/` (whichever file tests `InputResolver`): if a test asserts the INFO level of these records through `caplog`, move it to DEBUG. Run `grep -rn "Input treated as\|Input resolved as" tests` first.

## Acceptance

- [ ] `adw -v run --dry-run "x"` exits 0 and prints at least one `[DEBUG]` line.
- [ ] `adw run --dry-run "x"` prints no `[DEBUG]` and no resolver line.
- [ ] `uv run pytest tests/unit/cli tests/unit/task_managers -o addopts=""` and `scripts/preflight.sh` pass.

Evidence: the RED run (the verbose test finds no `[DEBUG]`, because the dry-run returns before any handler is attached), the GREEN pytest tail, and the preflight tail. TASK-005 takes the scratch-repo transcript.

## Steps

### RED
- [ ] Add the two tests. Run them: the verbose one fails and the default one passes.

### GREEN
- [ ] Add the early `setup_logging` call and demote the resolver lines. Run the partial suite: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- `tests/unit/cli/conftest.py`'s autouse `isolated_cwd` runs the dry run in an empty `tmp_path`, with no git and no `.adw`. `ConfigLoader().load()` raises `ConfigError` there and `redaction_config` stays `None`, so the redaction defaults apply. The existing `test_quiet_and_verbose_mutually_exclusive` already dry-runs from that directory.
