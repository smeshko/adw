# TASK-006: Delete dead executor, hook, logging, worktree and cli symbols

Depends on: TASK-005
Suggested commit: `refactor: delete unused executor, hook, logging, worktree and cli helpers`

## Goal

The remaining symbols the epic lists are gone: the executor, hook, logging, worktree and CLI helpers. So is the `console` parameter of `ClaudeCodeExecutor`, which only fed the deleted attribute.

## Files

- `src/adw/executors/mock.py`: delete `last_prompt`, `all_prompts`, `assert_called_once`, `assert_called_with` and `reset`. `call_count` stays because `tests/unit/executors/test_retry.py` uses it, and `_all_prompts` stays because `call_count` reads it.
- `src/adw/executors/claude_code.py`:
  - Delete the `console` parameter, its docstring lines, and `self.console = console or Console()`.
  - Remove the `rich.console.Console` import if nothing else uses it.
- `src/adw/cli/bootstrap.py:273`: stop passing `console=console` to `ClaudeCodeExecutor`. `console` is still used for `ProgressDisplay`.
- `src/adw/hooks/runner.py`: delete `find_hook`. `src/adw/hooks/__init__.py`: drop it from the import and `__all__`.
- `src/adw/logging/live_stream.py`: delete `LiveStreamTransport.write_phase` and `write_raw`.
- `src/adw/logging/console.py`: delete the `ConsoleTransport.is_tty` property and its docstring line. `_is_tty` stays.
- `src/adw/worktree/branch.py`: delete `WorktreeBranchManager.create_branch` and its class-docstring example. `ruff --fix` drops the now-unused `WorktreeError` import.
- `src/adw/worktree/concurrent.py`: delete `can_start_run` and `get_run_info`, and the `can_start_run` line in the class-docstring example.
- `src/adw/commands/template.py`: delete `escape_feature_description` and its `__all__` entry.
- `src/adw/cli/app.py`: delete the `escape_feature_description` import (L28) and the discarded call `_ = escape_feature_description(feature)` (L343).
- Tests:
  - `tests/unit/executors/test_claude_code.py`: delete `TestRealTimeStreaming::test_accepts_custom_console`.
  - `tests/unit/hooks/test_runner.py`: delete `TestFindHook`.
  - `tests/integration/test_hooks.py`: delete `test_find_and_execute_hook_workflow` and `test_missing_hook_returns_none`.
  - `tests/unit/logging/test_console.py`: delete `TestConsoleTransportTTYDetection`. `TestConsoleTransportTTYVsNonTTY` still covers TTY vs plain output.
  - `tests/unit/worktree/test_branch.py`: delete `TestBranchCreation`.
  - `tests/unit/worktree/test_concurrent.py`: delete `test_can_start_run_when_under_limit`, `test_can_start_run_when_at_limit` and the three `test_get_run_info_*` tests.
  - `tests/unit/commands/test_escape.py`: delete.

## Acceptance

- [ ] `grep -rnE "last_prompt|all_prompts|assert_called_with\(self|def reset\(self\)|find_hook\b|write_phase|write_raw|def is_tty|create_branch\(|can_start_run|get_run_info|escape_feature_description" src` returns nothing. Also, `grep -n "console" src/adw/executors/claude_code.py` shows no `console` parameter or attribute.
- [ ] `grep -rn "escape_feature_description\|find_hook\b" tests` returns nothing.
- [ ] `scripts/preflight.sh` passes.
- [ ] `uv run pytest tests/unit/executors tests/unit/hooks tests/unit/logging tests/unit/worktree tests/unit/commands tests/unit/cli tests/integration/test_hooks.py -o addopts=""` passes.
- [ ] The `vulture` diff against this task's start shows no new entry, or each new entry is handled per the cascade rule.

Evidence: the empty greps and the pytest summary line.

## Steps

### RED
- [ ] Save the `vulture` baseline.
- [ ] Re-grep each symbol across `src/adw` with no `--include` filter. At HEAD, each should show only its definition, docstring and re-export, except `escape_feature_description`, which also shows the discarded call in `cli/app.py`.

### GREEN
- [ ] Delete the symbols, the `console` parameter and its `bootstrap` argument, and the re-exports.
- [ ] Delete the tests listed under Files.
- [ ] Run the targeted pytest command.

### REFACTOR
- [ ] Run `uv run ruff check src/ --fix` and `uv run ruff format src/`.
- [ ] Take the `vulture` diff and apply the cascade rule. Watch for `MockExecutor._all_prompts`: it stays while `call_count` stays.
- [ ] Run `scripts/preflight.sh`.

## Notes

- `CommandResolver._find_hook_path` is the live hook lookup and is unrelated to `hooks.runner.find_hook`.
- `ConcurrentRunManager.check_can_start_or_raise` is the live concurrency check and stays.
- The `adw run` feature text was never escaped, since the call's result was discarded, so removing the call changes no behaviour.
