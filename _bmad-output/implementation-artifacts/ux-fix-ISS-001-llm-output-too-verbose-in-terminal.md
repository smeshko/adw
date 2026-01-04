# Story: UX Fix - Hide verbose LLM output from terminal

Status: complete
Linear Issue: not-configured
Epic: 7 - Observability & Logging
Created: 2026-01-04
Source Issue: ISS-001-llm-output-too-verbose-in-terminal.md

---

## Story

As a **developer using ADW**,
I want **LLM output to be hidden from the main terminal during phase execution**,
so that **I can easily follow execution progress without being overwhelmed by verbose streaming text**.

## Acceptance Criteria

- [x] **AC1**: During phase execution, LLM streaming text is NOT printed to the terminal by default
- [x] **AC2**: A progress spinner with token count continues to show execution is happening (existing behavior preserved)
- [x] **AC3**: LLM output is still captured to log files (existing `StreamLogger` behavior preserved)
- [x] **AC4**: Users can view live LLM output via `adw logs --follow` in a separate terminal
- [x] **AC5**: A new `--show-llm-output` flag enables verbose LLM streaming (for debugging)
- [x] **AC6**: Verbosity level `--trace` also enables LLM output streaming (backward compatibility)

## Tasks / Subtasks

### Task 1: Suppress default LLM console printing
- [x] Modify `ClaudeCodeExecutor._read_process_output()` to skip `console.print()` by default
- [x] Add `show_llm_output: bool` parameter to executor (default: False)
- [x] Only print to console when `show_llm_output=True`

### Task 2: Add CLI flag for explicit LLM output
- [x] Add `--show-llm-output` flag to `adw run` command
- [x] Pass flag through to executor via config or direct parameter
- [x] Document flag in help text

### Task 3: Wire verbosity to LLM output control
- [x] When `--trace` verbosity is set, enable `show_llm_output`
- [x] Ensure backward compatibility for users who expect verbose output

### Task 4: Verify log capture still works
- [x] Confirm `StreamLogger.token()` continues capturing all output
- [x] Confirm JSONL stream files are written correctly
- [x] Confirm `adw logs --follow` can display live output (Story 7-4 dependency)

### Task 5: Update tests
- [x] Add test for suppressed console output (default behavior)
- [x] Add test for `--show-llm-output` flag enabling console print
- [x] Add test for `--trace` enabling LLM output

---

## Developer Context

### Problem Analysis

**Root Cause**: In `src/adw/executors/claude_code.py:329`, the executor directly prints LLM streaming output to the Rich console:

```python
# claude_code.py:313-333
async def read_stdout() -> None:
    while True:
        line = await stdout.readline()
        if not line:
            break
        decoded = line.decode()
        content_lines.append(decoded)

        display_text = self._extract_display_text(decoded)
        if display_text:
            self.console.print(display_text, end="")  # <-- THIS IS THE PROBLEM

        if stream_logger:
            stream_logger.token(decoded)
```

**Impact**: Every token from the LLM is printed in real-time, making the terminal extremely noisy and hard to follow.

### Technical Requirements

1. **Minimal Change**: Only suppress the `console.print()` call, preserve all other behavior
2. **Stream Capture**: `StreamLogger.token()` must continue to work for log files
3. **Progress Display**: The spinner + token count from `progress.py` must continue working
4. **Flag Propagation**: New flag must flow from CLI → Orchestrator → PhaseRunner → Executor

### Architecture Compliance

**Existing Pattern**: The executor already receives a `Console` instance via constructor injection (`claude_code.py:57-83`):

```python
def __init__(
    self,
    config: LLMConfig,
    *,
    console: Console | None = None,  # Already injectable
    ...
):
    self.console = console or Console()
```

**Recommended Approach**: Add `show_llm_output` flag to control console printing behavior without changing the console injection pattern.

### Library & Framework Requirements

- **Rich Console**: Continue using `Console.print()` when output is enabled
- **Typer**: Add `--show-llm-output` as `typer.Option(False, help="...")`
- **No new dependencies required**

### File Structure Requirements

Files to modify:

| File | Change |
|------|--------|
| `src/adw/executors/claude_code.py` | Add `show_llm_output` parameter, conditionally print |
| `src/adw/cli/run.py` | Add `--show-llm-output` CLI option |
| `src/adw/core/phase_runner.py` | Pass flag through to executor |
| `src/adw/core/orchestrator.py` | Pass flag through pipeline |
| `tests/unit/executors/test_claude_code.py` | Add tests for new behavior |

### Testing Requirements

1. **Unit Tests**: Mock console and verify `print()` is NOT called by default
2. **Unit Tests**: Verify `print()` IS called when `show_llm_output=True`
3. **Integration Tests**: Verify full pipeline respects the flag
4. **Existing Tests**: Ensure no regressions in stream capture behavior

---

## Previous Story Intelligence

### Related Stories Completed

- **Story 7-1** (Multi-tier logging): Established the logging architecture
- **Story 7-2** (Verbosity levels): Established `--trace`, `--verbose`, `--quiet` flags
- **Story 7-3** (Capture LLM interactions): Stream logger captures all LLM output to files
- **Story 5-5** (Progress display): Spinner + token count display during execution

### Key Learnings

1. The verbosity system controls `LogManager` console transport, NOT direct executor printing
2. Stream capture is separate from console display - both paths exist
3. Progress display uses `transient=True` which auto-clears - unaffected by this change

---

## Git Intelligence

Recent patterns from Epic 7 implementation:
- Flags are added via `typer.Option()` with help text
- Config propagation follows: CLI → command handler → orchestrator → runner → executor
- Tests mock the executor's dependencies to verify behavior

---

## Code Location Reference

**Primary change location**: `src/adw/executors/claude_code.py:329`

```python
# BEFORE (current - always prints)
if display_text:
    self.console.print(display_text, end="")

# AFTER (conditional printing)
if display_text and self.show_llm_output:
    self.console.print(display_text, end="")
```

**CLI flag location**: `src/adw/cli/run.py` (add near other options)

**Verbosity integration**: Check `Verbosity.TRACE` in the flag resolution

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- All CLI options use `typer.Option()` with explicit defaults
- Boolean flags use `--flag/--no-flag` pattern when sensible
- Configuration flows through RunConfig to components

---

## Dev Notes

- This is a UX fix from issue ISS-001, not a full feature story
- Keep changes minimal - only suppress output, don't refactor
- The `adw logs --follow` capability (Story 7-4) should enable live viewing as alternative
- Test both the default (quiet) and explicit (verbose) modes

### References

- [Source: ISS-001-llm-output-too-verbose-in-terminal.md]
- [Source: claude_code.py:313-333 - streaming output loop]
- [Source: progress.py:146-181 - progress display]
- [Source: stream.py:58-178 - stream capture]

---

## Dev Agent Record

### Context Reference

Issue: `_bmad-output/implementation-artifacts/issues/ISS-001-llm-output-too-verbose-in-terminal.md`

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled during implementation_

### Completion Notes List

_To be filled during implementation_

### File List

_To be filled during implementation_
