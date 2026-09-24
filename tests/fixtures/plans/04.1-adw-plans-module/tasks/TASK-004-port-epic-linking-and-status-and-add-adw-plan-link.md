# TASK-004: Port epic linking and status, and add adw plan link

Depends on: TASK-001
Suggested commit: `feat(plans): port epic linking and status, and add adw plan link`

## Goal

ADW links a plan to its epic phase both ways, and reports an epic's phase counts, as `link_plan.py` and `epic_status.py` do. The bundled final-validation template calls `adw plan link`, so nothing under `src/adw` mentions `.claude/skills`.

## Files

- `src/adw/plans/epics.py`: new.
  - `epics_dir(root)` is `root / "docs" / "artifacts" / "epics"`.
  - `resolve_epic_file(root, token) -> Path | None`, the script's rule:
    - `12`, `E12` or `012` pick `12-*.md`
    - an exact name, with or without `.md`
    - else a unique substring match, never `EPICS.md`
  - `LINK_STATUSES = ("planned", "in-progress", "done")`.
  - `link_plan(root, epic, *, phase, plan, status="planned") -> tuple[Path, Path]` writes both sides and returns `(epic_file, plan_md)`:
    - the epic phase's `**Plan**:` line, inserted after the heading when the phase block has none
    - PLAN.md's `Epic:` and `Phase:` fields, and `Linear:` when the phase has an id
    - fields a plan lacks are inserted after `Created:`, else after `Status:`

    It raises `EPIC_NOT_FOUND`, `PHASE_NOT_FOUND`, `PLAN_NOT_FOUND` or `INVALID_PLAN` (bad status).
  - `EpicStatus(BaseModel)`: `epic`, `epic_slug`, `linear_issue`, `linear_milestone`, `project`, `phases_total`, `phases_done`, `all_phases_done`. The first five are `str`, with `"none"` as in the script's output.
  - `epic_status(root, epic) -> EpicStatus`.
- `src/adw/cli/plan.py`: `link EPIC --phase --plan [--status] [--root]`. It prints the script's three lines: `linked plan '<slug>' <-> <epic-slug> phase <id> (status: <s>)`, `epic_file=<rel>` and `plan_file=<rel>`.
- `src/adw/defaults/plans/template-task-final-validation.md`: the "Mark the phase done" step becomes `adw plan link <NN> --phase <NN.M> --plan <plan-slug> --status done`.
- `tests/unit/cli/test_plan.py`: the golden test's `normalise` maps `python3 ~/.claude/skills/create-epic/scripts/link_plan.py` to `adw plan link`, and says it is the only non-date mapping. Also add `link` CLI tests.
- `tests/unit/plans/test_epics.py`: new. It writes a small epic fixture (two phases, one with `**Linear**:`) into `tmp_path`.

## Acceptance

- [ ] After `link_plan(root, "7", phase="7.1", plan=slug)`:
  - The epic's phase 7.1 block has `**Plan**: [<slug>](../plans/<slug>/PLAN.md) · status: planned`.
  - PLAN.md has `Epic: 07 — <title> ([epic](../../epics/07-<name>.md))`, `Phase: 7.1 — <phase title>` and `Linear: ADW-99`.
  - A second call leaves both files unchanged.
- [ ] A phase with no `**Linear**:` line leaves `Linear: none` as it is. A phase block with no `**Plan**:` line gets one right after its heading.
- [ ] A plan that has no `Epic:`/`Phase:` fields gets them inserted after `Created:`.
- [ ] `resolve_epic_file` handles each token form, returns `None` for an ambiguous substring, and never returns `EPICS.md`.
- [ ] `epic_status` on an epic with one of two phases done gives `phases_total == 2`, `phases_done == 1`, `all_phases_done is False`, and the `Linear:`, `Milestone:` and `Project:` tokens.
- [ ] `adw plan link` with an unknown phase exits 1, with `error: phase '…' heading not found in …` on stderr.
- [ ] The golden test still passes, and `grep -rn "\.claude/skills" src/adw` returns nothing.
- [ ] `uv run pytest tests/unit/plans tests/unit/cli/test_plan.py -o addopts=""` and `scripts/preflight.sh` pass.

Evidence:
- the RED failures, then the GREEN pytest tail;
- one scratch run: `link_plan.py` against a copy of the golden plan and the test epic, `adw plan link` against another copy, then `diff -r` (empty);
- the grep output.

## Steps

### RED
- [ ] Write `test_epics.py` and the `link` CLI tests. Change the template line, and run the golden test: it fails until `normalise` maps the command.

### GREEN
- [ ] Add `epics.py` and the `link` command, and extend `normalise`.
- [ ] Run the partial suite, then the scratch `diff -r` and the grep.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- The template keeps `<NN>`, `<NN.M>` and `<plan-slug>` as placeholders on the changed line, as the skill's line does. Only the command in front of them changes.
