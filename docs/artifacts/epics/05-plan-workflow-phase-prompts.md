# Epic 05 — Plan-workflow phase prompts

Status: planned
Created: 2026-09-23
Depends on: Epic 04
Project: none
Linear: ADW-35 (https://linear.app/ivo-tsonev/issue/ADW-35)
Milestone: none

## Overview

Rewrites every bundled phase so an ADW run follows the plan workflow end to end, with no human involved:

1. write the plan from the issue
2. challenge it with Codex
3. implement one task per session
4. review the branch adversarially
5. document
6. land

Each prompt is the autonomous counterpart of a skill (`create-plan`, `validate-plan`, `implement-plan`, `review-plan`, `create-pr`, `archive-plan`). Wherever a skill asks the user, the prompt decides and records its reasoning: Decisions and Assumptions in the plan, rationale in the triage tables.

Deterministic work belongs to ADW code, not the model: scaffolding, ticking tasks, commits, pushes, PR edits, merges and archiving. The BMAD workflow engine is removed at the end.

## Architecture references

- [AGENTS.md](../../../AGENTS.md): commands, `scripts/preflight.sh`, commit rules, test isolation.
- Phase deep dives, rewritten or retired by this epic:
  - [Plan phase](../../architecture/deep-dive/plan-phase.md)
  - [Build phase](../../architecture/deep-dive/build-phase.md)
  - [Validate phase](../../architecture/deep-dive/validate-phase.md)
  - [Document phase](../../architecture/deep-dive/document-phase.md)
- [PhaseRunner deep dive](../../architecture/deep-dive/phase-runner.md) and [Template reference](../../templates.md): how prompts are rendered. Phase 1.10 (ADW-16) changes the rendering order, and these prompts rely on the new order.
- [Validation phase redesign](../../analysis/validation-phase-redesign.md): earlier thinking on LLM-driven evidence gathering.
- Outside the repo:
  - The skills each prompt mirrors: `~/.claude/skills/{create-plan,validate-plan,implement-plan,review-plan,create-pr,archive-plan}/SKILL.md`.
  - The round protocol: `~/.claude/skills/shared/adversarial-rounds.md`.
  - The autonomous reference flow: `~/.claude/skills/ship-phase/workflows/{build,land}.mjs`.
  - The Codex runner: `~/.claude/commands/codex-local/adversarial-review.md`.

## Dependencies

- Epic 04 (plan files, configurable phases, issue- and plan-driven runs, branch and draft PR).
- Phase 1.10 (ADW-16): prompt includes are expanded before variables are filled, and only ADW-defined names are filled.

## Out of scope

- Linear status writes, and filing deferred findings as issues: Epic 06. Here, deferred findings are written to `VALIDATION.md` / `REVIEW.md` only.
- The event stream, failure outcomes and tool policy: Epic 07.
- Any approval or question to a human.
- New documentation files outside `docs/artifacts/`. Phase 3.5 caps `docs/` at 8 files, so 5.8 edits existing docs only.

## Phase 5.1 — Adversarial review-round engine

**Plan**: _not yet created_

**Linear**: ADW-43 (https://linear.app/ivo-tsonev/issue/ADW-43)

**Goal**: One engine runs Codex (or a fallback reviewer) rounds, records them verbatim and parses the triage table, for both plan validation and code review.

### What to build

- A `src/adw/review/` module with `run_round(scope, base, focus, risk)`:
  - It runs Codex headless as `node <latest codex-companion.mjs> adversarial-review "--wait --scope working-tree|branch [--base <ref>] <focus>"`, resolving the plugin path the way `codex-local/adversarial-review.md` does.
  - It captures the output verbatim and bounds it with a timeout.
- A fallback reviewer: a separate `claude --print` session with the same adversarial framing. It runs when the Codex plugin is missing, fails or times out, and each round file records which reviewer ran.
- Depth by risk, from `shared/adversarial-rounds.md`:

  | Risk | Round 1 reviewer | Max rounds |
  |---|---|---|
  | tiny / small | fallback reviewer | 2 |
  | medium | Codex | 3 |
  | large / high | Codex plus a second lens in parallel, findings merged and deduplicated | 3 |

  Until 8.3 exists, the second lens is the fallback reviewer.
- `round-N.md` files rendered from the round template: header, verbatim output, empty triage section.
- A triage-table parser that checks every finding has a verdict. The columns are `apply|defer|reject` for plan validation and `fix|defer|reject` for code review.
- Escalation: when the last allowed round still has action rows, the result is `escalated`, and the caller stops the run.

### Acceptance criteria

- [ ] With a fake companion script returning canned findings, `run_round` writes `round-1.md` containing the output byte-for-byte and the reviewer name.
- [ ] With the plugin path missing, the fallback reviewer runs and is recorded, and nothing raises.
- [ ] A triage table with a row missing its verdict fails validation, naming the row.
- [ ] A medium-risk review that still has action rows in round 3 returns `escalated`.
- [ ] Lint and tests pass.

### Validation

Unit tests with the fake companion, plus one real Codex round against a scratch branch, with the resulting `round-1.md` in the PR.

---

## Phase 5.2 — plan phase: autonomous plan authoring

**Plan**: _not yet created_

**Linear**: ADW-44 (https://linear.app/ivo-tsonev/issue/ADW-44)

**Goal**: The plan phase writes a complete plan from the issue, deciding open questions itself and recording each decision and assumption.

### What to build

- A new `defaults/commands/plan/prompt.md` following the create-plan method:
  1. Explore the code; `AGENTS.md` comes first.
  2. Settle the goal, constraints, non-goals and success criteria from the issue.
  3. Walk the design branches and record decisions.
  4. Pick the risk tier.
  5. Break the work into tasks, each with acceptance criteria and an `Evidence:` line.
- The interview becomes judgement. The prompt answers every open question from the issue, the code and `AGENTS.md`:
  - Each answer goes into PLAN.md as a Decision with its rationale, or as an Assumption.
  - `DECISIONS.md` is written when two or more real options were weighed.
- The prompt scaffolds through `adw plan init/add-task/add-final` (from 4.1), then fills the files in.
- For an epic phase's sub-issue, the prompt reads the phase block (What to build, Acceptance criteria), and the plan is linked with `link_plan`.
- A post-step check, with one retry with feedback before failing. It fails the phase when:
  - template placeholder text is left over;
  - Status is not `ready`;
  - the risk tier is missing;
  - the final-validation task doesn't cover every acceptance criterion.

### Acceptance criteria

- [ ] A mock run with a fixture issue produces a plan directory that passes the post-step checks.
- [ ] The prompt contains no instruction to ask the user. The fixture's open questions show up under PLAN.md's Decisions or Assumptions.
- [ ] A plan with leftover `TODO` or angle-bracket stubs fails the phase, naming the file.
- [ ] A real run on a small ADW issue produces a plan that the build phase implements without extra input (plan attached to the PR).
- [ ] Lint and tests pass.

### Validation

Tests for the checks, plus the plan directory from one real run attached to the PR.

---

## Phase 5.3 — validate-plan phase

**Plan**: _not yet created_

**Linear**: ADW-45 (https://linear.app/ivo-tsonev/issue/ADW-45)

**Goal**: A new phase challenges the plan against the code and the issue, applies real findings in place and writes VALIDATION.md.

### What to build

- A bundled `validate-plan` command:
  - A pre-step checks that the plan's Status is `draft` or `ready` and that nothing outside the plan directory is dirty.
  - Rounds run through 5.1 on the working tree, using the skill's focus text (plan vs the codebase, plan's internal coherence).
- The prompt triages every finding and applies the real ones in place:
  - New tasks go through `adw plan add-task`.
  - The final-validation task is kept covering every acceptance criterion.
  - Rounds 2–3 follow the protocol.
- Decisions the skill hands to the user are made by the model:
  - "Does the plan miss what was asked?" is judged against the saved `issue.json`.
  - A borderline design challenge is decided with a rationale.
  - An apply finding that isn't grounded in real code (a file or symbol that doesn't exist) becomes `reject`, with the reason given.
- Writes `VALIDATION.md` from the template: rounds, verdict counts, applies with where they landed, defers and rejects with rationale.
- No commits; 4.4's plan commit captures the validated plan. Status is left untouched.

### Acceptance criteria

- [ ] A mock run with canned Codex findings leaves a complete triage table, the applied edits in the plan files, and a `VALIDATION.md` listing rounds, counts and defers.
- [ ] A finding that cites a non-existent path ends as `reject` with a rationale.
- [ ] Action rows remaining after the last round stop the run with reason `plan-validation-escalated`.
- [ ] PLAN.md's `Status:` is identical before and after the phase.
- [ ] Lint and tests pass.

### Validation

Tests with the fake companion, plus the `validation/` directory from one real run on a scratch plan, in the PR.

---

## Phase 5.4 — build phase: one session per task

**Plan**: _not yet created_

**Linear**: ADW-46 (https://linear.app/ivo-tsonev/issue/ADW-46)

**Goal**: Build implements each task in its own session, and ADW ticks, commits and pushes it only after its test gate passes.

### What to build

- ADW drives build as a loop over pending tasks in PLAN.md order. Each task gets its own `claude --print` session with the implement-plan per-task prompt:
  - read the task and re-read its files;
  - red → green → refactor;
  - verify acceptance with real evidence;
  - report which files it changed. The session stops short of committing.
- After each session, an ADW gate:
  1. Run the project's test command, plus `scripts/preflight*` when present.
  2. On pass: `mark_task_done`, commit (create-commit format; subject from the task's `Suggested commit:`; the reported paths plus PLAN.md) and push.
  3. On fail: one retry session given the failure output.
  4. Still failing: the phase fails, naming the task.
- Each task's report and test output are saved to `artifacts/build/TASK-NNN.md`.
- A final-validation session runs the plan's final-validation steps (full suite, acceptance walk). Then `mark_task_done`, `set_plan_status done`, and a `chore: finalize <slug>` commit if anything changed.
- Resume starts at the first unchecked task.
- Replaces `dev-story` and the auto-commit in `build/post.sh`. The empty-build retry becomes "task produced no diff".

### Acceptance criteria

- [ ] A mock plan with 3 tasks yields the plan commit plus 3 task commits in order. Each task commit contains its PLAN.md checkbox flip and is pushed (stub remote).
- [ ] A task whose tests fail twice stops build naming `TASK-00N`, with its box unchecked and nothing committed for it.
- [ ] Interrupting after task 2 and resuming continues at task 3.
- [ ] `artifacts/build/TASK-NNN.md` exists for every completed task.
- [ ] Lint and tests pass.

### Validation

Tests with `MockExecutor`, plus a real run of a 2-task plan on a scratch repo, with the commit list in the PR.

---

## Phase 5.5 — review phase replaces validate

**Plan**: _not yet created_

**Linear**: ADW-47 (https://linear.app/ivo-tsonev/issue/ADW-47)

**Goal**: After preflight, adversarial rounds on the branch fix real bugs as separate commits and write REVIEW.md.

### What to build

- A bundled `review` command:
  1. Run preflight first; fix and commit whatever it flags.
  2. Run rounds through 5.1 with scope `branch` against the base, using the review-plan focus.
- The prompt triages every finding:
  - Each `fix` is one commit, `fix(<scope>): … (review #N.M)`, followed by the fast feedback check. Its SHA is recorded in the triage table.
  - Borderline design challenges are decided with a rationale.
- Writes `REVIEW.md` from the template and commits the review record as `chore(<slug>): record adversarial review`.
- The old `validate` command (`code-review-loop`) stays for projects that list it, until 5.8 removes it.

### Acceptance criteria

- [ ] A mock round with two fix findings yields two fix commits and a review-record commit, with both SHAs in the triage table.
- [ ] On a fixture repo with a lint error, preflight fixes and commits it before round 1.
- [ ] Action rows remaining after the last round stop the run with reason `review-escalated`.
- [ ] Lint and tests pass.

### Validation

Tests with the fake companion, plus one real Codex review of a scratch branch, with `reviews/` and `REVIEW.md` in the PR.

---

## Phase 5.6 — document phase and ready PR

**Plan**: _not yet created_

**Linear**: ADW-48 (https://linear.app/ivo-tsonev/issue/ADW-48)

**Goal**: Docs are updated, and the draft PR becomes ready with a body built from the plan, VALIDATION.md and REVIEW.md.

### What to build

- The document prompt keeps feature-doc and `CONDITIONAL_DOCS.md` updates, committed with explicit paths. It no longer writes a PR description.
- A step at the end of document composes the PR, then applies it with `gh pr edit` and `gh pr ready`:
  - Title: a Conventional Commits summary.
  - Body:
    - Summary from PLAN.md's Goal and Scope.
    - Test plan from the final-validation evidence.
    - `## Plan validation` (VALIDATION.md) and `## Adversarial review` (REVIEW.md).
    - Known limitations from the defers.
    - `Closes <ISSUE-ID>` when the run has an issue.

### Acceptance criteria

- [ ] After document on a mock run, the stubbed `gh` receives an edited body containing both review sections and `Closes ADW-<n>`, followed by `gh pr ready`.
- [ ] The document prompt no longer asks for a PR description, and its output is not parsed for one.
- [ ] Lint and tests pass.

### Validation

Tests with stubbed `gh`, plus the body of one real PR produced this way, linked from the PR.

---

## Phase 5.7 — Land: CI, merge and archive

**Plan**: _not yet created_

**Linear**: ADW-49 (https://linear.app/ivo-tsonev/issue/ADW-49)

**Goal**: ADW waits for CI, makes one fix attempt if it fails, merges, and archives the plan.

### What to build

- The ship phase watches CI with `gh pr checks --watch` (configurable timeout):
  - Green: merge with a merge commit.
  - Red: one fix session reads the failing check's log and fixes it, without weakening tests; commit, push, and watch again.
  - Red again: the phase fails with `ci-red`, and the PR is left open.
- After merge, in the main checkout:
  1. `adw.plans.archive_plan` moves the plan to `plans/archive/<mergedAt>-<slug>/`.
  2. Commit `chore: archive plan <slug> after PR #<n> merge` and push it to the base.
  3. Delete the local branch and remove the run's worktree.
- Version bump and publish commands stay optional config that runs before merge.
- Remove `ship/instructions.xml` and the `DEPLOYMENT_STATUS` / `PR_MERGE_APPROVED` marker parsing in `ship/post.sh`.

### Acceptance criteria

- [ ] With stubbed `gh` and green checks, merge is called with `--merge`, the plan sits in `plans/archive/` under a date prefix, and the archive commit is on the base.
- [ ] Red, then green after the fix: exactly one fix commit, then a merge.
- [ ] Red twice: run failed with `ci-red`, and no merge call.
- [ ] Lint and tests pass.

### Validation

Tests with stubbed `gh`, plus one real end-to-end run on a scratch GitHub repo, with the PR and archive commit linked from the PR.

---

## Phase 5.8 — Remove the BMAD engine

**Plan**: _not yet created_

**Linear**: ADW-50 (https://linear.app/ivo-tsonev/issue/ADW-50)

**Goal**: No phase depends on workflow.xml or the BMAD create-story, dev-story, code-review-loop or document-feature files.

### What to build

- Delete from `defaults/commands/`:
  - `workflow.xml`
  - `plan/create-story/`, `build/dev-story/`, `validate/code-review-loop/`, `document/document-feature/`
  - `ship/instructions.xml`
  - the old `validate` command
  - every `_bmad` path reference
- Switch the default `phases:` to `[plan, validate-plan, build, review, document, ship]`, and have `adw init` write it.
- Update the existing phase docs and `docs/templates.md` to describe the new phases, editing files in place. No new doc files outside `docs/artifacts/` (phase 3.5's cap).

### Acceptance criteria

- [ ] `git grep -n "_bmad\|workflow.xml\|create-story\|dev-story\|code-review-loop\|document-feature" src docs` returns nothing outside `docs/artifacts/`.
- [ ] A fresh `adw init` project runs the new sequence end to end with `MockExecutor`.
- [ ] Every doc path referenced from `AGENTS.md` and `CONDITIONAL_DOCS.md` exists.
- [ ] Lint and tests pass.

### Validation

The grep output and a mock end-to-end run transcript in the PR.

---

<!-- PHASES -->

## Epic-level acceptance criteria

- [ ] On a scratch GitHub repo, `adw run <ISSUE-ID>` with no human input produces, in order: a validated plan, one commit per task, a review record, a ready PR carrying both review sections, green CI, a merge commit, and an archived plan.
- [ ] Every phase merged and its acceptance criteria met
- [ ] Status row in [EPICS.md](./EPICS.md) updated to `Done`
