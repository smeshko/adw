# Plan: Remove the terminal dashboard

Status: in-progress
Branch: feature/adw-20
Risk: small
Epic: 02 — Cleanup: remove inert features and consolidate ([epic](../../epics/02-cleanup-remove-and-consolidate.md))
Phase: 2.4 — Remove the terminal dashboard
Linear: ADW-20
Created: 2026-09-23

## Goal

`adw` has one dashboard, the web one. The terminal dashboard, its `adw global dashboard` command and their tests are gone, and no text points users at a dashboard that no longer exists.

## Scope

- Delete `src/adw/cli/dashboard.py`, the 1,097-line Rich/termios TUI (`DashboardController`, `DashboardLayout`, `DashboardState`, `DashboardData`, `run_dashboard`).
- Delete `dashboard_command`, the `adw global dashboard` command in `cli/global_commands.py` (L674–733).
- Delete the tests, 104 in all:
  - `tests/unit/cli/test_dashboard.py`
  - `tests/integration/cli/test_dashboard_integration.py`, which holds the flaky `test_stats_display_with_real_data`
  - `TestDashboardCommand` in `tests/unit/cli/test_global_commands.py`
- Delete the `## Gotchas` section of `AGENTS.md`. Its only entry is the flaky TUI test.
- Change "global dashboard" to "web dashboard" in every hint (user's choice). The hints are:
  - the `register`, `unregister` and `projects` help and module docstrings
  - the wizard's registry step: intro, prompt, step title, summary lines and warning
  - the registry docstrings
- In the same bullet lists, replace the three "TUI dashboard project breakdown" bullets and fix two wrong command names.

## Out of Scope

- The web dashboard (`src/adw/dashboard/`, `cli/dashboard_web.py`). It stays unchanged.
- `ProjectRegistryManager`, `StatsAggregator` and `IndexManager`. The web dashboard and `adw global list`/`stats` still use them.
- The wizard's structure and identifiers (`GlobalRegistryStepHandler`, `WizardStep.GLOBAL_REGISTRY`, `global_registry_enabled`). Phase 2.6 replaces them; this phase changes strings only.
- Renaming or merging `adw register`, `unregister` and `projects`: phase 2.12.
- A stub or deprecation message for `adw global dashboard` (user's choice).

## Research Summary

Findings from exploration and a prototype on a scratch copy of `src` at `be1d5bf8`:

- **Importers.** Only the function-local import in `dashboard_command` (`global_commands.py:722`) and the three test files import `adw.cli.dashboard`. `cli/__init__.py` doesn't re-export it. `cli.dashboard_web` is a separate module, and the epic's grep pattern `cli.dashboard import` doesn't match it.
- **Cascades.** Nothing becomes dead. The prototype deleted the module and the command, then diffed `uvx vulture --min-confidence 60`: only the two removed entries (`scroll_offset`, `dashboard_command`) left the report, and no new entry appeared. `ruff check` passes on the edited `global_commands.py`.
- **Data sources.** The TUI's data sources have other callers in `dashboard/` and `global_commands.py`: `IndexManager.get_recent_runs`, `ProjectRegistryManager.get_all` and `StatsAggregator`.
- **Dependencies.** No dependency leaves. The TUI uses `rich` plus the stdlib's `termios`, `tty` and `select`.
- **Baseline.** 3,817 passed, 5 skipped, coverage 85.05%. `cli/dashboard.py` has 456 statements at 79% coverage, below the average, so deleting it raises the total slightly. Expected after the change: about 3,713 passed.
- **Size.** `src` has 43,445 lines of `.py`. Deleting the module and the command removes about 1,160.
- **Wording.** `src` has 19 "global dashboard" sites to reword, listed in TASK-002. No test asserts any of those strings. Outside `docs/artifacts/epics`, no doc mentions the TUI or `adw global dashboard`.

## Decisions

- **No stub for `adw global dashboard` (user's choice).** Typer answers "No such command 'dashboard'" and exits 2. The epic removes commands outright, and a stub would be more code to delete later.
- **Say "web dashboard" instead of "global dashboard" (user's choice).** The registry feeds the web dashboard's project list and filter, so the new wording is accurate. The rule:
  - "global ADW dashboard" and "ADW global dashboard" become "ADW web dashboard"
  - "global dashboard" becomes "web dashboard"
  - "Global Dashboard" becomes "Web Dashboard"

  Identifiers keep their names.
- **Fix the wrong command names in the registry bullet lists.** `adw runs --global` and `adw stats` don't exist. These lists are rewritten anyway, so they now name `adw global list`, `adw global stats` and the web dashboard.
- **The `AGENTS.md` gotcha goes in TASK-001**, in the same commit as the test file it names, so no commit leaves a pointer to a deleted file. The `## Gotchas` heading goes too, because the section would be empty.
- **No new tests.** ADR-001 rules out help-text tests. CLI output demonstrates the removal instead: `adw global --help`, and `adw global dashboard` exiting 2.
- **Two commits.** TASK-001 is the deletion, which must land as one commit (module, command and tests). TASK-002 changes text only.

## Risks

- **A lazy import elsewhere still reaches `adw.cli.dashboard`.** Mitigation: TASK-001 greps `src` and `tests` for it, and mypy follows function-local imports. The prototype found only `global_commands.py:722`.
- **The rewording changes a string that a test asserts.** Mitigation: a grep of `tests/` found none, and TASK-002 runs the CLI, wizard, core and model tests.
- **Coverage drops below 80%.** Unlikely: the deleted module is below average, so the total rises. TASK-003 runs the full suite anyway.

## Acceptance Criteria

- [ ] `adw global --help` lists no `dashboard`, and `adw global dashboard` exits 2 with "No such command". Evidence: both transcripts.
- [ ] `adw dashboard web` is unaffected: started with a scratch `HOME`, a `curl` of `/` returns 200. Evidence: the curl status line.
- [ ] `grep -rn "cli.dashboard import\|cli/dashboard.py\|test_stats_display_with_real_data" src tests AGENTS.md` returns nothing. Evidence: the empty grep output.
- [ ] `grep -rni "global \(adw \)\?dashboard" src` and `grep -rn "TUI" src` return nothing, and `adw register --help` says "ADW web dashboard". Evidence: the empty greps and the help output.
- [ ] `uvx vulture src/adw --min-confidence 60`, diffed against the merge-base, reports no new entry. Evidence: the empty `comm -13` output.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%. Evidence: the preflight output and the pytest summary line with the coverage total.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Delete the terminal dashboard and its command
- [x] TASK-002: Point registry and wizard text at the web dashboard (depends on TASK-001)
- [ ] TASK-003: Final Validation
