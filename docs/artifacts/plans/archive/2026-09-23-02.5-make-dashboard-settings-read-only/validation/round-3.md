# Adversarial Validation — Round 3

**Run:** 2026-09-23 21:20 UTC
**Plan:** 02.5-make-dashboard-settings-read-only
**Status at start:** draft
**Reviewer:** Codex (`codex-local:adversarial-review`, working tree)
**Prior rounds in scope:** validation/round-1.md, validation/round-2.md

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

No-ship: the revised plan contains an impossible acceptance check, does not test one of its critical effective-config merge rules, and only partially applies round 2’s consolidation safeguard.

Findings:
- [medium] TASK-002 rejects an API that TASK-001 requires (docs/artifacts/plans/02.5-make-dashboard-settings-read-only/tasks/TASK-002-delete-the-settings-editing-path.md:28-30)
  TASK-001 requires `has_project_file` to use `ConfigLoader.has_project_config`, while TASK-002 requires `has_project_config` to be absent from all dashboard source and tests. A literal implementation cannot satisfy both tasks, so final acceptance will fail or the prescribed implementation must be silently changed.
  Recommendation: Narrow the grep to the deleted context key and legacy call sites, or explicitly revise TASK-001 to derive `has_project_file` through another API.
- [medium] Effective-config tests omit phase-specific source precedence (docs/artifacts/plans/02.5-make-dashboard-settings-read-only/tasks/TASK-001-render-the-settings-page-from-a-read-only-settings-context.md:32-35)
  The user-tier tests cover only `enabled`, `input_files`, and `llm`. They do not prove that user-tier `lint_command`, `doc_mappings`, or ship fields are ignored, even though PhaseRunner reads those fields only from the project config. An implementation that displays specialized fields from the resolved user tier would therefore disagree with actual runs while passing every planned merge test.
  Recommendation: Add user-tier specialized fields to the fixtures and assert they remain at model defaults until supplied by the project file; cover validate, document, and ship field sourcing.
- [medium] Round-2 consolidation safeguard remains unenforced (docs/artifacts/plans/02.5-make-dashboard-settings-read-only/tasks/TASK-003-rewrite-the-settings-docs-for-the-read-only-page.md:17)
  Round 2 recommended both repointing phase 2.8 and adding an acceptance guard that detects surviving direct phase loaders. TASK-003 adds only the read-site edit. Phase 2.8’s existing criteria can still pass while `dashboard/settings.py` retains `_load_phase_file` and its duplicated merge logic, allowing the dashboard to drift from runtime after consolidation.
  Recommendation: Have TASK-003 add a phase-2.8 acceptance check proving `dashboard/settings.py` uses `load_command_config` and contains no direct YAML/Pydantic phase-config loader.

Next steps:
- Resolve the contradictory `has_project_config` acceptance grep.
- Add tests for specialized phase-field precedence.
- Complete round 2’s phase-2.8 acceptance guard before approving the plan.

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | TASK-002's grep bans `has_project_config` everywhere, but TASK-001 reads the `ConfigLoader.has_project_config` property | med | apply | A real contradiction. Narrow the grep to the quoted context key `"has_project_config"`, which is the dead code the epic names | TASK-002 |
| 2 | The merge tests don't prove that user-tier phase-specific fields (`lint_command`, `doc_mappings`, ship fields) are ignored | med | apply | A run reads those fields from the project file only, and nothing else pins that rule. One parametrized test covers validate, document and ship | TASK-001 |
| 3 | The phase-2.8 repoint has no acceptance check that 2.8 actually replaces the dashboard's loader | med | apply | Cheap to enforce: add a 2.8 criterion (and the same line in Linear ADW-24) that `src/adw/dashboard` has no `yaml.safe_load`/`model_validate` once `settings.py` uses `load_command_config`. Today every such call in the dashboard is settings code | TASK-003 |

**Round-3 stop rule.** Round 3 still produced apply rows. The shared protocol would ask the user here. The session runs autonomously ("do not stop to ask me questions, use your best judgement"), and the three findings are precise one-line fixes, not a structural flaw. So they were applied, and no fourth round was run.
