# Adversarial Validation — Round 3

**Run:** 2026-09-24 04:30 UTC
**Plan:** 2026-09-24-02.1-remove-the-security-package
**Status at start:** draft
**Reviewer:** Codex (`/codex-local:adversarial-review --wait --scope working-tree`)
**Prior rounds in scope:** validation/round-1.md, validation/round-2.md

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

```
# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

Do not ship the plan yet. The prior grep and self-dependency fixes are sufficient, but final validation can run against the wrong checkout, omits two removal targets, and TASK-003 contradicts the repository’s test policy.

Findings:
- [high] Functional validation can exercise the main checkout instead of this worktree (docs/artifacts/plans/2026-09-24-02.1-remove-the-security-package/tasks/TASK-004-final-validation.md:18-21)
  The validate, dashboard, and removed-option checks invoke bare `adw`, while only the wizard check is pinned with `uv run --project "$WORKTREE"`. In this environment, bare `adw` imports `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw`, not this worktree. The legacy-config check can therefore falsely pass against the old model, and the dashboard/CLI evidence does not validate the implementation being shipped.
  Recommendation: Define the implementation checkout explicitly and run every scratch functional check—including `validate`, `dashboard web`, registration/setup, and `run --allow-dangerous`—through `uv run --project "$WORKTREE" adw ...`.
- [medium] Final absence validation omits two explicitly removed surfaces (docs/artifacts/plans/2026-09-24-02.1-remove-the-security-package/tasks/TASK-004-final-validation.md:15-16)
  The final grep excludes literal `allow-dangerous` and `security_interceptor`, although the plan requires removing the help example and executor plumbing. TASK-001 checks both only at an intermediate point; the final command and the CLI exit check can still pass with stale help text or a dormant interceptor attribute left behind.
  Recommendation: Add `allow-dangerous` and `security_interceptor` to the PLAN and final-validation absence grep, while retaining the epic’s literal command as separate evidence. Escape `adw\.security` consistently.
- [medium] TASK-003 preserves tests that ADR-001 requires deleting (docs/artifacts/plans/2026-09-24-02.1-remove-the-security-package/tasks/TASK-003-remove-the-wizard-security-step.md:18-34)
  The task updates the expected enum list and exact `STEP_SEQUENCE` count, then deliberately uses those assertions as RED tests. These are the enum-existence/count tests that ADR-001 classifies as waste and that AGENTS.md says not to write. The change therefore perpetuates fragile test churn instead of following the repository’s mandatory testing strategy.
  Recommendation: Delete `test_step_values_exist` and the enum/count-only `test_step_sequence_defined` instead of editing them. Use the summary behavior test and end-to-end wizard transcript as removal evidence.

Next steps:
- Pin every functional validation command to the implementation worktree.
- Broaden the final absence check to cover all removed runtime and CLI surfaces.
- Revise TASK-003 to remove the prohibited enum/count tests, then rerun adversarial validation.
```

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | Functional checks call bare `adw`, which runs another checkout's code | high | apply | Verified: `which adw` is a separate install, not this worktree. Every functional check now runs `uv run --project "$WORKTREE" adw …`. | `PLAN.md:Acceptance Criteria`, `TASK-004` |
| 2 | The final absence grep omits `allow-dangerous` and `security_interceptor` | med | apply | Both are removal targets checked only mid-plan. The plan grep now includes them and escapes `adw\.security`; the epic's literal grep stays as separate evidence. | `PLAN.md:Acceptance Criteria`, `TASK-003`, `TASK-004` |
| 3 | TASK-003 edits enum-existence and count tests that ADR-001 calls waste | med | apply | Verified against ADR-001's "Enum Existence Tests" row. TASK-003 deletes them instead; the flipped summary assertion stays as RED, and the wizard transcript is the end-to-end evidence. | `PLAN.md:Risks`, `TASK-003` |

Round 3 still produced `apply` rows. The protocol hands that call to the user; the user asked for a fully autonomous run, so the call made here is **apply and stop**: all three findings concern validation mechanics and test hygiene, not the plan's structure, and no fourth round runs.
