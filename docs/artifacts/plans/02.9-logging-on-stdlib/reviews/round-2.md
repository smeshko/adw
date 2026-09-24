# Adversarial Review — Round 2

**Run:** 2026-09-24 07:10 UTC
**Branch:** feature/adw-25
**Base:** staging
**Commits reviewed:** 779ecec6..f5dfb9a4
**Prior rounds in scope:** reviews/round-1.md
**Reviewer:** Codex

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

# Codex Adversarial Review

Target: branch diff against staging
Verdict: needs-attention

Do not ship yet. Both round-1 findings remain deferred, not fixed. The partial-message rationale supports deferring the split-delta finding for the current Claude invocation, but resumed work still disappears from live.log. Removing the file lock also leaves concurrent continuations able to corrupt that log.

Findings:
- [medium] Resumed work remains absent from live.log (src/adw/cli/resume.py:130-134)
  The triage calls this out of scope, but `resume` still configures console-only logging and creates the orchestrator without a live stream. A resumed phase therefore appends neither phase records nor Claude output to the run’s live.log. `adw logs follow` and the dashboard miss the activity needed to diagnose a failed resume.
  Recommendation: After resolving the run ID, attach its live.log handler and pass that handler to create_orchestrator. Verify that resumed records and LLM output append to the existing file.
- [medium] Concurrent continuations have no coordinated live.log writer (src/adw/logging/live_stream.py:75-86)
  The new handler uses an in-process lock and keeps the file open for appends. `adw run --phase … --from-run <id>` reuses a run directory, and `continue_from_run` has no exclusive-run guard, so two processes can write the same live.log. Large writes can interleave, damaging entries consumed by log readers; the previous writer used a per-file lock.
  Recommendation: Either enforce exclusive ownership of a run before continuation or retain cross-process coordination for live.log writes. Test two processes continuing the same run.

Next steps:
- Fix resumed-run logging or explicitly accept the loss of its diagnostic record as a release risk.
- Enforce one active writer per run or verify cross-process append safety under concurrent continuations.

## Triage

Codex accepted the round-1 #1 deferral ("The partial-message rationale supports deferring the split-delta finding for the current Claude invocation").

| # | Finding | Severity | Verdict | Rationale | Commit |
|---|---------|----------|---------|-----------|--------|
| 1 | Resumed work still writes nothing to `live.log` (round-1 #2 again) | med | defer | Unchanged from round 1. `staging`'s `adw resume` also writes no `live.log`, so nothing regresses. PLAN.md's Out of Scope keeps resume console-only. Phase 3.1 (ADW-29) rewrites resume as plain functions and is the natural place to attach the run's handler. Filed as a follow-up linked to ADW-29. | |
| 2 | Two processes continuing one run (`--from-run`) can interleave `live.log` writes without the old per-line `FileLock` | med | reject | Removing that lock is an explicit acceptance criterion of epic 02 phase 2.9 ("the per-line file lock is gone"). `live.log` is opened in append mode (`O_APPEND`), and each line goes out as one flushed `write()`, so lines from separate processes land whole on a local filesystem. Two processes continuing the same run at once is not a supported mode: they would share one worktree and race on `context.json`'s phase state regardless of how `live.log` is written. A run-level exclusive guard belongs with the run-loop work in Epic 03, not in the logging layer. | |
