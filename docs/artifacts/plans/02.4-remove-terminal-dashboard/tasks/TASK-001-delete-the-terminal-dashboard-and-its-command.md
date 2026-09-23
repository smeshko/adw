# TASK-001: Delete the terminal dashboard and its command

Depends on: None
Suggested commit: `refactor(cli): remove the terminal dashboard`

## Goal

`cli/dashboard.py`, the `adw global dashboard` command, their tests and the `AGENTS.md` gotcha about the TUI's flaky test are gone. Nothing in `src` or `tests` imports `adw.cli.dashboard`.

## Files

- `src/adw/cli/dashboard.py`: delete.
- `src/adw/cli/global_commands.py`: delete `dashboard_command`. The span runs from `@global_app.command(name="dashboard")` (L674) through `raise typer.Exit(code=0) from None` (L733), plus the blank lines after it. Afterwards, the `# Clean Command` banner follows `stats_command` after the usual two blank lines. No import becomes unused; the prototype's `ruff check` passed.
- `tests/unit/cli/test_dashboard.py`: delete.
- `tests/integration/cli/test_dashboard_integration.py`: delete.
- `tests/unit/cli/test_global_commands.py`:
  - Delete `class TestDashboardCommand`, from L121 to the end of the file.
  - Delete `from unittest.mock import MagicMock, patch` (L8). Only that class uses it.
  - Keep `import click`: `TestGlobalListCommand` uses it.
- `AGENTS.md`: delete the `## Gotchas` section, which is the heading, its blank line and the "Flaky:" bullet. It has no other entry.

## Acceptance

- [ ] `grep -rn "cli\.dashboard import\|cli\.dashboard\.\|run_dashboard\|DashboardController\|test_stats_display_with_real_data" src tests AGENTS.md` returns nothing. The `cli\.dashboard\.` pattern catches the `patch("adw.cli.dashboard.…")` strings but not `cli.dashboard_web`.
- [ ] `uv run adw global --help` lists `list`, `stats` and `clean`, and no `dashboard`.
- [ ] `uv run adw global dashboard` exits 2 with "No such command 'dashboard'".
- [ ] `scripts/preflight.sh` passes, and `uv run ruff check tests/unit/cli/test_global_commands.py` passes.
- [ ] `uv run pytest tests/unit/cli tests/integration/cli -o addopts=""` passes.

Evidence: the empty grep, both CLI transcripts, the preflight output and the pytest summary line.

## Steps

### RED
- [ ] Record the before state for the PR: `uv run adw global --help` lists `dashboard`. There is no failing test to write. ADR-001 rules out help-text tests, and the removed command has no replacement behaviour to test.
- [ ] Confirm the importers: `grep -rn "cli\.dashboard import\|cli\.dashboard\." src tests` shows only `global_commands.py:722` and the three test files.

### GREEN
- [ ] `git rm src/adw/cli/dashboard.py tests/unit/cli/test_dashboard.py tests/integration/cli/test_dashboard_integration.py`.
- [ ] Delete `dashboard_command` from `global_commands.py`.
- [ ] Delete `TestDashboardCommand` and the mock import from `test_global_commands.py`.
- [ ] Delete the `## Gotchas` section from `AGENTS.md`.
- [ ] Run the targeted pytest command from Acceptance.

### REFACTOR
- [ ] Run `uv run ruff check tests/unit/cli/test_global_commands.py` and `uv run ruff format --check tests/unit/cli/test_global_commands.py`.
- [ ] Run `scripts/preflight.sh`.
- [ ] Run the grep and both CLI commands from Acceptance, and keep the output for the PR.

## Notes

- Line numbers refer to `be1d5bf8`.
- `tests/integration/cli/` keeps 12 other test modules, so the package stays.
- Leave the "global dashboard" wording in the registry and wizard files alone. TASK-002 changes it.
