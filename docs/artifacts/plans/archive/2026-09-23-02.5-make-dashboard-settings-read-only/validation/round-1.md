# Adversarial Validation — Round 1

**Run:** 2026-09-23 20:55 UTC
**Plan:** 02.5-make-dashboard-settings-read-only
**Status at start:** draft
**Reviewer:** Codex (`codex-local:adversarial-review`, working tree)
**Precondition note:** the only change outside the plan dir was the one-line `**Plan**:` link that `create-plan`'s `link_plan.py` wrote into `docs/artifacts/epics/02-cleanup-remove-and-consolidate.md`. It is part of this plan's authoring, so validation proceeded.

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

No-ship: the plan can display incorrect effective phase settings, its write-surface guard is incomplete, and its final-validation commands use an undefined path variable that can target root directories.

Findings:
- [high] Phase view does not show the effective configuration required by the epic (docs/artifacts/plans/02.5-make-dashboard-settings-read-only/PLAN.md:68-71)
  The plan defines phase values as the project file over Pydantic defaults and explicitly excludes user-tier resolution. That contradicts the epic's requirement to show effective per-phase values. Current runtime behavior resolves a command tier and incorporates its enabled, input_files, and llm settings before applying project overrides (`PhaseRunner._get_merged_config` and `is_phase_enabled`). A user-tier config can therefore affect a run while the proposed page labels model defaults as effective, misleading operators about enabled phases, inputs, or models.
  Recommendation: Apply — update PLAN.md, RESEARCH.md, TASK-001, TASK-003, and TASK-004 so the page resolves and tests the same command tier and override semantics as PhaseRunner, or obtain an explicit epic scope change before implementation.
- [medium] Final-validation commands use an undefined SCRATCH variable (docs/artifacts/plans/02.5-make-dashboard-settings-read-only/tasks/TASK-004-final-validation.md:20-35)
  The validation recipe writes to "$SCRATCH/base" and "$SCRATCH/home" without initializing SCRATCH. In a clean shell this expands to `/base` and `/home`, causing permission failures or writing into unintended root-level directories. That makes the required vulture and smoke evidence non-reproducible and potentially unsafe.
  Recommendation: Apply — change TASK-004 to create and validate an explicit temporary directory with `mktemp -d`, use that absolute path throughout, and install a cleanup trap.
- [medium] The claimed write-surface guard only detects POST routes (docs/artifacts/plans/02.5-make-dashboard-settings-read-only/PLAN.md:79)
  The plan claims the guard prevents a write endpoint from returning, but it enumerates only POST. A future PUT, PATCH, or DELETE settings endpoint would satisfy both the guard and final route-list validation while restoring dashboard writes, violating the stated invariant that configuration changes only by hand.
  Recommendation: Apply — update PLAN.md, TASK-002, and TASK-004 to guard all state-changing HTTP methods and assert that only the two explicitly allowed run mutations remain.

Next steps:
- Correct the effective-config design before implementation.
- Make the validation workspace explicit and safe.
- Broaden the mutation-route invariant beyond POST.

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | Phase view shows the project file over model defaults, not the effective values a run uses: it ignores the resolved command tier (user/bundled), whose `enabled`, `input_files` and `llm` a run merges in | high | apply | The epic asks for effective per-phase values. `PhaseRunner._get_merged_config` merges `input_files`/`llm` from the resolved tier, `is_phase_enabled` takes the tier's `enabled` unless the project file sets it explicitly, and a user-tier config does reach runs. Mirroring those rules costs about 20 lines, and 2.8 replaces both with `load_command_config` | PLAN.md:Scope, Out of Scope, Decisions, Risks; RESEARCH.md:Uncertainty; TASK-001; TASK-003 |
| 2 | TASK-004 uses `$SCRATCH` without defining it | med | apply | In a clean shell the recipe would write to `/base` and `/home`. Define it with `mktemp -d` up front | TASK-004 |
| 3 | The write-surface guard checks only POST; a PUT/PATCH/DELETE route would slip past | med | apply | The invariant is "no config writes". Assert that the only routes with a method other than GET/HEAD are the two run mutations | PLAN.md:Decisions, Acceptance Criteria; TASK-002; TASK-004 |
