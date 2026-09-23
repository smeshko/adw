# Validation: Remove the terminal dashboard

Validated on `feature/adw-20` at `17e0a6fc`, merge-base `be1d5bf8` (`origin/staging`), 2026-09-23.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| `adw global --help` lists no `dashboard`, and `adw global dashboard` exits 2 with "No such command" | Met | [Smoke transcripts](#smoke-test): the command list is `list`, `stats`, `clean`; `No such command 'dashboard'.`, `exit=2` |
| `adw dashboard web` is unaffected: with a scratch `HOME`, a `curl` of `/` returns 200 | Met | [Smoke transcripts](#smoke-test): `status=200` |
| `grep -rn "cli.dashboard import\|cli/dashboard.py\|test_stats_display_with_real_data" src tests AGENTS.md` returns nothing | Met | [Greps](#greps): empty, exit 1 |
| `grep -rni "global \(adw \)\?dashboard" src` and `grep -rn "TUI" src` return nothing, and `adw register --help` says "ADW web dashboard" | Met | [Greps](#greps) and [smoke transcripts](#smoke-test) |
| `uvx vulture src/adw --min-confidence 60`, diffed against the merge-base, reports no new entry | Met | [Vulture diff](#vulture-diff): `comm -13` empty |
| `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80% | Met | [Preflight and tests](#preflight-and-tests): `preflight: ok`; 3,713 passed, 85.27% |

## Preflight and tests

```text
$ scripts/preflight.sh
==> ruff check
All checks passed!
==> ruff format --check
153 files already formatted
==> mypy
Success: no issues found in 153 source files
preflight: ok

$ uv run pytest
TOTAL                                    12242   1576   3520    361    85%
Required test coverage of 80% reached. Total coverage: 85.27%
================= 3713 passed, 5 skipped in 171.90s (0:02:51) ==================
```

The baseline was 3,817 passed at 85.05% coverage. The 104 deleted tests account for the whole drop, and coverage rose by 0.22 points.

```text
$ uv run python -c "import adw.cli.app, adw.cli.global_commands, adw.dashboard.routes"; echo "exit=$?"
exit=0
```

## Greps

```text
$ grep -rn "cli.dashboard import\|cli/dashboard.py\|test_stats_display_with_real_data" src tests AGENTS.md; echo "exit=$?"
exit=1
$ grep -rni "global \(adw \)\?dashboard" src; echo "exit=$?"
exit=1
$ grep -rn "TUI" src; echo "exit=$?"
exit=1
```

## Vulture diff

```text
$ comm -13 vb.txt vh.txt        # new at HEAD
(empty)
$ comm -23 vb.txt vh.txt        # gone since the merge-base
src/adw/cli/dashboard.py: unused variable 'scroll_offset' (60% confidence)
src/adw/cli/global_commands.py: unused function 'dashboard_command' (60% confidence)
```

The report shrank from 175 entries to 173, and the two entries that left were in the deleted code.

## LOC

| | `.py` lines in `src` |
|---|---|
| Merge-base `be1d5bf8` | 43,445 |
| HEAD `17e0a6fc` | 42,282 |
| Change | −1,163 (target: at least −1,100) |

## Smoke test

Run from a scratch directory with `HOME` set to a scratch home.

```text
$ adw global --help
 Usage: adw global [OPTIONS] COMMAND [ARGS]...

 Cross-project commands for viewing runs across all projects

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list    List runs across all projects.                                       │
│ stats   Show aggregate statistics across all projects.                       │
│ clean   Clean up stale and temporary entries from the global index.          │
╰──────────────────────────────────────────────────────────────────────────────╯

$ adw global dashboard; echo "exit=$?"
Usage: adw global [OPTIONS] COMMAND [ARGS]...
Try 'adw global --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'dashboard'.                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
exit=2

$ adw register --help
 Usage: adw register [OPTIONS]

 Register current project in the ADW web dashboard.

 Adds the current project to the global project registry at
 ~/.adw/projects.yaml.
 This enables the project to appear in cross-project views like:
 - Global run list (adw global list)
 - Cross-project statistics (adw global stats)
 - Web dashboard project list and filter
 ...

$ adw dashboard web --no-browser --port 8765 &
$ curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/
status=200
```

Before the change, `adw global --help` also listed `dashboard   Launch the interactive TUI dashboard.`

### Registry text (TASK-002)

```text
$ adw unregister --help
 Unregister current project from the ADW web dashboard.

$ adw projects --help
 Shows all projects registered in the ADW web dashboard at
 ~/.adw/projects.yaml.

$ printf 'n\n' | uv run python -c "from rich.console import Console; from adw.cli.wizard.global_registry import run_global_registry_step; print(run_global_registry_step(None, Console()))"

The ADW web dashboard tracks runs across all your projects.
Registering allows this project to appear in cross-project views.

Register this project in the ADW web dashboard? [y/n] (y): {'global_registry_enabled': False, 'global_registry_name': None}
```
