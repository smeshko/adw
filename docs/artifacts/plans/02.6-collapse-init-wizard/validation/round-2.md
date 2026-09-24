# Adversarial Validation — Round 2

**Run:** 2026-09-24 05:20 UTC
**Plan:** 02.6-collapse-init-wizard
**Status at start:** draft
**Prior rounds in scope:** validation/round-1.md
**Reviewer:** subagent (`general-purpose`, same adversarial framing and focus text). Codex started the round but hit its usage limit after 1m 25s (job `review-muf1xoiw-ktoey5`, phase `failed`); its partial output, which reported "No material findings" before the turn failed, is not a review and is not triaged.

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

Codex (failed, usage limit) printed:

> # Codex Adversarial Review
> 
> Target: working tree diff
> Verdict: needs-attention
> 
> I’m using the repository’s code-review skill because this is a working-tree review. Its required two-axis parallel review is now checking plan/spec completeness and repository standards independently while I trace the high-risk interrupt and validation paths.
> 
> No material findings.

Subagent review (the round of record):

# Adversarial Review — Round 2 (subagent)
Verdict: needs-attention

All five round-1 applies landed and are sound (the `or "unknown"` narrowing matches `DEFAULTS: dict[str, dict[str, str | None]]`; the lambda-adapted step list type-checks; dependencies are acyclic; TASK-006 now has a row per PLAN.md criterion; the retry block/uncomment round-trip and the ship-merge removal work against current code). But four issues block approval: the scratch-repo transcripts would exercise the main checkout's `adw` (on `staging`), not this worktree; TASK-004's blanket deletion of `TestStateIntegration` classes removes the only B17 regression test; TASK-001's `requirements.txt` RED claim is false; and the detector switch silently regresses `build.gradle.kts` detection. Several smaller factual claims are also wrong (notably: EOF today already exits 1 with "Aborted.", not a traceback).

Findings:
- [medium] Scratch-repo transcripts run the main checkout's `adw`, not this branch (tasks/TASK-006-final-validation.md:15; RESEARCH.md:61; TASK-005:44; PLAN.md:70-73)
  `which adw` resolves to a shim whose interpreter imports `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/__init__.py` — the editable install of the main checkout, which is on `staging`. The worktree's own `uv run` imports `.worktrees/adw-22/src/adw`. So a bare `adw init --wizard` in a scratch dir would record today's behaviour ("Wizard Complete!", exit 0 on decline, exit 0 on SIGINT), contradicting the evidence the plan expects, and the PR would carry transcripts of code not in it.
  Recommendation: apply — name the binary explicitly (e.g. `/…/.worktrees/adw-22/.venv/bin/adw`, which exists, or `uv run --project <worktree> adw …`) in RESEARCH.md "Useful Commands", TASK-005 Evidence and TASK-006 step 4; prefer the `.venv/bin/adw` path for the SIGINT transcript so `uv`'s signal forwarding is not in the picture.

- [medium] TASK-004 deletes the only B17 regression test (tasks/TASK-004-…:41)
  The instruction deletes every `TestStateIntegration` class as "state storage". But `tests/unit/cli/wizard/test_task_manager.py:306-333` `TestStateIntegration::test_accepted_defaults_yield_ship_mapping` runs the real mapping prompts + generator and validates with `ProjectConfig.model_validate`; it is the only test mentioning B17 (added in f7506a4e, #204). Likewise `test_basics.py::TestStateIntegration::test_full_flow_returns_complete_config` is a behaviour test, not state storage. Only `test_config_stored_via_flow_controller_pattern` and `test_config_can_be_stored_in_state` are the ADR-001 state-storage tests.
  Recommendation: apply — in TASK-004, delete only those state-storage tests; keep `test_accepted_defaults_yield_ship_mapping` (moved to a plain `cfg` dict `{"basics": …, "task_manager": …}`) and `test_full_flow_returns_complete_config`.

- [medium] TASK-001's `requirements.txt` RED claim is false, and the test can't distinguish detection from fallback (tasks/TASK-001-…:20, 25, 30, 36)
  Running today's `run_basics_step` with `Confirm.ask`→True and `Prompt.ask`→its default in a dir with only `requirements.txt` returns `python`/`pytest`, identical to the detector: the wizard detects "unknown", skips confirmation, and `_prompt_language`'s fallback default is `"python"` (basics.py:206). Only the java and php cases fail today, so the Step "the requirements.txt, java and php cases fail" is unreproducible and the acceptance "with requirements.txt … the wizard detects python" is not actually verified.
  Recommendation: apply — in TASK-001, have the parametrized test also assert the detection prompt was shown (`Confirm.ask` called once with `Language detected: python`), which makes the `requirements.txt` case genuinely RED today.

- [medium] Switching to `ProjectTypeDetector` drops `build.gradle.kts` (and `setup.cfg`) detection, unacknowledged (tasks/TASK-001-…:12-15; RESEARCH.md:31-38; PLAN.md:43)
  The wizard's `LANGUAGE_MARKERS["java"]` includes `build.gradle.kts` (basics.py:39); the detector's `MARKERS["java"]` is only `build.gradle`, `pom.xml` (detector.py:43). After TASK-001, a Kotlin-DSL Gradle project detects as "unknown" and, accepting defaults, writes `language: python`, `test_command: pytest`. The RESEARCH drift table lists `setup.cfg` but not `.kts`, so this regression was never weighed. (`setup.cfg`-only projects land on python via fallback, so only `.kts` is a real behaviour loss.)
  Recommendation: apply — in TASK-001, add `build.gradle.kts` (and `setup.cfg`) to `ProjectTypeDetector.MARKERS` (fixes minimal init too) with a parametrized case each; or record the loss under Decisions in PLAN.md and the RESEARCH drift table.

- [low] The hold-off window ends before the success message, so a late Ctrl+C still prints "No files created" after a write (tasks/TASK-005-…:17-18; PLAN.md:52)
  `_hold_interrupts()` wraps only `atomic_write_config` and `_register_in_global_dashboard`. After it restores `init._interrupt_handler`, `_show_success_message` and the return path up to `init()`'s `finally` still run; a SIGINT there prints "Setup cancelled. No files created." and exits 130 with files on disk — the same false-claim class as round-1 #1, just a smaller window. The Decision's "an interrupt lands before the write or not at all" is not strictly true.
  Recommendation: apply — in TASK-005, move `_show_success_message` inside the `_hold_interrupts()` block (or set a "written" flag that makes `_interrupt_handler` stop claiming "No files created"), and soften the PLAN.md Decision wording accordingly.

- [low] Several factual claims in the plan are wrong (PLAN.md:54; tasks/TASK-004-…:73; tasks/TASK-005-…:16, 28, 44)
  (a) "Today that surfaces as a traceback" — false: Typer's `_main` converts `EOFError` to `Abort`, printing "Aborted." and exit 1 (verified: `CliRunner` with input `"\n"` → exit 1, `SystemExit(1)`, no `.adw`). `test_end_of_input_cancels` is RED today only on the "Nothing was written" text. (b) TASK-004's note on `c\n`: in an empty dir the first prompt is `Prompt.ask("Language")`, not a `Confirm`; "c" is accepted as a custom language and EOF hits at "Platform" — also true today. (c) TASK-005 says "keep … `No files were written.`" but the current text is "No files were created." (summary.py:153) — it is a change. (d) TASK-005's decline test: patching `adw.cli.wizard.summary.Confirm.ask` replaces `ask` on Rich's shared `Confirm` class, so it is not "only the summary module's `Confirm`" — basics' `Confirm.ask` is patched too (verified). The test still passes, via a different path (registration declined too).
  Recommendation: apply — correct PLAN.md:54 and the TASK-004 note, say "change" in TASK-005:16, and patch `adw.cli.wizard.summary._prompt_confirmation` in TASK-005:28.

- [low] Some evidence doesn't back the criteria it's cited for (PLAN.md:65, 72; tasks/TASK-005-…:26, 29; tasks/TASK-006-…:21)
  PLAN.md's write-failure criterion requires "prints the error", but neither `test_write_failure_exits_non_zero` nor the TASK-006 row asserts the error text. The Risks mitigation says the accept-defaults test "pins the full sequence end to end", but it feeds 40 newlines and asserts nothing about prompt order/count (`test_run_wizard_calls_steps_in_order…` covers only step order). The accept test's "no … back/cancel text" assertion conflicts with TASK-005's new welcome text ("Ctrl+C cancels"); TASK-006's `b - Go back` phrasing is the unambiguous one.
  Recommendation: apply — assert the error message in the write-failure test (TASK-005/TASK-006); assert absence of `b - Go back`/`c - Cancel wizard` rather than "cancel"; either assert the `Step N/7` header sequence in the accept transcript or reword the PLAN.md:65 mitigation to cite the order test.

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | Scratch-repo transcripts would run the main checkout's `adw` (staging), not this branch | med | apply | Verified: `which adw` is the main checkout's editable install; the evidence must come from this worktree's `.venv/bin/adw`. | RESEARCH.md:Useful Commands; TASK-005:Evidence; TASK-006 |
| 2 | TASK-004 deletes the only B17 regression test (`test_accepted_defaults_yield_ship_mapping`) and a basics behaviour test | med | apply | Correct: only the two state-storage tests are ADR-001 waste. | TASK-004 |
| 3 | TASK-001's `requirements.txt` case isn't RED today; the test can't tell detection from the `"python"` fallback | med | apply | Correct: assert the detection confirm prompt was shown. | TASK-001 |
| 4 | Detector switch drops `build.gradle.kts` detection | med | apply | Real regression; add `build.gradle.kts` and `setup.cfg` to `ProjectTypeDetector.MARKERS`, which also fixes minimal init. | TASK-001 (+`detector.py`, `test_detector.py`); PLAN.md:Scope, Research Summary; RESEARCH.md:drift table |
| 5 | Hold-off window ends before the success message | low | apply | Move the success message inside the held block and state the remaining window precisely. | TASK-005; PLAN.md:Decisions |
| 6 | Factual errors: EOF today exits 1 "Aborted." (not a traceback); `c\n` note; "keep" vs "change" of the write-failure text; `Confirm.ask` patch is class-wide | low | apply | All verified against code; correct the text and patch `_prompt_confirmation` instead. | PLAN.md:Decisions; TASK-004:Notes; TASK-005 |
| 7 | Evidence gaps: write-failure error text unasserted; "pins the full sequence" unbacked; "no cancel text" clashes with the new welcome | low | apply | Assert the error text, the `Step N/7` header sequence, and the absence of `b - Go back`/`c - Cancel wizard`. | TASK-005; TASK-006; PLAN.md:Risks |
