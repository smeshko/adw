# TASK-005: Archive a plan and repair its relative links

Depends on: TASK-001
Suggested commit: `feat(plans): archive a plan and repair its relative links`

## Goal

`archive_plan` moves a plan to `plans/archive/<YYYY-MM-DD>-<slug>/`, as `archive_plan.sh` does. It also leaves every relative link into and out of the plan working, which today's manual archive step fixes by hand.

## Files

- `src/adw/plans/archive.py`: new.
  - `archive_plan(root, slug, merged_on: date) -> Path`:
    1. Raise `PLAN_NOT_FOUND` when `plans/<slug>/PLAN.md` is missing, and `INVALID_PLAN` for the slug `archive`.
    2. Pick `archive/<merged_on>-<slug>`, adding `-2`, `-3` and so on while that name exists.
    3. Move the dir with `shutil.move`.
    4. Rewrite the links in every `*.md` under the moved dir.
    5. Rewrite the epic links.
    6. Return the new dir.
  - Link rewrite, for each `](target)` whose target has no scheme (`^[a-z][a-z0-9+.-]*:`) and doesn't start with `/` or `#`:
    - Split off any `#anchor`.
    - Resolve the target against the file's old directory with `os.path.normpath`.
    - If the result lies outside the old plan dir, replace the target with `os.path.relpath(result, new file dir)` plus the anchor. Otherwise leave it.
    - Paths are computed, never read from disk.
  - Epic side: in each `epics/*.md`, `](../plans/<slug>/` becomes `](../plans/archive/<name>/`. The trailing `/` keeps `<slug>-2` apart from `<slug>`.
- `tests/unit/plans/test_archive.py`: new.

## Acceptance

- [ ] `archive_plan(root, slug, date(2026, 9, 24))` returns `plans/archive/2026-09-24-<slug>` and the source dir is gone. Two more archives of a same-slug plan land in `-2` and `-3`.
- [ ] After the move:
  - PLAN.md's `([epic](../../epics/04-x.md))` reads `(../../../epics/04-x.md)`.
  - RESEARCH.md's `(../../../../AGENTS.md)` reads `(../../../../../AGENTS.md)`.
  - A task file's `(../PLAN.md)` is unchanged, and its `(../../../epics/04-x.md#phase-41)` reads `(../../../../epics/04-x.md#phase-41)`.
  - `(https://…)`, `(#goal)` and `(./RESEARCH.md)` are unchanged.
- [ ] The epic's `**Plan**: [<slug>](../plans/<slug>/PLAN.md) · status: done` points at `../plans/archive/2026-09-24-<slug>/PLAN.md`. A link to `../plans/<slug>-2/` in the same epic is unchanged.
- [ ] Every rewritten link in the test resolves to an existing file (`(new_file.parent / target).resolve().exists()`).
- [ ] The error paths raise their codes and move nothing.
- [ ] `uv run pytest tests/unit/plans -o addopts=""` and `scripts/preflight.sh` pass.

Evidence: the RED failure (`No module named 'adw.plans.archive'`), then the GREEN pytest tail.

## Steps

### RED
- [ ] Write `test_archive.py`, with a plan dir, a task file, an epic and an `AGENTS.md` in `tmp_path`. Run it: it fails.

### GREEN
- [ ] Add `archive.py`.
- [ ] Run the partial suite: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.
