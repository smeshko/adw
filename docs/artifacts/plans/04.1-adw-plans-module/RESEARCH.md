# Research: adw.plans: plan files in ADW

Curated findings only — no raw conversation transcripts.

## Key Files & Directories

The skills live outside the repo, under `~/.claude/skills/`:

- `create-plan/scripts/init_plan.py`: writes `PLAN.md` from `template-plan.md`, `RESEARCH.md` from `template-research.md` when the risk is `medium`, `large` or `high`, and an empty `tasks/`. It refuses when the plan directory exists, and prints `created:`, `slug:`, `risk:` and `research:` lines.
- `create-plan/scripts/add_task.py`: next `TASK-NNN` (the highest number in `tasks/` plus one), a task file from the impl or checklist template, and a checkbox line appended to `PLAN.md`. Prints the id.
- `create-plan/scripts/add_final_task.py`: the same for `TASK-NNN-final-validation.md`, with the line `- [ ] TASK-NNN: Final Validation`.
- `create-plan/references/`: `template-plan.md`, `template-research.md`, `template-decisions.md`, `template-task-implementation.md`, `template-task-checklist.md`, `template-task-final-validation.md`.
- `validate-plan/references/`: `VALIDATION.md.tmpl`, `round.md.tmpl`. `review-plan/references/`: `REVIEW.md.tmpl` and a different `round.md.tmpl`.
- `implement-plan/scripts/list_plans.py`: `<slug>\t<status>\t<title>` for each child of `plans/` that has a `PLAN.md`, in sorted order. `archive/` has no `PLAN.md` of its own, so it drops out.
- `implement-plan/scripts/list_tasks.py`: `<task-id>\t<done|pending>\t<task-file relative to root>\t<title>` for each checkbox line in `## Tasks`, up to the next `## ` heading.
- `implement-plan/scripts/mark_task_done.py`, `set_plan_status.py`, `set_plan_branch.py`: one regex substitution each on `PLAN.md`.
- `archive-plan/scripts/archive_plan.sh` and `get_plan_branch.py`: the merged-PR check, checkout, pull, `mv` to `archive/<merge-date>-<slug>` (with `-2`, `-3` on collision) and branch delete.
- `review-plan/scripts/resolve_plan.py`: the slug for the current branch. A plan whose `Branch:` equals it wins; failing that, a plan with no `Branch:` whose slug is the branch's `/<slug>` suffix. More than one match at either step is an error.
- `create-epic/scripts/link_plan.py` and `epic_status.py`: the plan↔phase link, both sides, and the phase-completion counts.

In the repo:

- `src/adw/commands/resolver.py`: loads bundled defaults with `importlib.resources.files("adw") / "defaults" / "commands"`.
- `src/adw/cli/app.py`: registers sub-apps with `app.add_typer(<typer>, name=…)`, as `logs`, `dashboard` and `global` do.
- `src/adw/exceptions.py`: `ADWError(code, message, *, suggestion, recoverable)` and its subclasses.
- `tests/conftest.py`: the autouse `isolated_home`, and the `git_repo` fixture. `tests/unit/cli/conftest.py`: the autouse `isolated_cwd`, which enters `tmp_path`.
- `docs/artifacts/plans/archive/*`: fifteen archived plans written by the skills, all with every task ticked.

## Architecture Facts

- **Every template substitution replaces the first occurrence only.**
  - `init_plan.py` replaces, in order: `<title>`; `draft | ready | in-progress | done` with `draft`; `tiny | small | medium | large | high` with the risk; `YYYY-MM-DD` with today's date. For `RESEARCH.md` it replaces `<plan-title>`.
  - `add_task.py` replaces `TASK-00X` with the id, `<title>` with the title, and `TASK-00Y | None` with the `--depends` value or `None`.
  - `add_final_task.py` replaces `TASK-00N` with the id and `<plan-slug>` with the slug. The final-validation template holds `<plan-slug>` twice, so its second occurrence, on the `link_plan.py` line, stays a placeholder.
- **Appending a task line.** `append_task_line` strips trailing whitespace from `PLAN.md` and adds one `\n`. It adds a blank line first unless the last line starts with `- [`. It exits when `## Tasks` is missing.
- **Filenames.** A task file is `TASK-<NNN>-<slugify(title)>.md`, where `slugify` lowercases, turns every run of characters outside `[a-z0-9]` into `-`, and strips `-` at both ends. Numbering takes the highest `TASK-(\d+)-` in `tasks/` plus one, so gaps are never filled.
- **Task lines.** A line reads `- [ ] TASK-NNN: <title>`, plus ` (depends on TASK-001,TASK-002)` when there are dependencies. `list_tasks.py` parses it with `^- \[(?P<box>[ xX])\]\s+(?P<id>TASK-\d+):\s+(?P<title>.+?)(?:\s+\(depends on [^)]+\))?\s*$`.
- **Header fields.** `Status:`, `Risk:`, `Epic:`, `Phase:`, `Linear:` and `Created:` come from the template. `set_plan_branch.py` inserts `Branch:` right after `Status:`, or replaces an existing one. `link_plan.py` sets `Epic: <NN> — <title> ([epic](../../epics/<NN>-<slug>.md))`, `Phase: <NN.M> — <title>`, and `Linear: <ID>` when the phase has one.
- **The epic side.** `link_plan.py` writes `**Plan**: [<slug>](../plans/<slug>/PLAN.md) · status: <status>` into the phase block. The block runs from `## Phase <id>` to the next `## `. `epic_status.py` counts the `## Phase <n>` headings and the `**Plan**:` lines with `status: done`.
- **Archiving.** The plan dir moves one level deeper, from `plans/<slug>/` to `plans/archive/<date>-<slug>/`. Its `../../epics/` links need `../../../epics/`, and the epic's `../plans/<slug>/` link needs `../plans/archive/<date>-<slug>/`. `archive_plan.sh` fixes neither. The archives of 02.4, 02.5 and 02.6 all fixed them by hand, in their `chore: archive plan …` commits.
- **Output.** The scripts print plain text on stdout, and errors as `error: …` on stderr with exit 1.

- **Baseline.** `uv run pytest` on `779ecec6`: 2982 passed, 5 skipped in 175 s, coverage 84.79% (gate 80%).

## Constraints

- `grep -rn "\.claude/skills" src/adw` must return nothing, and today it does. Only `template-task-final-validation.md` would bring the string in.
- Tests never touch the checkout. Functions take `root`, and the CLI tests pass `--root` or run in `tmp_path` / `git_repo`.
- `ruff` (line length 88) and `mypy --strict` gate CI. Tests follow ADR-001: no help-text, import-smoke or Pydantic-smoke tests.

## Useful Commands

```bash
# Regenerate the golden tree from the skill scripts (TASK-001 records the exact inputs)
S=~/.claude/skills/create-plan/scripts
python3 $S/init_plan.py --root <dir> --title "<title>" --risk medium
python3 $S/add_task.py <slug> --root <dir> --type impl --title "<title>"
python3 $S/add_task.py <slug> --root <dir> --type checklist --title "<title>" --depends TASK-001
python3 $S/add_final_task.py <slug> --root <dir>

# Partial test run (no coverage gate)
uv run pytest tests/unit/plans tests/unit/cli/test_plan.py -o addopts=""
```

## Uncertainty

- **The grep criterion against the golden criterion.** Resolved: ADW's final-validation template names `adw plan link`, and the golden test maps that one command (see PLAN.md's Decisions).
- **Whether `archive_plan` should also do the git steps.** Resolved: no. Phase 5.7 runs them, and the function only moves files.
- **Where the round-trip fixture comes from.** Resolved: a snapshot of this plan. Archived plans have every box ticked, so they can't show a flip.

## References

- [Epic 04, phase 4.1](../../epics/04-plan-driven-runs.md)
- Epic 05 phases 5.2, 5.3, 5.4 and 5.7, and Epic 06's `adw run --epic`: the callers of `adw plan` and `adw.plans`.
- `docs/architecture/adrs/ADR-001-test-reduction-strategy.md`
