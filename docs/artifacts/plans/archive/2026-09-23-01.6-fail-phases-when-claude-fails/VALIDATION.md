# Validation: Fail phases when Claude fails

Validated: 2026-09-23 at `88034c6c`. CI on PR #203 was green for every task commit up to `e813dcd8`. The run for `88034c6c` was still in progress when this file was written.

| Criterion | Result |
|---|---|
| `MockExecutor` fails twice and then succeeds: the phase passes on attempt 3 with sleeps `[0.5, 1.0]` | Met: `test_mock_executor_fails_twice_then_succeeds`. RED `[1, 2]` before TASK-001, GREEN after |
| A fake `claude` that exits 1 fails the run: `failed` in `context.json` and in the index after 4 attempts | Met: `test_fake_claude_exit_fails_run`. RED `DID NOT RAISE` on TASK-001, GREEN from TASK-002. Scratch-repo smoke run below |
| `grep -rn "RetryExecutor\|LLMRateLimitError" src` is empty | Met |
| `grep -rn "timeout: int\|timeout=timeout" src/adw/executors` is empty, and the pipe-drain `wait_for(..., timeout=5.0)` stays | Met |
| `scripts/preflight.sh` passes; `uv run pytest` is green with coverage ≥ 80% | Met: 4264 passed, 5 skipped, 84.40% |

## B2 regression test: `test_fake_claude_exit_fails_run`

`tests/integration/core/test_phase_failure.py` runs the real `create_orchestrator` in a `git_repo`. That repo's `project.yaml` sets `llm.retry` to `max_retries: 4`, `base_delay_seconds: 0.5`, `multiplier: 3` and `max_delay_seconds: 1.0`. A fake `bin/claude` prints an `is_error` result, writes `fatal: simulated failure` to stderr and exits 1.

This is B2's regression test. The epic-level "B1–B5 regression test" criterion stays unticked until the other bugs have theirs.

RED, on the TASK-001 code (`a75c471a`) with the test added: the non-zero exit returned a result, so nothing was raised and the run completed.

```
tests/integration/core/test_phase_failure.py::test_mock_executor_fails_twice_then_succeeds PASSED [ 50%]
tests/integration/core/test_phase_failure.py::test_fake_claude_exit_fails_run FAILED [100%]
E       Failed: DID NOT RAISE <class 'adw.exceptions.LLMError'>
========================= 1 failed, 1 passed in 3.24s ==========================
```

GREEN at `88034c6c`, together with the other acceptance tests:

```
tests/integration/core/test_phase_failure.py::test_mock_executor_fails_twice_then_succeeds PASSED [ 20%]
tests/integration/core/test_phase_failure.py::test_fake_claude_exit_fails_run PASSED [ 40%]
tests/unit/core/test_orchestrator.py::TestRetryLogic::test_backoff_reads_retry_config PASSED [ 60%]
tests/unit/core/test_orchestrator.py::TestRetryLogic::test_retry_prints_line_per_retry PASSED [ 80%]
tests/unit/models/test_llm.py::TestLLMResult::test_unknown_field_rejected PASSED [100%]
============================== 5 passed in 5.07s ===============================
```

## `test_mock_executor_fails_twice_then_succeeds`

RED before TASK-001: the orchestrator slept `2**attempt` and ignored `llm.retry`.

```
E       assert [call(1), call(2)] == [call(0.5), call(1.0)]
```

GREEN from TASK-001 onwards (see the run above): 3 executor calls, sleeps `[0.5, 1.0]`, run `completed`.

## Smoke test: `adw run --phase plan` in a scratch repo

This follows the recipe in `RESEARCH.md`: a scratch `HOME`, a fake `bin/claude` first on `PATH`, a committed `.adw/project.yaml` with `worktree.enabled: false` and no `llm.retry` (so the defaults apply), and `.adw/runs/` gitignored. It was run from this checkout with `uv run --project`.

```
⠋ LLM executing... · 0:00:0011:44:03 [ERROR] [llm] Claude Code execution failed
11:44:03 [ERROR] [phase] LLM execution failed
11:44:03 [ERROR] [phase] Phase failed
11:44:03 [WARN] [phase] Retrying phase
⚠ Phase 'plan' failed (CLAUDE_EXIT_NONZERO), retrying in 1s (2/3)...
⠋ LLM executing... · 0:00:0011:44:04 [ERROR] [llm] Claude Code execution failed
11:44:04 [ERROR] [phase] LLM execution failed
11:44:04 [ERROR] [phase] Phase failed
11:44:04 [WARN] [phase] Retrying phase
⚠ Phase 'plan' failed (CLAUDE_EXIT_NONZERO), retrying in 2s (3/3)...
⠋ LLM executing... · 0:00:0011:44:06 [ERROR] [llm] Claude Code execution failed
11:44:06 [ERROR] [phase] LLM execution failed
11:44:06 [ERROR] [phase] Phase failed
11:44:06 [ERROR] [phase] Retries exhausted

╭──────────────────────────────── PLAN Failed ─────────────────────────────────╮
│ Error: Claude Code exited with code 1: fatal: simulated failure              │
│                                                                              │
│ Suggestion: See the run's live.log. The phase is retried per llm.retry in    │
│ .adw/project.yaml.                                                           │
╰──────────────────────────────────────────────────────────────────────────────╯

╭────────────────────────────── Pipeline Summary ──────────────────────────────╮
│ · plan → · build → · validate → · document → · ship                          │
│                                                                              │
│ Status: failed                                                               │
│ Duration: 5.1s                                                               │
│ Tokens: 0                                                                    │
╰──────────────────────────────────────────────────────────────────────────────╯
11:44:06 [ERROR] [phase] Run failed
Error: Claude Code exited with code 1: fatal: simulated failure
adw exit: 1
```

State after the run:

```
claude calls: 3
context.json: {'status': 'failed', 'current_phase': 'plan', 'phase_history': []}
index 01M3718WPQWAXCJQDKWGHFTX7M status failed
live.log: [ERROR] Claude Code exited with code 1: fatal: simulated failure
```

On `f61f8873` the same recipe exited 0 after 1 call, and recorded `completed` in both `context.json` and the index (`RESEARCH.md`).

## Greps

```
$ grep -rn "RetryExecutor\|LLMRateLimitError" src
(exit 1)
$ grep -rn "timeout: int\|timeout=timeout" src/adw/executors
(exit 1)
$ grep -n "timeout=5.0" src/adw/executors/claude_code.py
285:                timeout=5.0,
```

TASK-004's grep for `\.success\b|attempt_count|success=` returns one line, and it is intended: the negative test `test_unknown_field_rejected` passes `LLMResult(content="x", success=True)` to prove that `extra="forbid"` rejects it.

## Preflight and full suite

```
$ scripts/preflight.sh
All checks passed!
165 files already formatted
Success: no issues found in 165 source files
preflight: ok

$ uv run pytest -p no:cacheprovider
Required test coverage of 80% reached. Total coverage: 84.40%
================= 4264 passed, 5 skipped in 227.23s (0:03:47) ==================
```

The full suite ran on the committed `88034c6c` tree. `test_stats_display_with_real_data` passed on the first run.
