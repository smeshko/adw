# Adversarial Validation — Round 1

**Run:** 2026-09-24 04:10 UTC
**Plan:** 2026-09-24-02.1-remove-the-security-package
**Status at start:** draft
**Reviewer:** Codex (`/codex-local:adversarial-review --wait --scope working-tree`)

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

```
# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

Do not approve yet: the plan’s principal absence checks are not reproducible in this working tree because they scan ignored Python bytecode.

Findings:
- [medium] Apply — absence greps scan stale ignored bytecode (docs/artifacts/plans/2026-09-24-02.1-remove-the-security-package/PLAN.md:72)
  The prescribed recursive grep currently reports matches from ignored `__pycache__/*.pyc` files. After `git rm`, bytecode under the deleted security packages can remain on disk, so the required “returns nothing” evidence can fail despite a correct source change. This also affects TASK-001, TASK-003, and TASK-004 validation. Verdict: apply — make every absence check operate only on tracked/source files.
  Recommendation: Replace the recursive greps with `git grep -n -E '<pattern>' -- src tests` or explicitly exclude `__pycache__`. Update PLAN.md, RESEARCH.md, TASK-001, TASK-003, and TASK-004 consistently.

Next steps:
- Correct the grep recipes across all affected plan artifacts, then approve the plan.
```

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | Absence greps scan stale `__pycache__/*.pyc`, so "returns nothing" can fail after a correct `git rm` | med | apply | Real: `git rm` leaves ignored bytecode behind, and GNU grep reports "Binary file … matches". Keeping `grep -rn` with `--exclude-dir=__pycache__` preserves the epic's command shape and still sees untracked files, which `git grep` would miss mid-task. | `PLAN.md:Acceptance Criteria`, `RESEARCH.md:Useful Commands`, `TASK-001`, `TASK-002`, `TASK-003`, `TASK-004` |

Self-corrections made during the apply loop (not Codex findings):

- `TASK-001` Acceptance: the residual hits after TASK-001 are only the `security_allow_dangerous` keys in `tests/unit/cli/wizard/test_security.py` and `test_summary.py`; `cli/wizard/security.py` itself has no `allow_dangerous`.
- `TASK-004`: the wizard step now names the exact stdin recipe. A planning-time probe showed piped stdin drives every prompt, and captured the before transcript (`Step 8/10: Security Settings`, `Security: Default`), so the `CliRunner` fallback is gone.
