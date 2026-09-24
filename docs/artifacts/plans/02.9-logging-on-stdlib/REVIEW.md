# Review Summary — 02.9-logging-on-stdlib

**Rounds:** 2 (Codex)
**Fix commits:** none: both rounds produced only deferrals and a rejection

## Rounds

| Round | Findings | Fixed | Deferred | Rejected |
|-------|----------|-------|----------|----------|
| 1     | 2        | 0     | 2        | 0        |
| 2     | 2        | 0     | 1        | 1        |

Round 2's first finding restates round 1's second, so the review raised three distinct findings in all.

## Fixes

None.

## Deferred

- (round 1, finding 1) **A secret split across two `content_block_delta` events escapes per-record redaction.** `ClaudeCodeExecutor` runs Claude Code without `--include-partial-messages`, so every stream-json line ADW reads is a complete assistant message and a key can't straddle two writes on this path. Codex accepted this rationale in round 2. On `staging` no LLM text was redacted at all. Filed as **ADW-70** in case partial messages are ever enabled.
- (round 1, finding 2; round 2, finding 1) **`adw resume` writes nothing to the run's `live.log`.** The same was true on `staging`, and PLAN.md's Out of Scope keeps resume console-only. Phase 3.1 (ADW-29) rewrites resume and is the place to attach the run's handler. Filed as **ADW-69**, related to ADW-29.

## Rejected

- (round 2, finding 2) **Two processes continuing one run can interleave `live.log` writes without the old per-line `FileLock`.** Removing that lock is one of the phase's acceptance criteria. `live.log` is opened in append mode and each line goes out as one flushed `write()`, so lines from separate processes land whole. Two processes continuing one run at once is not a supported mode: they would share a worktree and race on `context.json` regardless. A run-level exclusive guard belongs with Epic 03's run-loop work.
