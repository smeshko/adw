# Research: Fail phases when Claude fails

Curated findings only — no raw conversation transcripts.

## Key Files & Directories

- `src/adw/executors/claude_code.py`:
  - `_build_result` (≈ line 316) returns `LLMResult(success=False, error=stderr or "Claude Code exited with code N")` on a non-zero exit, after `live_stream.write_error`. Nothing in `src` reads `LLMResult.success` or `.error`, which is B2.
  - `_stream_subprocess` wraps `_read_process_output` and `_build_result` in `except Exception`, which logs "Claude Code execution failed" and re-raises. A raise from `_build_result` passes through it.
  - `_parse_output` reads the `result` message's `usage`, `total_cost_usd` and a `text` key. It ignores `is_error` and the `result` key, where Claude Code puts the error text.
- `src/adw/executors/retry.py`: `RetryExecutor` retries on `LLMError.recoverable`, with jitter and the `LLMRateLimitError.retry_after` branch, and sets `attempt_count`. Because the executor never raised on a non-zero exit, it never retried one.
- `src/adw/cli/bootstrap.py`:
  - `create_orchestrator` wraps `ClaudeCodeExecutor` in `RetryExecutor(config=llm_config.retry)` in production.
  - `MockExecutor` is used when `ADW_MOCK_EXECUTOR` is set, and is not wrapped.
  - `Orchestrator(...)` is built without `max_retries`, so it runs on the default of 3.
- `src/adw/core/orchestrator.py`:
  - `_execute_phase_with_retry`: `for attempt in range(self.max_retries)`, catches `ADWError`, calls `progress_display.on_llm_complete()`, re-raises non-recoverable errors, and sleeps `2**attempt`.
  - `_retry_empty_build` calls it with a nudge prefix, and prints its own yellow line through `progress_display.console`, the pattern the new retry line copies.
- `src/adw/core/phase_runner.py`: `run()` runs pre-hook → render → `_execute_llm` → capture artifacts → post-hook → auto-commit. On an `ADWError` it logs "Phase failed", sets `e.phase` and re-raises. `_execute_llm` calls `executor.execute(prompt, phase=, cwd=, model=)`, never with `timeout`.
- `src/adw/core/run_lifecycle.py`: `handle_adw_error` sets `status="failed"` in `context.json` and the index. `run`, `run_single_phase`, `resume` and `continue_from_run` all route an `ADWError` there.
- `src/adw/models/config.py`: `RetryConfig` has `max_retries` (default 3, gt 0; used as total attempts by both loops), `base_delay_seconds` 1.0, `max_delay_seconds` 60.0, `multiplier` 2.0 (gt 1), and a validator requiring max ≥ base. It lives at `LLMConfig.retry`, which is `llm.retry` in `project.yaml`, and is also exposed by the wizard (`cli/wizard/retry.py`), `yaml_generator.py` and the dashboard settings (`dashboard/mutations.py`).
- `src/adw/models/llm.py`: `LLMResult` has no `model_config`, so pydantic's default `extra="ignore"` applies. `success: bool` is required. `error` and `attempt_count` are optional.
- `src/adw/exceptions.py`: `LLMRateLimitError(LLMError)` has `retry_after` and `to_dict`. Only `retry.py` and a docstring in `executors/base.py` reference it.
- `src/adw/core/interruption.py`: `ShutdownRequested` is a `BaseException`, so the `except ADWError` retry loop never swallows Ctrl+C.
- Tests touched:
  - `tests/unit/executors/test_retry.py` (28 tests, deleted)
  - `tests/unit/cli/test_bootstrap.py::TestBootstrapRetryExecutorWiring` (3 tests)
  - `tests/unit/core/test_orchestrator.py`: `TestRetryLogic` (6), `test_init_default_max_retries`, `test_init_custom_max_retries`
  - `tests/unit/executors/test_claude_code.py`: `test_execute_with_timeout_parameter`, `test_execute_returns_failure_on_non_zero_exit`, `test_subprocess_error_returns_failure_result`, `test_stderr_included_in_error_message`, `test_fallback_error_message_when_no_stderr`, `TestDurationOnFailure`, and the `result.success` asserts
  - `tests/unit/executors/test_protocol.py`
  - `tests/unit/models/test_llm.py`
  - `tests/unit/core/test_phase_runner.py` (18 `LLMResult(success=...)` constructions)
  - `tests/integration/test_claude_code_executor.py` (skipped in mock mode, but still edited)

## Architecture Facts

- The retry unit is the whole phase: pre-hook, render, LLM, artifacts, post-hook, commit. Built-in pre-hooks are rerun-safe:
  - `plan/pre.sh` exits early if already on the feature branch, and otherwise creates the branch or switches to it
  - `ship/pre.sh` only reads (`gh pr view`)
  - `validate` has no hooks
  - post-hooks run only after a successful LLM step
- Recoverable `ADWError`s raised today: `context_manager` (3), `snapshot_manager` (2), `cli/pr.py` (2), `task_managers/linear*.py` (3). They go through the same loop, and with the default `RetryConfig` (1.0 s × 2^(n-1)) their delays stay 1 s, then 2 s.
- The test `HOME` is `tmp_path/home`, and the `git_repo` fixture's repo is `tmp_path` itself. Anything written under `~/.adw` or `.adw/runs/` therefore shows as untracked in that repo, and `plan/pre.sh` exits 1 on a dirty tree.
- `create_orchestrator` loads `.adw/project.yaml` through `ConfigLoader(get_project_root())`. `llm_config = config.llm`, so `llm.retry` in the fixture's `project.yaml` reaches bootstrap.
- `Orchestrator.run_single_phase(phase, feature_description, *, use_worktree=True)` re-raises the `ADWError` after `handle_adw_error` records the failure.
- `IndexManager.get_recent_runs()` reads the global index under `Path.home()/.adw`.

## Constraints

- mypy `--strict` covers `src/adw` only (`scripts/preflight.sh`), so test code is not type-checked.
- Tests run with `ADW_MOCK_EXECUTOR=1` from `tests/conftest.py`. The fake-`claude` test must `monkeypatch.delenv("ADW_MOCK_EXECUTOR")`.
- Every test that touches git or runs a phase hook must use `git_repo` plus `monkeypatch.chdir` (AGENTS.md).
- Phases 1.2 and 1.3 are unmerged and touch neighbouring code: `MockExecutor` helpers, the `executors/__init__` exports and `exceptions.py`. Keep this phase's edits to the symbols named in the epic, to keep conflicts small.

## Useful Commands

```bash
# Affected unit tests (baseline: 282 passed in 1.3 s)
uv run pytest tests/unit/executors tests/unit/core/test_orchestrator.py \
  tests/unit/core/test_phase_runner.py tests/unit/cli/test_bootstrap.py \
  tests/unit/models/test_llm.py tests/unit/models/test_retry_config.py -o addopts="" -q

# B2 reproduction in a scratch repo (scratch HOME so the real ~/.adw is untouched)
CHECKOUT=$(git rev-parse --show-toplevel)  # run from the plan checkout
S=$(mktemp -d); mkdir -p "$S/bin" "$S/home" "$S/repo"
cat > "$S/bin/claude" <<'EOF'
#!/bin/sh
echo call >> "$FAKE_CLAUDE_LOG"
echo '{"type":"result","subtype":"success","is_error":true,"result":"API Error: 529 overloaded"}'
echo "fatal: simulated failure" >&2
exit 1
EOF
chmod +x "$S/bin/claude"
cd "$S/repo" && git init -q -b main
mkdir -p .adw && printf 'name: scratch\nlanguage: python\ntest_command: "true"\nworktree:\n  enabled: false\n' > .adw/project.yaml
printf '.adw/runs/\n' > .gitignore && git add . && git -c user.name=t -c user.email=t@t commit -qm init
HOME="$S/home" GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t \
  FAKE_CLAUDE_LOG="$S/calls.log" PATH="$S/bin:$PATH" \
  uv run --project "$CHECKOUT" adw run --phase plan "noop feature"
```

Result at `f61f8873`:
- exit 0
- `claude calls: 1`
- `context.json` `status completed`, `phase_history ['plan']`
- index `status completed`

## Uncertainty

- **Whether `plan/pre.sh` blocks the scratch run.** Resolved: the first attempt failed with "Uncommitted changes detected" because `.adw/` was untracked. Committing `project.yaml` and gitignoring `.adw/runs/` fixed it, and the integration fixture does the same, adding `home/` and `bin/`.
- **Whether `extra="forbid"` on `LLMResult` can break old runs.** Resolved: `LLMResult` is never loaded from disk. Its only constructors are the executors and tests.
- **The exact shape of Claude Code's error `result` message.** Partly open. The executor reads `data.get("is_error")` and `data.get("result")` defensively, and falls back to the bare exit code. The fake binary emits `{"type":"result","is_error":true,"result":"..."}`.

## References

- Epic: [01 — phase 1.6](../../epics/01-cleanup-safety-dead-code-bugs.md)
- [Orchestrator deep dive](../../../architecture/deep-dive/orchestrator.md) (retry rows go stale with this phase)
- [ADR-001 test reduction strategy](../../../architecture/adrs/ADR-001-test-reduction-strategy.md)
- Prior plan pattern: [01.1-isolate-test-suite](../01.1-isolate-test-suite/PLAN.md) (`adw.core.orchestrator.time.sleep` patching)
- Linear: ADW-12
