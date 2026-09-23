# TASK-005: Trim test_claude_code.py and hoist its executor fixture

Depends on: None
Suggested commit: `test: trim trivial executor tests and hoist the executor fixture`

## Goal

`test_claude_code.py` holds only executor behaviour tests, built on one `executor` fixture. The hook-timeout precedence tests live with the hook runner tests.

## Files

- `tests/unit/executors/test_claude_code.py`:
  - Delete `TestClaudeCodeExecutorClass` (4 tests: exists, isinstance protocol, constructor, has `execute`).
  - Delete `TestHookRunnerTimeoutResolution`, after moving 3 of its tests (below).
  - In `TestAdditionalParsingCoverage`, delete `test_handles_json_array`. It hits the same branch (`claude_code.py:417-418`) as `test_handles_non_dict_json`. Keep the other four.
  - Add one module-level fixture near the top of the file:

    ```python
    @pytest.fixture
    def executor() -> ClaudeCodeExecutor:
        return ClaudeCodeExecutor(LLMConfig(path="claude"))
    ```

    Then delete the 11 class-level `executor` fixtures. `RESEARCH.md` → Fixture duplicate groups lists their classes.
- `tests/unit/hooks/test_runner.py`: add `class TestResolveTimeout` with the three precedence tests, their imports moved to module level:
  - `test_timeout_parameter_takes_precedence`
  - `test_config_timeout_used_when_no_parameter`
  - `test_default_timeout_used_when_config_is_zero`

  Drop the `assert result == 60` line from the last one; it is the constant check. Drop `test_default_hook_timeout_constant_value` entirely.
- `tests/integration/conftest.py` (new): the same `executor` fixture, with a one-line module docstring.
- `tests/integration/test_claude_code_executor.py` (`TestClaudeCodeIntegration`, line ~39) and `tests/integration/test_token_tracking.py` (`TestTokenTrackingIntegration`, line ~22): delete the class-level `executor` fixtures.

## Acceptance

- [ ] The duplicate-fixture scan (`RESEARCH.md` → Useful Commands) shows exactly two `executor` definitions: `tests/unit/executors/test_claude_code.py` (module-level) and `tests/integration/conftest.py`.
- [ ] Branch coverage of `adw.executors.claude_code` over `tests/unit/executors tests/integration` is unchanged from the with-class baseline in `RESEARCH.md` (`233 29 94 13 85%`). The same lines are missed; in particular `417-418`, `461->404`, `467->404` and `477->404` are still covered.
- [ ] `uv run pytest tests/unit/executors tests/unit/hooks tests/integration -o addopts=""` passes.
- [ ] `uv run pytest tests/unit/hooks/test_runner.py -o addopts="" -k TestResolveTimeout -v` shows 3 passing tests.
- [ ] `uv run pytest --collect-only -q -o addopts="" | tail -1` shows **4,124** after TASK-001–004 (4,130 − 4 − 4 + 3 − 1).
- [ ] `uv run ruff check tests/ && uv run ruff format --check tests/` pass.

Evidence:
- the scan output
- the coverage line and its missing-lines list, before and after
- the `-k TestResolveTimeout -v` run
- the collected count

## Steps

### RED
- [ ] Record the branch-coverage line and missing lines for `claude_code.py` with the command in `RESEARCH.md` → Useful Commands (no deselect).
- [ ] Add `TestResolveTimeout` to `tests/unit/hooks/test_runner.py`, and run it (3 pass) before deleting the original class. The precedence behaviour must be covered at every point.

### GREEN
- [ ] Delete `TestClaudeCodeExecutorClass`, `TestHookRunnerTimeoutResolution` and `test_handles_json_array`.
- [ ] Add the module-level `executor`, delete the 11 class-level copies, and run `test_claude_code.py`.
- [ ] Create `tests/integration/conftest.py`, delete the two integration copies, and run both files.
- [ ] Re-run the coverage command, and compare its missing lines with RED.

### REFACTOR
- [ ] Drop imports left unused in `test_claude_code.py` (e.g. `LLMExecutor` if only the deleted class used it). Run ruff check and format on `tests/`.

## Notes

- `TestClaudeCodeExecutorClass::test_implements_llm_executor_protocol` overlaps `tests/unit/executors/test_protocol.py`, which already checks protocol conformance with a stub. No coverage is lost.
- Phase 1.2 deletes `find_hook` and `TestFindHook` from `hooks/test_runner.py`. Put `TestResolveTimeout` after `TestHookRunner`, not after `TestFindHook`, to keep the rebase conflict small.
- Other integration modules may define an `executor` of their own, such as a `MockExecutor`. The local definition shadows the conftest one, so they are unaffected.
