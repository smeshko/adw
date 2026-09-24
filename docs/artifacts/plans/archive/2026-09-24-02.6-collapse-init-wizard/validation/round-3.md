# Adversarial Validation — Round 3

**Run:** 2026-09-24 05:45 UTC
**Plan:** 02.6-collapse-init-wizard
**Status at start:** draft
**Prior rounds in scope:** validation/round-1.md, validation/round-2.md
**Reviewer:** subagent (`general-purpose`, same adversarial framing). Codex was still usage-limited.

## Codex output

<!-- Paste /codex:adversarial-review stdout verbatim below this line. Do not edit. -->

# Adversarial Review — Round 3 (subagent)
Verdict: needs-attention

The round-1 and round-2 applies hold against the code, and there are no defer/reject rows to contest. I verified the typing claims by running `mypy --strict` on a scratch copy of the planned shapes (the `(section, title, step)` list with the basics lambda, `_hold_interrupts()`, and the `get_defaults(...)["language"] or "unknown"` narrowing) — all clean. `.venv/bin/adw` imports the worktree's `src/adw`. Today's wizard under `CliRunner` in a scratch git repo with 40 newlines exits 0, prints plain-text `Step N/8: <title>` headers, and `adw validate` reports `0 errors`, so the accept-test design and its `Step 1/7…7/7` assertion are sound once retry is gone. Dependencies are acyclic and correct; every PLAN criterion has a TASK-006 row. One round-2 edit introduced a real defect (TASK-001's detection assert can never pass), and three smaller gaps leave evidence unrecorded or non-reproducible.

Findings:
- [medium] TASK-001's detection-prompt assert can't match the real prompt text, so the test fails even after GREEN (tasks/TASK-001-…:22, 39)
  The test must assert the `Confirm.ask` question contains `Language detected: <language>`, but `_prompt_language` passes a Rich-markup string: `f"Language detected: [cyan]{detected}[/]. Correct?"` (src/adw/cli/wizard/basics.py:185-189). Verified in a `setup.cfg` dir with `Confirm.ask` patched: the call arg is `'Language detected: [cyan]python[/]. Correct?'` and `"Language detected: python" in q` is `False`. As written, every parametrized case fails permanently, and the RED step's "`setup.cfg` passes today" is false. Stripping the markup from the prompt would violate PLAN's out-of-scope rule on prompt wording.
  Recommendation: apply — in TASK-001, assert on `rich.text.Text.from_markup(question).plain` containing `Language detected: <language>` (or on the literal `Language detected: [cyan]<language>[/]`).

- [low] `test_write_holds_off_ctrl_c` never reaches the dashboard registration it's meant to cover (tasks/TASK-005-…:31; PLAN.md:73)
  `run_summary_step` only calls `_register_in_global_dashboard` when `cfg["global_registry"]["global_registry_enabled"]` is truthy (summary.py:133-139), and the existing `TestRunSummaryStep` cfgs carry no `global_registry` key (test_summary.py:662-667). The test says "all three recorded `SIG_IGN`" but doesn't enable registration, so it either fails or — if written as `all(...)` over what was recorded — passes with two recordings, leaving the "Ctrl+C cannot interrupt … the dashboard registration" claim unevidenced.
  Recommendation: apply — in TASK-005, set `cfg["global_registry"] = {"global_registry_enabled": True, "global_registry_name": "p"}` and assert exactly three recordings, all `SIG_IGN`.

- [low] TASK-005 never records the RED that PLAN criteria 1 and 4 require (tasks/TASK-005-…:44, 49; PLAN.md:70, 73)
  PLAN asks for "the transcript test, RED then GREEN" and "`test_write_holds_off_ctrl_c`, RED then GREEN", but TASK-005's RED step lists only the decline, write-failure, end-of-input and hold-off tests, and its Evidence line omits the hold-off test and never mentions the accept test. The accept test does fail after TASK-004 (prints `Configuration created!`, `Wizard Complete!`, `b - Go back`), so the RED is reproducible, but following TASK-005 literally never captures it, and TASK-006 row 1 only asks "passes".
  Recommendation: apply — add the accept test to TASK-005's RED step and list the accept and hold-off RED failures in its Evidence line.

- [low] The acceptance grep matches stale bytecode with system `grep` (PLAN.md:74; tasks/TASK-006-…:23)
  `git rm` leaves orphaned `.pyc` files. Today `command grep -rn "WizardFlowController\|WizardState\|StepHandler\|nav_prompt_ask" src tests` already prints `Binary file src/adw/models/__pycache__/wizard.cpython-313.pyc matches` and similar; after TASK-004 the `models/wizard`, `navigation`, `retry` and `ship` `.pyc` files remain. The agent's shell wraps `grep` as ugrep with `-I --ignore-files`, so the implementer sees empty output, but Ivo re-running the same command in his terminal would see matches — the "returns nothing" evidence isn't reproducible.
  Recommendation: apply — in TASK-006, clear caches first (`find src tests -name __pycache__ -prune -exec rm -rf {} +`) or add `-I --exclude-dir=__pycache__` to both greps.

## Triage

| # | Finding | Severity | Verdict | Rationale | Applied to |
|---|---------|----------|---------|-----------|------------|
| 1 | TASK-001's detection assert can't match the Rich-markup prompt text | med | apply | Verified: the question is `Language detected: [cyan]python[/]. Correct?`; compare on `Text.from_markup(q).plain`. A defect my round-2 edit introduced. | TASK-001 |
| 2 | `test_write_holds_off_ctrl_c` never enables registration | low | apply | Correct: registration runs only when `global_registry_enabled`. | TASK-005 |
| 3 | TASK-005 never records the accept and hold-off RED runs PLAN asks for | low | apply | Add them to RED and the Evidence line. | TASK-005 |
| 4 | Acceptance grep matches stale `.pyc` files with the system `grep` | low | apply | Reproducibility for anyone re-running it; add `-I --exclude-dir=__pycache__`. | PLAN.md:Acceptance Criteria; TASK-006 |

**Round-3 stop.** Round 3 still produced action rows, which the protocol hands to the user. Ivo asked for an autonomous run with no questions, so I took act-and-stop: all four are local test-instruction and evidence fixes, not structural defects, and none changes the design. No fourth round.
