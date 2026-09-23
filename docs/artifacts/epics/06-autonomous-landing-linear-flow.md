# Epic 06 — Autonomous landing and the Linear flow

Status: planned
Created: 2026-09-23
Depends on: Epic 05
Project: none
Linear: ADW-37 (https://linear.app/ivo-tsonev/issue/ADW-37)
Milestone: none

## Overview

Makes the autonomous pipeline safe to leave alone and visible where work is tracked.

- **No approvals:** a run either lands, or stops with a named reason reported on its Linear issue.
- **One status spine:** Linear shows where each issue stands using the same status changes the plan skills make by hand, so ADW-run and hand-run work look the same on the board.
- **No lost findings:** deferred review findings become Backlog issues.
- **Whole epics:** `adw run --epic <NN>` ships an epic's remaining phases one after another.

## Architecture references

- [AGENTS.md](../../../AGENTS.md): Linear team ADW and the label set (never create labels).
- [Orchestrator deep dive](../../architecture/deep-dive/orchestrator.md): run status, failure paths and resume, which stop reasons plug into.
- [EPICS.md](./EPICS.md) and the epic file format, which 6.3 reads and updates.
- Outside the repo:
  - The status spine and follow-up-issue rules to reproduce: `~/.claude/skills/shared/linear-integration.md`.
  - The stop conditions of the autonomous reference flow: `~/.claude/skills/ship-phase/SKILL.md`.

## Dependencies

- Epic 05 (the full autonomous phase sequence, and the `escalated` / `ci-red` outcomes it produces).
- Phase 2.10 (ADW-26): the single Linear manager and TicketSync that the status writes go through.

## Out of scope

- Automatic pickup of new issues: Epic 08.
- Approval gates or questions to a human. A stopped run is reported, not held open.
- Creating Linear labels or projects. Missing labels are skipped with a warning.

## Phase 6.1 — Stop conditions and failure reports

**Plan**: _not yet created_

**Linear**: ADW-51 (https://linear.app/ivo-tsonev/issue/ADW-51)

**Goal**: Runs land without approval; any stop condition fails the run with a named reason posted on its Linear issue.

### What to build

- One `StopReason` enum on `RunContext`:
  - `plan-missing`, `plan-invalid`, `plan-validation-escalated`
  - `task-failed` (with the task id), `no-progress`
  - `preflight-failed`, `review-escalated`, `ci-red`, `merge-conflict`
  - `model-error`, `timeout` (both filled in by Epic 07)
- On any stop:
  - The run is marked `failed`, and the PR stays open (draft if the run never reached ship).
  - One comment goes on the issue: reason, phase, task, evidence or log path, and the exact `adw resume <run-id>` command.
- Merge conflicts: when the base moved, merge the base into the branch and rerun the tests. If the conflict can't be resolved, stop with `merge-conflict`.
- A `ship.merge` config flag, default `true`. `false` stops after the PR is ready, as a per-project policy rather than a pause.
- The run loop never reads stdin; a test runs a full mock pipeline with stdin closed.

### Acceptance criteria

- [ ] Each stop reason, forced in a test, ends with status `failed`, `stop_reason` set, and exactly one Linear comment (stubbed) containing the reason and the resume command.
- [ ] `adw resume <run-id>` after a `task-failed` stop continues from that task.
- [ ] A full mock pipeline with stdin closed completes without blocking.
- [ ] Lint and tests pass.

### Validation

Tests per stop reason, plus the Linear comment from one real forced failure (a CI red) linked in the PR.

---

## Phase 6.2 — Linear status spine and follow-up issues

**Plan**: _not yet created_

**Linear**: ADW-52 (https://linear.app/ivo-tsonev/issue/ADW-52)

**Goal**: Issue status follows the run the way the plan skills move it, and every deferred finding becomes a Backlog issue.

### What to build

- Replace `state_mapping`-driven writes with the skills' spine:
  - Plan written → Todo.
  - Build start → In Progress. On an epic's first phase, the epic parent issue moves too.
  - Review start → In Review.
  - Merge → Done, through the PR's `Closes` line.
- ADW writes Done itself only when `linear.github_integration: false`. When the integration is connected, a direct write would duplicate it.
- The issue description's Tasks section mirrors the plan's task titles once the plan exists.
- Every defer in `VALIDATION.md` and `REVIEW.md` becomes a Backlog issue:
  - Deduplicated by title.
  - The `code-review` label plus fitting existing Type/Platform labels.
  - The description carries the rationale and the plan path.
  - The created id is written back next to the defer.
- Label names that don't exist are skipped with a warning; labels are never created.

### Acceptance criteria

- [ ] With Linear mocked and the integration flag on, a full mock run writes Todo → In Progress → In Review, and no Done.
- [ ] With the flag off, Done is written after merge.
- [ ] Two defers create two Backlog issues with `code-review`, and rerunning creates none.
- [ ] The issue description lists the plan's tasks.
- [ ] Lint and tests pass.

### Validation

Tests with mocked Linear, plus the status history of one real ADW issue driven by a run, shown in the PR.

---

## Phase 6.3 — Epic runs and roll-up

**Plan**: _not yet created_

**Linear**: ADW-53 (https://linear.app/ivo-tsonev/issue/ADW-53)

**Goal**: adw run --epic <NN> ships an epic's remaining phases in order and closes the epic when its last phase merges.

### What to build

- `adw run --epic <NN>`: for each phase of `docs/artifacts/epics/<NN>-*.md` whose plan isn't done, in order:
  1. Run the plan phase with the phase block as the issue: Goal, What to build, Acceptance criteria, plus its Linear sub-issue.
  2. Link the plan with `link_plan`.
  3. Run the full sequence.
- The next phase starts only after the previous one merges. The first stop ends the epic run.
- Epic bookkeeping through `adw.plans`:
  - Phase status moves `planned` → `in-progress` → `done`.
  - When the last phase merges, close the epic parent issue.
  - Post one project status update when the epic belongs to a Linear project.
- The EPICS.md row moves to `In progress` after the first merge, and to `Done` after the last.

### Acceptance criteria

- [ ] A fixture epic with two phases and `MockExecutor` produces two runs and two merges (stubbed). Both phases end `done`, and the epic parent is closed (stubbed Linear).
- [ ] A stop in the first phase ends the epic run; the second phase never starts.
- [ ] The EPICS.md row reads `Done` after the fixture run.
- [ ] Lint and tests pass.

### Validation

Tests with fixtures, plus one real `adw run --epic` over a two-phase scratch epic, linked in the PR.

---

<!-- PHASES -->

## Epic-level acceptance criteria

- [ ] A run left alone either merges or stops with a named reason visible on its Linear issue; nothing waits for input.
- [ ] Every phase merged and its acceptance criteria met
- [ ] Status row in [EPICS.md](./EPICS.md) updated to `Done`
