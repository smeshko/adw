# TASK-002: Parse PLAN.md into a Plan model and add list, show and tasks

Depends on: TASK-001
Suggested commit: `feat(plans): parse plans and add adw plan list, show and tasks`

## Goal

ADW parses a PLAN.md into a `Plan` and lists plans and tasks. `adw plan list` and `adw plan tasks` print the same lines as `list_plans.py` and `list_tasks.py`, and archived plans are left out.

## Files

- `src/adw/plans/model.py`: new.
  - `PlanTask(BaseModel)`: `id`, `title`, `done: bool`, `depends_on: list[str]`, `file: Path | None` (absolute).
  - `Plan(BaseModel)`: `slug`, `title`, `status`, `risk`, `epic`, `phase`, `linear`, `branch`, `created`, `dir: Path` and `tasks: list[PlanTask]`.
  - Every optional field is `str | None`, where `none` or a missing field is `None`. `status` defaults to `unknown` and `title` to `""`.
- `src/adw/plans/reader.py`: new.
  - `load_plan(root, slug) -> Plan` raises `PLAN_NOT_FOUND` when there is no PLAN.md.
  - `list_plans(root) -> list[Plan]`: children of `plans/` that have a `PLAN.md`, sorted, skipping `archive/`. A missing `plans/` dir gives `[]`.
  - `list_tasks(root, slug) -> list[PlanTask]`.
  - `resolve_plan_by_branch(root, branch) -> str | None`, following review-plan's `resolve_slug`. A plan whose `Branch:` equals the branch wins. Failing that, a plan with no `Branch:` whose slug is the branch's `/<slug>` suffix. Two matches at either step raise `AMBIGUOUS_PLAN`. No match returns `None`.
  - Header fields are read from the lines before the first `## ` heading, with `^(Status|Branch|Risk|Epic|Phase|Linear|Created):\s*(.*)$`. `epic`, `phase` and `linear` keep their first token.
  - Tasks come from `## Tasks` up to the next `## `, parsed with `list_tasks.py`'s `TASK_LINE` regex plus a group for the `depends on` list.
- `src/adw/cli/plan.py`: three commands, each taking `--root`.
  - `list` prints `<slug>\t<status>\t<title>`.
  - `tasks SLUG` prints `<id>\t<done|pending>\t<file relative to root, or empty>\t<title>`.
  - `show SLUG` prints `slug=`, `title=`, `status=`, `risk=`, `epic=`, `phase=`, `linear=`, `branch=`, `created=` (`none` for `None`), then `dir=<relative to root>` and `tasks=<done>/<total>`.
- `tests/fixtures/plans/04.1-adw-plans-module/`: new. A copy of this plan's `PLAN.md`, `RESEARCH.md` and `tasks/`, taken from the working tree at the start of this task: TASK-001 ticked, Status `in-progress`, `Branch: feature/adw-39`.
- `tests/unit/plans/test_reader.py`: new.
- `tests/unit/cli/test_plan.py`: `list`, `tasks` and `show` tests.

## Acceptance

- [ ] `load_plan` on the fixture reads:
  - the title, `status == "in-progress"`, `risk == "medium"`, `epic == "04"`, `phase == "4.1"`, `linear == "ADW-39"`, `branch == "feature/adw-39"`, `created == "2026-09-24"`
  - seven tasks in order, TASK-001 done and the rest pending
  - `TASK-006.depends_on` with five ids
  - a `file` that exists for every task
- [ ] `list_tasks` ignores checkbox lines outside `## Tasks` (acceptance criteria above it, a section after it).
- [ ] `adw plan list`, run on two plans, `plans/archive/<date>-<slug>/PLAN.md`, a dir without PLAN.md, and a plan with no `Status:`, prints exactly two sorted lines. The plan without `Status:` shows `unknown`. The archived plan does not appear.
- [ ] `adw plan tasks 04.1-adw-plans-module` on the fixture prints seven lines. The first is `TASK-001\tdone\tdocs/artifacts/plans/04.1-adw-plans-module/tasks/TASK-001-bundle-the-plan-templates-and-port-plan-authoring.md\tBundle the plan templates and port plan authoring`.
- [ ] `resolve_plan_by_branch` covers:
  - a recorded match
  - a recorded match beating a suffix match
  - the suffix fallback, used only for plans without `Branch:`
  - two recorded matches (`AMBIGUOUS_PLAN`)
  - no match (`None`)
  - an archived plan that is never matched
- [ ] `adw plan show` on a missing slug exits 1, with `error: plan not found: …` on stderr.
- [ ] `uv run pytest tests/unit/plans tests/unit/cli/test_plan.py -o addopts=""` and `scripts/preflight.sh` pass.

Evidence:
- the RED failures, then the GREEN pytest tail;
- `adw plan tasks` against `list_tasks.py` on the same fixture copy (`diff` empty);
- `adw plan list` against `list_plans.py` on a scratch root holding the fixture and an archived plan (`diff` empty).

## Steps

### RED
- [ ] Copy the fixture, then write `test_reader.py` and the CLI tests. Run them: they fail on the missing `adw.plans.reader` import and the missing `list` command.

### GREEN
- [ ] Add `model.py`, `reader.py`, and the three commands.
- [ ] Run the partial suite, then the two `diff`s against the scripts.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- The fixture has to be copied at the start of this task, when implement-plan has set `Status: in-progress` and `Branch:`, and TASK-001's box is ticked. Its later history doesn't matter: the fixture is frozen from then on.
- `list_plans.py` stops at the first `Status:` line anywhere in the file. `load_plan` reads the header block only. The two agree on every plan the skills write.
