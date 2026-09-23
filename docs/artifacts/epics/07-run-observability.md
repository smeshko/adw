# Epic 07 — Run observability from Loop

Status: planned
Created: 2026-09-23
Depends on: Epic 03
Project: none
Linear: ADW-36 (https://linear.app/ivo-tsonev/issue/ADW-36)
Milestone: none

## Overview

Brings over the observability design of the Sunrise hackathon loop (`.agents/loop`). An autonomous pipeline is only trustworthy if every run can be reconstructed after the fact and stops loudly when something breaks. After this epic:

- Every run writes one typed event stream. The terminal, `live.log`, a rolling `summary.json` and the dashboard are all derived from it.
- Failures have distinct outcomes, so model errors, timeouts and no-progress no longer blur into one.
- Each phase's tool policy is enforced on every tool call, and each decision is recorded.
- A phase can fall back to a second model.

The loop's weak spots are left behind: it swallowed model errors, treated a timeout as no progress, and wiped its event file on resume.

## Architecture references

- [Orchestrator deep dive](../../architecture/deep-dive/orchestrator.md) and [PhaseRunner deep dive](../../architecture/deep-dive/phase-runner.md): where events are emitted. Epic 03 restructures both; trust the code.
- [AGENTS.md](../../../AGENTS.md): the test rules for the new hook and consumers.
- The loop's source, under `/Users/A1E6E98/Developer/rewe/software-factory/DTGS-Sunrise%20Mobile%20App/.agents/loop/` (outside this repo):
  - `engine/types.ts`: the `LoopEvent` union and the `run:start` roster.
  - `engine/event-bus.ts`, `engine/consumers/{jsonl,summary,terminal}.ts`: consumers, chunk coalescing, the rolling summary.
  - `engine/policy.ts` and `stage-worker.ts`: the per-stage policy gate and fallback-model switch.
  - `serve.ts`: replay-then-tail streaming.

## Dependencies

- Epic 03 (ADW-6): one run loop to emit from.
- Phase 1.6 (ADW-12): a Claude failure already fails the phase; 7.2 turns that into typed outcomes.
- Phase 2.1 (ADW-17): the inert security package is gone; 7.3 is its working replacement, and carries ADW-1's intent.
- Phase 2.9 (ADW-25): stdlib logging; `live.log` becomes an event consumer on top of it.

## Out of scope

- Queue and daemon events: Epic 08.
- Plan-workflow semantics. The task and round events defined here are emitted by Epic 05's phases once both land.

## Phase 7.1 — Typed event stream and summary.json

**Plan**: _not yet created_

**Linear**: ADW-54 (https://linear.app/ivo-tsonev/issue/ADW-54)

**Goal**: Every run writes a typed events.jsonl that the terminal, live.log and a rolling summary.json are built from.

### What to build

- An `adw.events` module:
  - Typed event models:
    - `run:start`, carrying the roster: configured phases, tasks when known, models, policies, limits.
    - `run:resume`, `run:end`.
    - `phase:start/end`, `task:start/end`, `round:start/end`, `finding:triaged`.
    - `tool:start/end`, `usage`, `error:*`.
  - A bus that never lets a consumer failure break the run.
  - Consumers:
    - `events.jsonl` writer that merges consecutive text chunks and flushes on pause.
    - `summary.json`, rewritten at every phase end and carrying a `version` field.
    - Terminal renderer.
    - `live.log` writer.
- The executor maps Claude Code `stream-json` lines (assistant text, thinking, `tool_use`, `tool_result`, result and usage) to events.
- Resume appends to `events.jsonl`, never truncates it, and emits `run:resume`.

### Acceptance criteria

- [ ] A mock run's `events.jsonl` has `run:start` listing every configured phase before the first `phase:start`.
- [ ] `summary.json` exists after every phase and after an interrupted run.
- [ ] Resuming keeps every prior event; the line count only grows.
- [ ] Nothing outside the `live.log` consumer writes to `live.log` (grep).
- [ ] Lint and tests pass.

### Validation

Tests per criterion, plus an excerpt of `events.jsonl` and `summary.json` from a real run in the PR.

---

## Phase 7.2 — Failure outcomes and circuit breakers

**Plan**: _not yet created_

**Linear**: ADW-55 (https://linear.app/ivo-tsonev/issue/ADW-55)

**Goal**: Model errors, timeouts, no-progress and crashes are distinct outcomes, and caps stop runaway runs.

### What to build

- Outcomes for phases, tasks and sessions: `passed`, `failed`, `model_error`, `timeout`, `no_progress`, `crash`.
  - `model_error` carries the API error text from the `stream-json` result (`is_error`, `subtype`).
  - `no_progress` means the plan directory and `HEAD` are unchanged after a task or fix session.
  - Each outcome is emitted as an event with a suggestion line, and maps to a stop reason from 6.1.
- `usage` events include cache-read and cache-creation tokens and the reported cost; `summary.json` totals include them.
- Configurable caps:
  - maximum agent sessions per run;
  - maximum fix attempts per task and per review round;
  - a per-phase timeout that kills the session's process group.

### Acceptance criteria

- [ ] A fake `claude` returning an API error result produces `model_error`, with the message in the events and in `context.json`.
- [ ] A session that outlives its timeout ends as `timeout` within timeout + 5 s, with no process from its group left.
- [ ] A task session that changes nothing twice stops the run with `no-progress`.
- [ ] Token totals in `summary.json` equal the sum of the `usage` events, cache fields included.
- [ ] Lint and tests pass.

### Validation

Tests with fake `claude` binaries on `PATH`, plus the events of one forced `model_error` run in the PR.

---

## Phase 7.3 — Per-phase tool policy

**Plan**: _not yet created_

**Linear**: ADW-56 (https://linear.app/ivo-tsonev/issue/ADW-56)

**Goal**: Each phase's allowed writes and commands are enforced on every tool call by a Claude Code hook, and every decision is recorded.

### What to build

- A `policy:` block in phase config:
  - `write_paths`: glob patterns.
  - `commands`: an allowlist with `*` suffixes.
- Global denies:
  - `rm -rf`, `git push --force`, `git reset --hard`, `git clean -f`, `git branch -D`, `sudo`, `curl | sh`;
  - reading `.env` files.
- A `PreToolUse` hook that ADW injects into each session through `--settings`:
  - It asks `adw.policy` for a decision and returns allow or deny with a reason.
  - It appends a `tool:allowed` or `tool:denied` event to the run's `events.jsonl`.
- The plan settles whether `--dangerously-skip-permissions` can stay with the hook in force, or must give way to a permission mode. Either way, a denial must actually block the call.
- Each phase's policy appears in the `run:start` roster, so a denial can be explained without reading config.

### Acceptance criteria

- [ ] A session attempting `git push --force` is blocked, and a `tool:denied` event names the rule.
- [ ] A write outside `write_paths` is blocked, and one inside is allowed.
- [ ] Reading `.env` is blocked.
- [ ] Every tool call in a mock run has exactly one allow or deny event.
- [ ] Lint and tests pass.

### Validation

Tests driving the hook script directly, plus one real session with a forbidden command, whose denial event appears in the PR.

---

## Phase 7.4 — Dashboard on the event stream

**Plan**: _not yet created_

**Linear**: ADW-57 (https://linear.app/ivo-tsonev/issue/ADW-57)

**Goal**: The dashboard replays a run from its events and keeps following it live, down to tasks and review rounds.

### What to build

- The run page replays `events.jsonl`, then follows it live (SSE). Finished and running runs share one code path.
- The pipeline is drawn from the `run:start` roster before any phase starts.
- Drill-down: phase → task → review round → tool calls. Denials and failure outcomes are highlighted with their suggestion.
- The runs list reads `summary.json` only.
- Remove the dashboard's `live.log` text parsing.

### Acceptance criteria

- [ ] A finished run's page shows the same timeline as the one recorded while it ran (test compares the rendered event lists).
- [ ] A running run's page shows a new event within 2 s.
- [ ] The runs index renders without opening any `events.jsonl`.
- [ ] Lint and tests pass.

### Validation

Tests with fixture event files, plus a screen recording of a live run and its replay, linked in the PR.

---

## Phase 7.5 — Per-phase fallback model

**Plan**: _not yet created_

**Linear**: ADW-58 (https://linear.app/ivo-tsonev/issue/ADW-58)

**Goal**: A phase switches to its fallback model on provider errors, and the run records which model did the work.

### What to build

- `llm.fallback_model` in phase config, next to `llm.model`.
- On a `model_error` classed as provider-side (overloaded, rate limited, 5xx, content filter), the session reruns once on the fallback model.
- A `model:switched` event records why, and `summary.json` records the model that ran each phase and task.
- Any other error leaves the model alone and follows 7.2.

### Acceptance criteria

- [ ] A fake `claude` that reports "overloaded" on model A reruns on model B, emits `model:switched`, and the phase passes.
- [ ] A non-provider error does not switch models.
- [ ] `summary.json` names the model per phase.
- [ ] Lint and tests pass.

### Validation

Tests with fake `claude` binaries, plus the summary of one run that switched models, in the PR.

---

<!-- PHASES -->

## Epic-level acceptance criteria

- [ ] Any finished run can be replayed from its `events.jsonl` alone, down to each tool call, denial, failure outcome and model used.
- [ ] Every phase merged and its acceptance criteria met
- [ ] Status row in [EPICS.md](./EPICS.md) updated to `Done`
