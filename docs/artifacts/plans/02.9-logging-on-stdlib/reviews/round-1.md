# Adversarial Review — Round 1

**Run:** 2026-09-24 07:07 UTC
**Branch:** feature/adw-25
**Base:** staging
**Commits reviewed:** 779ecec6..f5dfb9a4
**Reviewer:** Codex

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

# Codex Adversarial Review

Target: branch diff against staging
Verdict: needs-attention

Do not ship yet: streamed secrets can bypass redaction, and resumed runs lose their live log.

Findings:
- [high] Secrets split across stream events bypass redaction (src/adw/logging/redactor.py:239-240)
  Claude text deltas are passed to write_llm_token separately, and the filter redacts each record in isolation. If a key is split across two content_block_delta events, neither fragment matches the configured pattern; both are written to live.log and can be reconstructed. This defeats the change’s secret-redaction goal on a normal streaming path.
  Recommendation: Buffer streamed text across event boundaries before writing it, retaining enough trailing context to detect secrets spanning adjacent deltas. Test a key split across two events.
- [medium] Resume never attaches the run’s live.log handler (src/adw/cli/resume.py:130-134)
  The changed resume path calls setup_logging without a run directory, then creates the orchestrator without passing a live stream. Phase records and Claude output from resumed work therefore do not append to that run’s live.log, leaving `adw logs follow` and the dashboard without the resumed activity.
  Recommendation: After resolving the run ID, call setup_logging with its run directory and pass the returned handler to create_orchestrator. Verify resumed records and LLM output append to the existing live.log.

Next steps:
- Fix both paths and verify them with split-delta and resume integration tests.

## Triage

| # | Finding | Severity | Verdict | Rationale | Commit |
|---|---------|----------|---------|-----------|--------|
| 1 | A secret split across two `content_block_delta` events escapes per-record redaction | high | defer | `ClaudeCodeExecutor` runs `claude --print --verbose --output-format stream-json` without `--include-partial-messages`, and `claude --help` says partial chunks arrive only with that flag. So every stream-json line ADW reads is a complete assistant message, and a key cannot straddle two writes on this path. The top-level `content_block_delta` branch in `_extract_display_text` never fires today. On `staging` no LLM text was redacted at all, so this is a limitation of the new coverage, not a regression. If partial messages are ever enabled, cross-event buffering is needed: filed as a follow-up. | |
| 2 | `adw resume` writes no `live.log` for the resumed run | med | defer | PLAN.md Out of Scope ("A `live.log` for resumed runs") keeps resume console-only on purpose: `staging`'s resume writes no `live.log` either (`create_orchestrator(console)` got no run id), and giving it one is a behaviour change for Epic 03's run-loop work. The fix is small (`setup_logging(verbosity, runs_dir / run_id)` after the run resolves, then pass `live_stream`), so it is filed as a follow-up rather than rejected. | |
