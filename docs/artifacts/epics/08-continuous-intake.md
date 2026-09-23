# Epic 08 — Continuous intake

Status: planned
Created: 2026-09-23
Depends on: Epic 06, Epic 07
Project: none
Linear: ADW-38 (https://linear.app/ivo-tsonev/issue/ADW-38)
Milestone: none

## Overview

Lets ADW find its own work and review work it didn't write.

- A Linear source feeds a deduplicated queue. A daemon drains the queue into runs, retrying with backoff and setting aside items that keep failing.
- The hackathon loop's multi-lens PR review backs ADW's high-risk reviews and can review any PR.
- An optional runtime-verify phase proves UI and API changes work in the running app.

This replaces the webhook server that phase 2.3 removes.

## Architecture references

- [AGENTS.md](../../../AGENTS.md): Linear team ADW and labels. Pickup is label-gated, and labels are never created by ADW.
- [Epic 07](./07-run-observability.md): the event stream the queue events join and the dashboard reads.
- The loop's source, under `/Users/A1E6E98/Developer/rewe/software-factory/DTGS-Sunrise%20Mobile%20App/.agents/loop/` (outside this repo):
  - `INPUT_QUEUE_PLAN.md`: the queue design and lifecycle.
  - `engine/daemon.ts`, `engine/queue-store.ts`, `engine/input-source.ts`, `sources/ado.ts`: the daemon, single-writer queue and source contract.
  - `scripts/check-scope.ts`: the offline scope check.
  - `loops/pr-review/config.ts` and `agents/pr-*-agent-prompt.md`: the six review lenses, verdict-fix and merge.
  - `agents/runtime-verify-agent-prompt.md`: runtime verification.

## Dependencies

- Epic 06: stop reasons and Linear reporting, which queue outcomes reuse.
- Epic 07: events, failure outcomes and the dashboard's event-based run views.

## Out of scope

- Sources other than Linear, such as GitHub issues.
- Any approval step. A set-aside item is visible in the queue view; resuming it is a manual command, not a pause the run waits on.

## Phase 8.1 — Linear source and work queue

**Plan**: _not yet created_

**Linear**: ADW-59 (https://linear.app/ivo-tsonev/issue/ADW-59)

**Goal**: Labelled ADW issues flow into a deduplicated queue that retries with backoff and sets aside repeat failures.

### What to build

- A Linear source:
  - Returns issues in team ADW carrying the configured pickup label and states.
  - Keys each item `linear:<issue-id>`, so an issue runs once.
  - Re-checks the label on every item after the fetch.
- A queue at `.adw/queue/`:
  - `queue.json` has one writer: the daemon.
  - `events.jsonl` records refresh, added, claimed, done, requeued, set-aside and error events.
  - `commands/*.json` files let anything else enqueue, pause, resume, requeue or drop.
- A failed item gets a not-before time and the queue moves on; after the configured attempts it is set aside.
- `adw queue verify-scope` checks offline that the source can only return labelled items.

### Acceptance criteria

- [ ] Against a fake Linear with three labelled issues and one unlabelled, a refresh queues three and ignores one; a second refresh adds nothing.
- [ ] A failing item is retried after its backoff and set aside after the configured attempts, while other items keep running.
- [ ] `adw queue verify-scope` fails when the source query drops the label filter.
- [ ] Lint and tests pass.

### Validation

Tests with a fake Linear client, plus a transcript of `adw queue status` after a refresh against the real team (with a test label), in the PR.

---

## Phase 8.2 — adw watch daemon and queue view

**Plan**: _not yet created_

**Linear**: ADW-60 (https://linear.app/ivo-tsonev/issue/ADW-60)

**Goal**: A daemon drains the queue into runs, and the dashboard shows the queue and why each item is where it is.

### What to build

- `adw watch [--once] [--dry-run]`:
  - Claims items and runs each one in its own worktree, up to the configured concurrency.
  - Emits queue events.
  - Shuts down gracefully between phases.
- `adw queue status | requeue | drop`, all through command files.
- A dashboard queue page:
  - Source health and next poll time.
  - Items grouped by state, each with its reason; set-aside items first.
  - A link from each item to its run.

### Acceptance criteria

- [ ] `adw watch --once` over a fixture queue of two items runs both with `MockExecutor` and exits.
- [ ] SIGINT during a run stops it between phases and requeues the item.
- [ ] The queue page lists each item with its state and reason.
- [ ] Lint and tests pass.

### Validation

Tests with fixtures, plus a recording of `adw watch` draining two real labelled issues, linked in the PR.

---

## Phase 8.3 — Multi-lens PR review loop

**Plan**: _not yet created_

**Linear**: ADW-61 (https://linear.app/ivo-tsonev/issue/ADW-61)

**Goal**: Any PR can be reviewed by six focused lenses, fixed, and merged or commented on, and the same lenses back high-risk reviews.

### What to build

- `adw review-pr <number>`:
  1. Six lens sessions write findings JSON: style, architecture, side effects, performance, security, coverage.
  2. A static check runs preflight and the tests.
  3. A verdict-fix session applies the real findings as commits.
  4. The loop comments on the PR, or merges it, per config.
  - Findings are saved per lens, with a `review.md` summary.
- The lenses serve as 5.1's second reviewer for large and high risk, merged and deduplicated with Codex's findings.
- A PR queue source keyed `pr:<number>@<head-sha>`, so a new push is new work.

### Acceptance criteria

- [ ] A mock review of a fixture PR writes six findings files and `review.md`, one fix commit, and a PR comment (stubbed `gh`).
- [ ] A high-risk 5.1 round uses Codex plus the lenses, and the merged findings contain no duplicates.
- [ ] The same PR at the same SHA isn't queued twice; a new SHA is.
- [ ] Lint and tests pass.

### Validation

Tests with stubs, plus one real `adw review-pr` on a scratch PR, linked in the PR.

---

## Phase 8.4 — Runtime-verify phase

**Plan**: _not yet created_

**Linear**: ADW-62 (https://linear.app/ivo-tsonev/issue/ADW-62)

**Goal**: An optional phase proves UI and API changes work by exercising the running app and saving the evidence.

### What to build

- An optional `runtime-verify` phase, not in the default sequence:
  - Starts the app with `project.run_command`.
  - Exercises the changed flows for the project's platform: HTTP calls for APIs, a browser or simulator for UI.
  - Saves responses and screenshots as artifacts.
- A failure routes to a fix session and re-verifies, up to the configured attempts, then stops with a named reason.
- A plan with no runtime surface skips the phase and records why.

### Acceptance criteria

- [ ] On an API fixture project, the phase calls the changed endpoint and saves the response as evidence.
- [ ] A broken endpoint triggers exactly one fix session, then re-verification.
- [ ] A logic-only plan skips the phase with its reason recorded.
- [ ] Lint and tests pass.

### Validation

Tests with a fixture API project, plus the evidence folder from one real run, in the PR.

---

<!-- PHASES -->

## Epic-level acceptance criteria

- [ ] Labelling an ADW issue for pickup is enough to get it planned, built, reviewed and merged with nobody at the keyboard.
- [ ] Every phase merged and its acceptance criteria met
- [ ] Status row in [EPICS.md](./EPICS.md) updated to `Done`
