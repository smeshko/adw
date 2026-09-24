# Epic 04 — Plan-driven runs

Status: planned
Created: 2026-09-23
Depends on: Epic 03
Project: none
Linear: ADW-34 (https://linear.app/ivo-tsonev/issue/ADW-34)
Milestone: none

## Overview

Makes the plan directory the unit of work in an ADW run, so ADW can execute the same plan workflow that `create-plan` → `implement-plan` → `archive-plan` follow by hand. Today:

- the plan phase hands build a markdown blob (`{{artifacts.plan.plan_output}}`);
- the phase order is the hard-coded `PHASE_SEQUENCE`;
- branches are named after the feature text.

After this epic:

- ADW reads and writes `docs/artifacts/plans/<slug>/` in the skills' exact format;
- a run starts from a Linear issue or from an existing plan;
- the phase order comes from config;
- every run gets the workflow's branch name, plan commit and draft PR.

No prompt changes here; Epic 05 rewrites the prompts. Runs stay fully autonomous: nothing in this epic waits for a human.

## Architecture references

- [AGENTS.md](../../../AGENTS.md): base branch `staging`, Linear team ADW, labels, and the rule that tests stay out of the checkout.
- [Orchestrator deep dive](../../architecture/deep-dive/orchestrator.md): phase sequencing, resume, `--phase` / `--from-run` (4.2, 4.3). Epic 03 restructures this; trust the code.
- [PhaseRunner deep dive](../../architecture/deep-dive/phase-runner.md): template context, artifacts and hook environment (4.3).
- [Template reference](../../templates.md): the `{{artifacts.*}}` references that plan variables replace (4.3).
- The plan skills whose format and behaviour this epic ports. They live outside the repo, under `~/.claude/skills/`:
  - `create-plan/` and its `scripts/`
  - `implement-plan/scripts/`
  - `archive-plan/scripts/archive_plan.sh`
  - `create-epic/scripts/link_plan.py` and `epic_status.py`
  - `shared/linear-integration.md`

## Dependencies

- Epic 03 (ADW-6): the single run loop and explicit phase steps (3.2, 3.4) are where the configurable sequence and the pre-build step plug in.
- Phase 1.7 (ADW-13): the core `create_pr(context, body, *, base, draft=False)` in `adw.core.pr`, which 4.4 reuses; the caller owns the body. The default base branch is `GitConfig.base_branch` (`main`).
- Phase 2.10 (ADW-26): the single Linear manager that 4.3 reads issues through.

## Out of scope

- Rewriting the phase prompts: Epic 05.
- Linear status writes and follow-up issues: Epic 06. This epic only reads the issue.
- Human-in-the-loop pauses or approvals: none are planned. Wherever the skills ask the user, Epic 05's prompts decide.

## Phase 4.1 — adw.plans: plan files in ADW

**Plan**: [04.1-adw-plans-module](../plans/04.1-adw-plans-module/PLAN.md) · status: done

**Linear**: ADW-39 (https://linear.app/ivo-tsonev/issue/ADW-39)

**Goal**: ADW reads and writes the plan directory format the plan skills use, through one tested module.

### What to build

- `src/adw/plans/`: port the plan-lifecycle scripts to Python functions that write the skills' exact on-disk format.
  - Authoring: `init_plan` (PLAN.md, RESEARCH.md for medium+ risk, `tasks/`), `add_task` (impl or checklist, next `TASK-NNN`, checkbox appended to PLAN.md), `add_final_task`.
  - Reading: `list_plans`, `list_tasks`, `resolve_plan_by_branch`.
  - State: `mark_task_done`, `set_plan_status`, `set_plan_branch`.
  - Lifecycle: `archive_plan` (move to `plans/archive/<YYYY-MM-DD>-<slug>/`); `link_plan` and `epic_status` for epic files.
- Templates copied to `src/adw/defaults/plans/`: plan, impl task, checklist task, final validation, research, decisions, VALIDATION, REVIEW, round.
- A `Plan` model parsed from PLAN.md: slug, status, risk, Linear id, epic/phase, branch, and tasks with their done state.
- An `adw plan` CLI group that the prompts in Epic 05 call through Bash:
  - Read: `list`, `show <slug>`, `tasks <slug>`.
  - Write: `init`, `add-task`, `add-final`.
- Nothing in `adw.plans` shells out to `~/.claude/skills`. The skills stay the interactive tools; ADW owns its own copy of the format.

### Acceptance criteria

- [x] For the same title, risk and task list, `adw plan init/add-task/add-final` and the skill scripts produce identical trees once dates are normalised (golden-file test).
- [x] `adw plan tasks <slug>` and `mark_task_done` round-trip on a plan written by `/create-plan` in this repo.
- [x] `adw plan list` prints slug, status and title for every plan, archived ones excluded.
- [x] `grep -rn "\.claude/skills" src/adw` returns nothing.
- [x] Lint and tests pass.

### Validation

Golden-file test output, plus a scratch-repo transcript of `adw plan init` → `add-task` ×2 → `add-final` → `tasks` → `list`, pasted into the PR.

---

## Phase 4.2 — Configurable phase sequence

**Plan**: _not yet created_

**Linear**: ADW-40 (https://linear.app/ivo-tsonev/issue/ADW-40)

**Goal**: A project's phase order comes from config, defaulting to plan, validate-plan, build, review, document, ship.

### What to build

- A `phases:` list on `ProjectConfig` that replaces `PHASE_SEQUENCE` in `core/constants.py`. Every name must resolve through `commands/resolver.py` (project → user → bundled tiers).
- Everything that walks phases reads the configured list:
  - the run loop, `--phase`, `--from-run` and resume
  - required-artifact checks
  - the dashboard's pipeline view
  - the `adw validate` config checker
- Placeholder bundled commands `validate-plan` and `review`, so the new sequence resolves before Epic 05 gives them real prompts.
- The default stays the current five phases in this phase. Phase 5.8 switches the default to `[plan, validate-plan, build, review, document, ship]` once every new phase has a real prompt.

### Acceptance criteria

- [ ] A project with `phases: [plan, build]` runs exactly those two phases, and the dashboard shows two steps.
- [ ] An unknown phase name fails `adw validate` and `adw run` before any phase starts, naming the phase.
- [ ] Resuming an interrupted run continues from the next configured phase.
- [ ] `grep -rn "PHASE_SEQUENCE" src` returns nothing.
- [ ] Lint and tests pass.

### Validation

Tests for each criterion with `MockExecutor`, plus a scratch-repo `adw run` with a custom three-phase list, shown in the PR.

---

## Phase 4.3 — Issue- and plan-driven runs

**Plan**: _not yet created_

**Linear**: ADW-41 (https://linear.app/ivo-tsonev/issue/ADW-41)

**Goal**: `adw run <ISSUE-ID>` plans from the Linear issue and `adw run --plan <slug>` starts from an existing plan, with the plan directory passed between phases.

### What to build

- `adw run <ISSUE-ID>`:
  - Fetches the issue (title, description, labels, parent, project) through the task manager.
  - Saves it to the run directory as `issue.json`.
  - Uses the issue title as the feature description.
- `adw run --plan <slug>`:
  - Starts from an existing plan and skips `plan`.
  - Also skips `validate-plan` when the plan already has a `VALIDATION.md`.
- `RunContext` gains `issue_id`, `plan_slug`, `risk`, `epic` and `phase`. The last four are read from PLAN.md once the plan exists.
- The plan-phase contract: the phase must leave a plan directory with `Status: ready`, and the run records its slug. A plan phase that leaves no plan fails with a named reason.
- New template variables `{{plan.dir}}`, `{{plan.slug}}`, `{{plan.risk}}` and `{{issue.*}}` replace `{{artifacts.plan.plan_output}}`. These work with phase 1.10's rule of expanding includes before filling variables (ADW-16).
- Plain `adw run "<text>"` keeps working: no issue, and the plan is written from the text.

### Acceptance criteria

- [ ] With Linear stubbed, `adw run ADW-<n> --phase plan` (mock executor that scaffolds a plan through `adw plan`) ends with `plan_slug` set in `context.json` and `issue.json` in the run directory.
- [ ] `adw run --plan <slug>` on a plan that has a `VALIDATION.md` starts at `build`.
- [ ] A template using `{{plan.dir}}` renders the real path, and no bundled prompt references `artifacts.plan.plan_output`.
- [ ] A plan phase that finishes without a plan directory fails with reason `plan-missing`.
- [ ] Lint and tests pass.

### Validation

Tests with Linear and the executor stubbed, plus a scratch-repo run from a real ADW issue showing `issue.json` and the recorded slug.

---

## Phase 4.4 — Branch, plan commit and draft PR

**Plan**: _not yet created_

**Linear**: ADW-42 (https://linear.app/ivo-tsonev/issue/ADW-42)

**Goal**: Every run implements on a <prefix>/<issue>-<slug> branch cut from the base, with the plan as its first commit and a draft PR open before build.

### What to build

- Replace feature-text branch names (`hooks/git_branch.py`, `RunLifecycle._feature_branch_name`):
  - The branch becomes `<prefix>/<issue-id-lowercase>-<slug>`, or `<prefix>/<slug>` when there is no issue.
  - The prefix comes from the issue's Type label: `feature` → `feature`, `bug` → `bug`, `refactoring` → `refactor`. It defaults to `feature`.
  - The branch is cut from `origin/<base>` after a fetch, inside the run's worktree.
- An explicit pre-build step (the step mechanism comes from 3.4). It runs after `plan` and `validate-plan`:
  1. Commit the plan directory as `chore: add plan for <slug>`, staging only that directory.
  2. Record `Branch:` in PLAN.md.
  3. Push, and open a draft PR through `create_pr(draft=True)`.
  4. Set `context.pr_url`.
- Every commit ADW makes stages explicit paths. Remove `git add -A` from `build/post.sh` and `ship/post.sh`, which closes ADW-3.

### Acceptance criteria

- [ ] A run for an issue with Type `bug` creates `bug/adw-<n>-<slug>` from `origin/staging`, and its first commit touches only the plan directory.
- [ ] A draft PR exists, and `context.pr_url` is set, before build's first task starts (the `gh` stub records `--draft`).
- [ ] Two concurrent runs get separate worktrees and branches.
- [ ] `git grep -n "add -A" src/adw` returns nothing.
- [ ] Lint and tests pass.

### Validation

A scratch GitHub repo run (or stubbed `gh`) showing the branch, the first commit's file list and the draft PR URL in `context.json`, pasted into the PR.

---

<!-- PHASES -->

## Epic-level acceptance criteria

- [ ] On a scratch repo, `adw run ADW-<n>` ends with a plan directory committed on a correctly named branch and a draft PR open, with the phase order read from config.
- [ ] Every phase merged and its acceptance criteria met
- [ ] Status row in [EPICS.md](./EPICS.md) updated to `Done`
