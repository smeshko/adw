# Adversarial Validation — Round 1

**Run:** 2026-09-24 04:55 UTC
**Plan:** 02.6-collapse-init-wizard
**Status at start:** draft
**Reviewer:** Codex (`/codex-local:adversarial-review`, working tree)

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

Do not implement this plan yet. Two prescribed implementations conflict with strict typing, the dependency graph is incomplete, and the core no-write-on-interrupt guarantee is neither supported by the retained writer nor adequately validated.

Findings:
- [high] Interrupts can leave files behind while the CLI claims nothing was written (docs/artifacts/plans/02.6-collapse-init-wizard/tasks/TASK-005-report-honestly-whether-files-were-written.md:18-24)
  Verdict: apply. TASK-005 changes SIGINT to raise SystemExit(130) but retains atomic_write_config unchanged. The current writer catches only OSError (src/adw/cli/wizard/summary.py:405-471), records newly created paths only after write_text returns, and performs no rollback for SystemExit. An interrupt during writing can therefore leave partial or overwritten configuration; an interrupt after writing but during registration can leave complete files while the global handler prints "No files created." The proposed SIGINT smoke checks only the exit code, so it cannot detect this false report.
  Recommendation: Apply — update PLAN.md, TASK-005, and TASK-006 to require rollback/state-aware interrupt handling and filesystem assertions for interruption during and immediately after writing, or weaken the no-write guarantee and message.
- [medium] The prescribed detector expression fails mypy strict typing (docs/artifacts/plans/02.6-collapse-init-wizard/tasks/TASK-001-detect-the-language-and-test-command-with-projecttypedetector.md:12-15)
  Verdict: apply. ProjectTypeDetector.get_defaults returns dict[str, str | None] (src/adw/config/detector.py:120-129), so the specified indexed language expression has type str | None. Passing it to _prompt_language, whose detected parameter is str (src/adw/cli/wizard/basics.py:170-183), will fail the repository's mandatory mypy --strict gate if implemented literally.
  Recommendation: Apply — change TASK-001 to require explicit narrowing, such as detector.get_defaults(detector.detect(root))["language"] or "unknown", with the resulting variable typed as str.
- [medium] The proposed step list has incompatible callable signatures (docs/artifacts/plans/02.6-collapse-init-wizard/tasks/TASK-004-replace-the-flow-controller-and-wizardstate-with-run-wizard.md:12-25)
  Verdict: apply. TASK-004 requires one iterable of step callables, but basics takes (console, root) while every other step takes only console. A direct heterogeneous tuple list followed by step(console) produces an unsafe callable union under strict mypy. The plan identifies the signature exception but provides no adapter or alternate invocation design.
  Recommendation: Apply — update TASK-004 to define a homogeneous Callable[[Console], dict[str, Any]] list, adapting basics with a typed wrapper/partial, or call basics separately before iterating the remaining steps.
- [medium] TASK-004 omits its real dependency on TASK-001 (docs/artifacts/plans/02.6-collapse-init-wizard/tasks/TASK-004-replace-the-flow-controller-and-wizardstate-with-run-wizard.md:1-4)
  Verdict: apply. TASK-001 explicitly preserves run_basics_step's state-bearing signature until TASK-004, while TASK-004 removes that parameter and rewrites its tests. Nevertheless, TASK-004 declares dependencies only on TASK-002 and TASK-003. A dependency-driven executor may run TASK-004 first, after which TASK-001's signature and test instructions are stale, contradicting PLAN.md's claim that task order keeps every commit green.
  Recommendation: Apply — add TASK-001 to TASK-004's Depends on list and reflect the same dependency in PLAN.md.
- [medium] Final validation does not provide one-to-one coverage of the plan criteria (docs/artifacts/plans/02.6-collapse-init-wizard/tasks/TASK-006-final-validation.md:10-17)
  Verdict: apply. TASK-006 explicitly checks the full suite, one reduced symbol grep, accept/decline transcripts, and a SIGINT exit code. It does not name final evidence for partial-write failure behavior, detector-default parity, removal of retry and ship-build prompts, or the customized ship serialization path. Its generic "all acceptance criteria met" checkbox is not an auditable acceptance matrix, and its grep omits the stronger symbol sets defined in TASK-002 through TASK-004.
  Recommendation: Apply — expand TASK-006 with one checkbox per PLAN.md acceptance criterion, naming the exact test, grep or transcript and expected result; include interruption filesystem state and customized ship YAML serialization.

Next steps:
- Correct the two strict-typing recipes and TASK-004 dependency metadata.
- Resolve the interrupt/write transaction guarantee before retaining any "nothing was written" message.
- Turn TASK-006 into an explicit acceptance-to-evidence matrix.

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | SIGINT during the write or dashboard registration can leave files behind while the handler prints "No files created" | high | apply | Real: `atomic_write_config` rolls back only on `OSError`, and the `SystemExit` from the SIGINT handler skips it; the plan would make that false claim exit 130 and call it honest. Hold off SIGINT across write + registration so an interrupt lands before the write or not at all. | PLAN.md:Scope, Out of Scope, Decisions, Acceptance Criteria; TASK-005; TASK-006 |
| 2 | `get_defaults(...)["language"]` is `str \| None`, which fails `mypy --strict` where `_prompt_language` takes `str` | med | apply | Correct: `DEFAULTS` is `dict[str, dict[str, str \| None]]`. | TASK-001 |
| 3 | The `(section, title, step)` list mixes `run_basics_step(console, root)` with `(console)` steps | med | apply | The plan gives no typed adapter; name one. | TASK-004 |
| 4 | TASK-004 omits its dependency on TASK-001 | med | apply | TASK-001 keeps `run_basics_step`'s `state` for TASK-004 to remove, so the order matters. | TASK-004; PLAN.md:Tasks |
| 5 | TASK-006 has no one-to-one acceptance-to-evidence checks | med | apply | Its generic checkbox cannot be audited; list each PLAN.md criterion with its test, grep or transcript. | TASK-006 (matrix); TASK-004 (+`test_customized_ship_commands_reach_ship_config`) |
