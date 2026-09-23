# Adversarial Validation — Round 2

**Run:** 2026-09-23 21:10 UTC
**Plan:** 02.5-make-dashboard-settings-read-only
**Status at start:** draft
**Reviewer:** Codex (`codex-local:adversarial-review`, working tree)
**Prior rounds in scope:** validation/round-1.md

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

No-ship: the revised plan leaves its future config-loader consolidation stale and its final screenshot validation cannot run in the documented order.

Findings:
- [medium] The promised phase-config consolidation will miss the new settings loader (docs/artifacts/plans/02.5-make-dashboard-settings-read-only/PLAN.md:89)
  The plan mitigates duplicated merge logic by claiming phase 2.8 will replace the dashboard read site. However, phase 2.8 explicitly lists `dashboard/partials.py`, while TASK-001 moves phase loading into the new `dashboard/settings.py` and TASK-003 instructs implementers to leave artifact plans alone. Following phase 2.8 as written would therefore delete or modify an obsolete read site and leave this new merge implementation behind. The duplication—and its risk of displaying phase values differently from actual runs—would become permanent precisely when phase 2.8 changes the merge rules for phase-specific fields.
  Recommendation: Add an explicit task in this plan to update phase 2.8’s read-site list from `dashboard/partials.py` to `dashboard/settings.py`, and make its acceptance criteria grep for direct phase-config loaders after consolidation.
- [medium] Final validation kills the dashboard before the required screenshots (docs/artifacts/plans/02.5-make-dashboard-settings-read-only/tasks/TASK-004-final-validation.md:37-54)
  The smoke-test recipe starts the dashboard and then executes `kill %1` at line 44. The following validation step requires screenshots “with the smoke dashboard running,” so the documented sequence cannot produce the required evidence. Additionally, the cleanup trap removes only the scratch directory; a failure before `kill %1` leaves the dashboard process running and can make retries fail on the occupied port.
  Recommendation: Capture and validate the server PID, install an EXIT trap that terminates it, perform curls and screenshots before shutdown, and explicitly stop/wait for the process only after all browser evidence is captured.

Next steps:
- Correct the phase 2.8 dependency before implementation.
- Make the smoke-and-screenshot procedure one ordered lifecycle with reliable process cleanup.

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | Epic phase 2.8 lists `dashboard/partials.py` as the dashboard read site, but after this plan the phase-config read and merge live in `dashboard/settings.py`, so 2.8 would miss the copy | med | apply | True. `phase_config_partial` is deleted here, and without the fix 2.8 would chase a site that no longer exists and leave the merge copy behind. A one-bullet epic edit fixes it | TASK-003; PLAN.md:Scope, Risks |
| 2 | TASK-004 kills the dashboard before the screenshot step that needs it running, and the trap doesn't stop the server on an early failure | med | apply | True as written. The smoke and screenshots now run as one ordered block with the server PID in the EXIT trap | TASK-004 |
