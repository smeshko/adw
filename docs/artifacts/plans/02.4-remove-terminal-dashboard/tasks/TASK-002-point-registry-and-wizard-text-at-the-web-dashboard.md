# TASK-002: Point registry and wizard text at the web dashboard

Depends on: TASK-001
Suggested commit: `chore(cli): point registry and wizard text at the web dashboard`

## Goal

Help text, prompts and docstrings about the project registry name the web dashboard. Nothing in `src` mentions a "global dashboard" or the TUI.

## Files

All paths are under `src/adw/`, and line numbers refer to `be1d5bf8`. Change strings only; identifiers keep their names.

| Site | Now | After |
|---|---|---|
| `core/project_registry.py:7` | `in cross-project views like the global dashboard.` | `in cross-project views like the web dashboard.` |
| `core/project_registry.py:34–36` | bullets `Global run list (adw runs --global)`, `Cross-project statistics`, `TUI dashboard project breakdown` | bullets `Global run list (adw global list)`, `Cross-project statistics (adw global stats)`, `Web dashboard project list and filter` |
| `models/registry.py:7` | as `core/project_registry.py:7` | as `core/project_registry.py:7` |
| `models/registry.py:54–56` | as `core/project_registry.py:34–36` | as `core/project_registry.py:34–36` |
| `cli/register.py:4` | `the current project in the global ADW dashboard registry.` | `the current project in the ADW web dashboard registry.` |
| `cli/register.py:29` (help) | `Register current project in global ADW dashboard.` | `Register current project in the ADW web dashboard.` |
| `cli/register.py:33–35` | bullets `Global run list (adw runs --global)`, `Cross-project statistics (adw stats)`, `TUI dashboard project breakdown` | the three new bullets above |
| `cli/unregister.py:4` | `the current project from the global ADW dashboard registry.` | `the current project from the ADW web dashboard registry.` |
| `cli/unregister.py:21` (help) | `Unregister current project from global ADW dashboard.` | `Unregister current project from the ADW web dashboard.` |
| `cli/projects.py:4` | `in the global ADW dashboard registry.` | `in the ADW web dashboard registry.` |
| `cli/projects.py:42` (help) | `Shows all projects registered in the global ADW dashboard at ~/.adw/projects.yaml.` | `Shows all projects registered in the ADW web dashboard at ~/.adw/projects.yaml.` |
| `cli/wizard/__init__.py:14` | `global dashboard registration step` | `web dashboard registration step` |
| `cli/wizard/flow.py:84` (step title) | `Global Dashboard Registration` | `Web Dashboard Registration` |
| `cli/wizard/summary.py:132` (comment) | `Register project in global dashboard if enabled` | `Register project in web dashboard if enabled` |
| `cli/wizard/summary.py:198,200` (summary) | `Global Dashboard:` | `Web Dashboard:` |
| `cli/wizard/summary.py:502` | `Register project in the global ADW dashboard.` | `Register project in the ADW web dashboard.` |
| `cli/wizard/summary.py:517` (warning) | `Could not register in global dashboard` | `Could not register in web dashboard` |
| `cli/wizard/global_registry.py:4` | `the ADW global dashboard.` | `the ADW web dashboard.` |
| `cli/wizard/global_registry.py:23` | `register project in global ADW dashboard` | `register project in the ADW web dashboard` |
| `cli/wizard/global_registry.py:62` (intro) | `The ADW global dashboard tracks runs across all your projects.` | `The ADW web dashboard tracks runs across all your projects.` |
| `cli/wizard/global_registry.py:71` (prompt) | `Register this project in ADW global dashboard?` | `Register this project in the ADW web dashboard?` |

## Acceptance

- [ ] `grep -rni "global \(adw \)\?dashboard" src` returns nothing.
- [ ] `grep -rn "TUI\|adw runs --global\|(adw stats)" src` returns nothing.
- [ ] `uv run adw register --help`, `uv run adw unregister --help` and `uv run adw projects --help` each say "ADW web dashboard".
- [ ] The wizard's registry step shows the new intro and prompt. Pipe `n` into it:

  ```bash
  printf 'n\n' | uv run python -c "from rich.console import Console; from adw.cli.wizard.global_registry import run_global_registry_step; print(run_global_registry_step(None, Console()))"
  ```

  The step prints "The ADW web dashboard tracks runs…" and "Register this project in the ADW web dashboard?", then returns `{'global_registry_enabled': False, 'global_registry_name': None}`.
- [ ] `scripts/preflight.sh` passes.
- [ ] `uv run pytest tests/unit/cli tests/unit/core tests/unit/models -o addopts=""` passes.

Evidence: the empty greps, the three help outputs, the wizard-step transcript, the preflight output and the pytest summary line.

## Steps

- [ ] Before editing, run `grep -rni "global \(adw \)\?dashboard" src` and confirm it lists exactly the 19 sites in the table.
- [ ] Apply the table.
- [ ] Run both greps from Acceptance.
- [ ] Run the three `--help` commands and the wizard-step command, and keep the output for the PR.
- [ ] Run `scripts/preflight.sh` and the targeted pytest command.

## Notes

- `state` is unused in `run_global_registry_step` (`# noqa: ARG001`), so passing `None` from the smoke command is safe.
- No test asserts any of these strings. If one fails, update its expected text; don't restore the old wording.
