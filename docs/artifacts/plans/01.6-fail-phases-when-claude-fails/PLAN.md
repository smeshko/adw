# Plan: Fail phases when Claude fails

Status: in-progress
Branch: feature/adw-12
Risk: medium
Epic: 01 — Cleanup: test safety, dead code and bug fixes ([epic](../../epics/01-cleanup-safety-dead-code-bugs.md))
Phase: 1.6 — Fail phases when Claude fails
Linear: ADW-12
Created: 2026-09-23

## Goal

A non-zero Claude Code exit fails the phase. The orchestrator retries it as the only retry layer, with the backoff set in `llm.retry`, and a run that keeps failing ends as `failed`, not `completed` (B2).

## Scope

- `Orchestrator._execute_phase_with_retry` becomes the only retry layer:
  - Reads `RetryConfig` (`retry_config` constructor argument, replacing `max_retries: int`).
  - Backoff is `min(base_delay_seconds × multiplier^(n-1), max_delay_seconds)`, with no jitter.
  - Prints a yellow retry line through `progress_display.console`.
- `cli/bootstrap.py` passes `llm_config.retry` to the `Orchestrator` and stops wrapping the executor.
- Delete:
  - `executors/retry.py`, its export in `executors/__init__.py`, and `tests/unit/executors/test_retry.py`
  - `LLMRateLimitError` in `exceptions.py`, which also removes the dead `isinstance` branch that lived in `retry.py`
- `ClaudeCodeExecutor._build_result` raises on a non-zero exit instead of returning `LLMResult(success=False)`:
  - `LLMError(code="CLAUDE_EXIT_NONZERO", recoverable=True)`
  - The message is the exit code plus the last 20 lines of stderr. When stderr is empty, it falls back to the text of the stream-json `result` message that carries `is_error: true`.
- Remove the `timeout` parameter from `LLMExecutor.execute`, `ClaudeCodeExecutor.execute` and `MockExecutor.execute`. No caller passes it.
- Delete `LLMResult.success`, `LLMResult.error` and `LLMResult.attempt_count`, and set `extra="forbid"` on `LLMResult`.
- Docs: the `RetryConfig` docstring and field descriptions, and the retry rows in `docs/architecture/deep-dive/orchestrator.md`.
- A new integration test module, `tests/integration/core/test_phase_failure.py`, runs the real `create_orchestrator` in a `git_repo`. It covers the acceptance paths for both `MockExecutor` and a fake `claude` binary.

## Out of Scope

- Typed phase outcomes, or reading `is_error` on a zero exit (Claude reports an error but exits 0): Epic 07, phase 7.2.
- Renaming `RetryConfig.max_retries`. It keeps its name and its "total attempts" meaning, so existing `project.yaml` files, the wizard and the dashboard settings form keep working.
- The dead `MockExecutor` helpers (`all_prompts`, `last_prompt`, `reset`, `assert_called_*`): phase 1.2.
- Other exception pruning and re-export trimming (`CommandError`, `PhaseError`, `to_dict()`, and the other `__init__` lists): phase 1.3. This phase removes only `LLMRateLimitError`, which 1.3 explicitly leaves for it, and the `RetryExecutor` export that would otherwise break the import.
- Orphaned Claude processes when `ShutdownRequested` (a `BaseException`) escapes `asyncio.run`. The bug predates this phase and is unchanged by it.
- Changing which non-LLM errors count as recoverable, for example `context_manager`, Linear and `cli/pr.py`. They keep going through the same loop, and with the default `RetryConfig` their timing is unchanged (1 s, then 2 s).

## Research Summary

See [RESEARCH.md](./RESEARCH.md). Key findings:

- **B2 reproduced on HEAD (`f61f8873`).** A fake `claude` on `PATH` that exits 1 and writes an `is_error` result was run through `adw run --phase plan` in a scratch repo:
  - it was called once
  - `context.json` and the index both recorded `completed`
  - `adw` exited 0
- **The two retry layers never both fire.** `RetryExecutor` retries only when the executor raises `LLMError`, which a non-zero exit never did. The orchestrator loop does fire, but for other recoverable `ADWError`s only, and with hard-coded `2**attempt` delays.
- **Retrying a whole phase is safe for the built-in hooks.** `plan/pre.sh` creates the branch or switches to it (and exits early when already on it), `ship/pre.sh` only reads, and `build`/`document`/`ship` `post.sh` run only after a successful LLM step.
- **`LLMResult` is never deserialized.** It is built in-process only, by the executors and by tests, so `extra="forbid"` cannot break reading old runs.
- **mypy checks only `src/`.** Without `extra="forbid"`, a stale `success=True` left in a test would be silently ignored by pydantic.
- **Baseline:** the six affected test files pass (282 tests in 1.3 s).

## Decisions

- **No jitter.** The user chose deterministic delays over porting `RetryExecutor`'s ±25% jitter. It keeps the backoff exactly assertable, and one run drives one Claude process, so there is no thundering herd.
- **Delete `success`, `error` and `attempt_count` from `LLMResult`** (user's choice). Nothing reads them after the executor raises, and an unread `success=False` is how B2 happened.
- **Print a retry line** (user's choice), following `_retry_empty_build`'s pattern: `⚠ Phase '{phase}' failed ({code}), retrying in {delay}s ({next}/{max})...`. A failed 20-minute build must not silently rerun.
- **Error text: stderr tail, else the `is_error` result text** (user's choice). Claude Code in stream-json mode often exits 1 with empty stderr and puts the reason in its `result` message. The message goes into `context.json` and the Linear failure comment.
- **Error code `CLAUDE_EXIT_NONZERO`**, next to the existing `CLAUDE_NOT_FOUND`. `CLAUDE_NOT_FOUND` stays non-recoverable.
- **`Orchestrator(retry_config: RetryConfig | None = None)`** replaces `max_retries: int = 3`. The only production caller is `create_orchestrator`, and tests pass `RetryConfig(...)`.
- **The acceptance tests go through `create_orchestrator` in a `git_repo`**, not a hand-built `PhaseRunner`. That also proves the `project.yaml → LLMConfig.retry → Orchestrator` wiring. The fixture's `llm.retry` uses non-default values (`max_retries: 4`, `base_delay_seconds: 0.5`, `multiplier: 3`, `max_delay_seconds: 1.0`), so a default-valued loop cannot pass.
- **Task order:** retry consolidation first (TASK-001), then the executor raise (TASK-002). This way no commit has two live retry layers stacking up to 9 Claude calls per phase.

## Risks

- **A long phase that fails gets rerun.** With defaults, a build that dies after 20 minutes runs up to 2 more times. Mitigation: the retry line makes it visible, and `llm.retry.max_retries: 1` turns retries off. The status quo, a silent `completed`, is worse.
- **A retried build starts from a partly edited worktree.** Auto-commit only runs on success, so a failed attempt's edits stay uncommitted for the next attempt. Accepted: the build prompt works from the current tree state.
- **Non-transient failures (bad auth, unknown model) are retried.** The cost is a few seconds of backoff before the run fails with the real message. Accepted.
- **Hidden `success=`/`error=` constructor kwargs survive TASK-004.** Mitigation: `extra="forbid"` turns each one into a `ValidationError` in the suite.
- **The integration fixture trips `plan/pre.sh`'s uncommitted-changes check.** `HOME` (`tmp_path/home`) and `.adw/runs/` live inside the `git_repo`. Mitigation: the fixture writes and commits a `.gitignore` covering `home/`, `bin/` and `.adw/runs/`, together with `.adw/project.yaml`.
- **Real sleeps in the new tests.** Mitigation: patch `adw.core.orchestrator.time.sleep` in every retry test, and assert the calls on that mock.

## Acceptance Criteria

- [ ] With `MockExecutor` configured to fail twice and then succeed, the phase succeeds on attempt 3 and waits the configured backoff between attempts (sleep patched and asserted: `[0.5, 1.0]`). Evidence: `test_phase_failure.py::test_mock_executor_fails_twice_then_succeeds` output.
- [ ] With a fake `claude` binary on `PATH` that exits 1, the phase is recorded as `failed` (not `completed`) in `context.json` and in the index, after the configured 4 attempts. Evidence: the `test_fake_claude_exit_fails_run` output, RED on the pre-TASK-002 code and GREEN after, plus the scratch-repo `adw run --phase plan` transcript in `VALIDATION.md`.
- [ ] `grep -rn "RetryExecutor\|LLMRateLimitError" src` returns nothing.
- [ ] `grep -rn "timeout: int\|timeout=timeout" src/adw/executors` returns nothing. The pipe-drain `asyncio.wait_for(..., timeout=5.0)` in `claude_code.py` stays.
- [ ] `scripts/preflight.sh` passes, and `uv run pytest` is green with coverage ≥ 80%.

## Tasks

Task state lives here. Tasks are appended by `scripts/add_task.py` and
`scripts/add_final_task.py`. Update the checkboxes as work progresses.

- [x] TASK-001: Make the orchestrator the single RetryConfig-driven retry layer
- [x] TASK-002: Raise LLMError when Claude Code exits non-zero (depends on TASK-001)
- [x] TASK-003: Drop the unused timeout parameter from executors (depends on TASK-001)
- [ ] TASK-004: Delete LLMResult success, error and attempt_count (depends on TASK-002)
- [ ] TASK-005: Final Validation
