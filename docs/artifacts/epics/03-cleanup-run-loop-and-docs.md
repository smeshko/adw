# Epic 03 — Cleanup: run-loop consolidation and docs

Status: planned
Created: 2026-09-23
Depends on: Epic 02
Project: none
Linear: ADW-6 (https://linear.app/ivo-tsonev/issue/ADW-6)
Milestone: none

## Overview

Last third of the codebase simplification. The run loop is currently spread over six classes (`Orchestrator`, `RunLifecycle`, `ResumeManager`, `RunLookup`, `RunDirectoryManager`, `InterruptionHandler`) plus the extensions plugin layer. This epic collapses them into one orchestrator with explicit phase steps, and makes Ctrl+C and abort actually work. It then rewrites the docs to describe what is left.

This is the riskiest part of the cleanup. It comes last so that the code around it is at its smallest and the tests no longer leak. Each phase is sized to land as one small-to-medium pull request, driven by a single plan under `../plans/`.

## Architecture references

- [Orchestrator deep dive](../../architecture/deep-dive/orchestrator.md): the run loop being consolidated. Stale in places; trust the code.
- [Extensions system deep dive](../../architecture/deep-dive/extensions-system.md): the plugin layer that phase 3.4 replaces. It references a `core/extensions.py` that no longer exists.
- [PhaseRunner deep dive](../../architecture/deep-dive/phase-runner.md): hook environment and artifact capture (3.4).
- [CONDITIONAL_DOCS.md](../../CONDITIONAL_DOCS.md) and [AGENTS.md](../../../AGENTS.md): rewritten in 3.5.
- [Simplification audit report](https://claude.ai/artifact/P59fUpiUcp7rATwMUSjjmp) (private): findings and call graphs for `adw run` and `adw resume`. Bug IDs `B*` refer to it.

## Dependencies

- Epic 02: dead code, inert features and duplicated helpers must be gone first, so this epic moves as little code as possible.

## Out of scope

- New run-loop features (parallel phases, new phase types).
- Changing `PhaseRunner`'s responsibilities beyond the config caching done in 2.8 and the hook-environment change in 3.4.
- Rewriting the BMAD-derived workflow prompts.

## Phase 3.1 — Resume and run-directory helpers as functions

**Plan**: _not yet created_

**Linear**: ADW-29 (https://linear.app/ivo-tsonev/issue/ADW-29)

**Goal**: Resuming a run and creating a run directory are plain functions, not manager classes.

### What to build

- Replace `ResumeManager`, `RunLookup` and `models/resume.py` (`ResumeInfo`, `ResumeStatus`) with two functions:
  - `find_resumable(runs_dir, run_id | None) -> RunContext`
  - `resume_phase(ctx, from_phase) -> str`

  Both raise `ADWError` with the existing codes `RUN_COMPLETED`, `RUN_NOT_FOUND`, `STATE_CORRUPTED` and `NO_INCOMPLETE_RUNS`.
- Move run finding and listing into `core/context_manager.py`.
- `Orchestrator.resume(ctx, from_phase)` takes the context the CLI already loaded. Today the run is loaded twice and validated three times.
- Replace `RunDirectoryManager` with `create_run_dir(runs_dir, ctx)`, which uses `ContextManager.save`. This drops the redundant non-atomic first write of `context.json`.
- Delete `PhaseRunnerProtocol` (one implementation) and the `artifacts_override` plumbing, including `_load_artifacts_from_source`. Every production path reloads the same run.
- Drop the `Orchestrator` constructor parameters that bootstrap never passes: `run_lifecycle`, `resume_manager`, `index_manager`, `max_retries`.

### Acceptance criteria

- [ ] `adw resume` on an interrupted mocked run resumes at the interrupted phase.
- [ ] Each of the four error codes is produced by a CLI-level test.
- [ ] `grep -rn "ResumeManager\|RunLookup\|RunDirectoryManager\|artifacts_override\|PhaseRunnerProtocol" src tests` returns nothing.
- [ ] `context.json` is written exactly once when a run is created (spy test).
- [ ] Lint and tests pass.

### Validation

Include CLI transcripts for resume success and each error code, from a scratch repo with prepared run directories, in the PR.

---

## Phase 3.2 — Merge RunLifecycle into the orchestrator

**Plan**: _not yet created_

**Linear**: ADW-30 (https://linear.app/ivo-tsonev/issue/ADW-30)

**Goal**: One run loop with one finish path and one place that saves run state.

### What to build

- Move the `RunLifecycle` methods into `Orchestrator` and delete `core/run_lifecycle.py`. The dependencies are held once, with no 15-kwarg forwarding.
- One `_finish(ctx, status, error=None)` replaces:
  - the two copied completion blocks (`orchestrator.py:426-459` and `645-678`)
  - the nearly identical `handle_adw_error` and `handle_exception`
- One `_save(ctx)` writes `context.json` and mirrors the index entry. It replaces the 8 hand-written index updates.
- `run`, `resume`, `run_single_phase` and `continue_from_run` share one `_run(ctx, phases)` with one try/except.
- Re-home `tests/unit/core/test_run_lifecycle.py` onto the orchestrator. Do this in a first commit, before moving code, so the tests prove behaviour is unchanged.

### Acceptance criteria

- [ ] A golden test records the ordered side effects (context save, index update, label, comment, snapshot) for a successful run, a failed run and a single-phase run on the pre-merge code, and still passes after the merge.
- [ ] `core/run_lifecycle.py` is gone, and `orchestrator.py` holds a single `_finish` and a single `_save`.
- [ ] `scripts/preflight.sh` and the full suite pass.
- [ ] Lint and tests pass.

### Validation

Run a mocked full pipeline and a failing mocked run in a scratch repo, both before and after the change. Include a diff of their `context.json` and index entries (only timestamps and IDs should differ) in the PR.

---

## Phase 3.3 — Interrupts and aborts that stop the run

**Plan**: _not yet created_

**Linear**: ADW-31 (https://linear.app/ivo-tsonev/issue/ADW-31)

**Goal**: Ctrl+C saves the live state and abort actually stops the running process.

### What to build

- Replace `InterruptionHandler`'s shutdown path, which never fires, with `except KeyboardInterrupt` in the run loop. The handler finishes the live context, not a stale copy, as `interrupted` at the phase that was running (B14). A SIGTERM handler raises `KeyboardInterrupt`. Keep `abort_gracefully` as a plain function; the rest of `interruption.py` goes.
- One core `abort_run(run_id)`, used by `cli/abort.py` and `dashboard/mutations.py`. It validates the run, then sends SIGTERM to the PID in the concurrent-run lock file, and the run finishes itself as `aborted`. Today abort only rewrites `context.json`, and the running process later overwrites it (B13).
- `IndexManager.update_run` takes a file lock around its read-modify-write of `~/.adw/index.jsonl` (B19).

### Acceptance criteria

- [ ] Ctrl+C during the build phase of a mocked slow run leaves `context.json` with status `interrupted` and phase `build`. `adw resume` then restarts build, not plan.
- [ ] `adw abort <id>` on a running mocked run makes the process exit within 10 s with final status `aborted`, and the status stays `aborted`.
- [ ] A dashboard abort behaves the same way.
- [ ] Two processes each updating the index 100 times concurrently lose no entries.
- [ ] Lint and tests pass.

### Validation

Include a scratch-repo transcript of Ctrl+C then resume, and of abort from the CLI and from the dashboard (screenshot). Include the concurrent-index test output. All of these run against a mocked executor that sleeps per phase.

---

## Phase 3.4 — Extensions as explicit phase steps

**Plan**: _not yet created_

**Linear**: ADW-32 (https://linear.app/ivo-tsonev/issue/ADW-32)

**Goal**: Phase-specific behaviour is plain functions called at explicit points, not a plugin registry.

### What to build

- Delete `core/extensions/`: `base.py`, `registry.py`, `build.py`, `document.py`, `ship.py` and `__init__.py`. That is 3 built-in extensions behind a 4-hook Protocol and a registry, with 6 of the 12 hook methods being no-op stubs.
- Replace them with plain functions called at explicit points in the run loop and the phase runner, each wrapped in the existing non-blocking try/except:
  - `capture_build_diff` (in `adw/git.py`)
  - `create_pr` (from 1.7)
  - `ship_skip_reason`
  - `ship_hook_env`
  - `post_merge_cleanup`
- Fold the `isinstance(ShipCommandConfig)` branch in `phase_runner` into `ship_hook_env`. Replace the `os.environ` mutate-and-restore around hooks with an `extra_env` argument to `run_hook`.
- Drop the `pr_description.md` extra artifact, which is byte-identical to `document_output.md`, and have `adw pr` read `document_output.md`.
- Verify and fix the `merge_record.json` lookup. `post.sh` writes it to `$ADW_ARTIFACTS_DIR` in the main project, but the extension looks under the worktree, so post-merge cleanup probably never runs.

### Acceptance criteria

- [ ] `grep -rn "extensions" src/adw/core` returns nothing.
- [ ] A mocked build still writes the diff artifacts.
- [ ] A mocked document step still creates a PR and sets `context.pr_url`.
- [ ] A mocked ship with a fake `gh` that reports a merge runs post-merge cleanup: the worktree is removed and the base branch is pulled.
- [ ] The ship hook receives the `ADW_SHIP_*` variables through `extra_env`, and `os.environ` is unchanged after the hook.
- [ ] Lint and tests pass.

### Validation

Include the integration tests for each step, with a fake `gh`/`git` on PATH, and a real scratch-repo run through ship with a local bare remote, showing the worktree cleaned up after merge.

---

## Phase 3.5 — Rewrite architecture docs, README and agent guide

**Plan**: _not yet created_

**Linear**: ADW-33 (https://linear.app/ivo-tsonev/issue/ADW-33)

**Goal**: The docs describe the simplified codebase, and every doc reference points at a file that exists.

### What to build

- Merge `docs/architecture/deep-dive/*.md` (7 files) into one `docs/architecture.md` describing:
  - the single run loop
  - phases and their explicit steps
  - hooks, config loading and template rendering
- Merge the 21 `docs/features/*.md` story write-ups into one `docs/dashboard.md`, keeping `design-system-brutalist.md` alongside if still useful.
- Point ADW's own document phase (`doc_mappings` in `.adw/commands/document/config.yaml`) at the new structure, so `docs/features/` doesn't regrow.
- Replace `docs/CONDITIONAL_DOCS.md` with a short table that references only existing files, or fold it into `AGENTS.md`. Today it has 14 dead links and no deep-dive references.
- Delete the completed and stale docs: `docs/testing/TEST_REDUCTION_PLAN.md`, `docs/analysis/validation-phase-redesign.md` and `docs/development/tech-debt/`.
- Expand `README.md` from 196 bytes to about 60 lines: what ADW is, install, `adw init`, `adw run`, the phases, config files, the dashboard, and links.
- Update `AGENTS.md` to match the code:
  - the config hierarchy without `PhaseConfig`
  - how command variables reach templates
  - the removed packages and gotchas

### Acceptance criteria

- [ ] A link check (script in the PR) finds every relative link in `docs/`, `README.md` and `AGENTS.md` resolves.
- [ ] `grep -rnE "RunLifecycle|ResumeManager|ExtensionRegistry|SecurityInterceptor|PortAllocator|adw\.webhook|adw\.validation|PhaseConfig\b" --exclude-dir=artifacts docs README.md AGENTS.md` returns nothing.
- [ ] `docs/` contains no more than 8 files, excluding `docs/artifacts/`.
- [ ] Lint and tests pass.

### Validation

Include the link-check output, the grep, and `find docs -type f -not -path 'docs/artifacts/*' | wc -l` in the PR.

---

<!-- PHASES -->

## Epic-level acceptance criteria

- [ ] Every phase merged and its acceptance criteria met
- [ ] Status row in [EPICS.md](./EPICS.md) updated to `Done`
- [ ] `src/adw/core/` contains only `orchestrator.py`, `phase_runner.py`, `context_manager.py`, `artifact_manager.py`, `snapshot_manager.py`, `index_manager.py`, `stats_aggregator.py`, `project_registry.py`, `run_trigger.py` and `constants.py`
- [ ] One real `adw run`, using the real Claude CLI on a trivial feature in a scratch GitHub repo, completes all five phases and merges its PR
- [ ] `src/adw` is at or below ~33k lines (47k at `cdb2003f`). If not, the final PR explains the gap
