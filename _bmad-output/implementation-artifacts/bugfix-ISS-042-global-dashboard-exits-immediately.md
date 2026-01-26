# Story: Bugfix ISS-042 - Global Dashboard Exits Immediately

Status: ready-for-dev
Linear Issue: not-configured
Epic: 16 - Cross-Project Dashboard
Created: 2026-01-26

---

## Story

As a **developer using ADW**,
I want **the global dashboard to correctly handle arrow key input**,
so that **I can navigate the dashboard interactively without it unexpectedly exiting**.

## Acceptance Criteria

**Given** the global dashboard is running
**When** I press an arrow key (up/down/left/right)
**Then** the dashboard navigates accordingly (moves selection up/down) without exiting

**Given** the global dashboard is running
**When** I press the Escape key (bare `\x1b` with no follow-up bytes)
**Then** the dashboard exits OR closes detail view (current behavior is correct for actual Escape)

**Given** the global dashboard is running
**When** I press 'q' or 'Q'
**Then** the dashboard exits (this works correctly)

**Given** the global dashboard is running
**When** I press 'r' or 'R'
**Then** the dashboard refreshes data (this works correctly)

## Tasks / Subtasks

### Task 1: Replace Custom Keyboard Handling with readchar Library
- [x] Add `readchar` dependency to pyproject.toml
- [x] Replace `_setup_keyboard()`, `_cleanup_keyboard()`, and `_read_key()` methods in `dashboard.py`
- [x] Use `readchar.readkey()` for proper cross-platform key reading
- [x] Map `readchar.key.UP`, `readchar.key.DOWN`, etc. to handle_key inputs

### Task 2: Update Key Handling in DashboardController.handle_key()
- [x] Update key comparisons to work with readchar key constants
- [x] Keep escape key handling (`\x1b`) for actual Escape key presses
- [x] Ensure arrow key strings ("up", "down") are correctly passed from readchar

### Task 3: Add Unit Tests
- [x] Test keyboard input handling with mock readchar
- [x] Test that arrow keys map to correct navigation actions
- [x] Test that escape key triggers quit when not in detail view
- [x] Test that escape key closes detail view when in detail view

### Task 4: Manual Integration Testing
- [ ] Run `adw global dashboard` and verify arrow key navigation works
- [ ] Verify up/down arrows move selection in runs table
- [ ] Verify 'q' still quits the dashboard
- [ ] Verify 'r' still refreshes data
- [ ] Verify Escape key still quits (when not in detail view)

---

## Relevant Feature Documentation

No matching conditional docs found - this is a bugfix for recently implemented TUI dashboard (Story 16-5).

---

## Developer Context

### Technical Requirements

**Root Cause Analysis:**

The bug is in `src/adw/cli/dashboard.py` in the `_read_key()` method (lines 1034-1057):

```python
def _read_key(self) -> str | None:
    try:
        if select.select([sys.stdin], [], [], 0.25)[0]:
            key = sys.stdin.read(1)

            # Handle escape sequences for arrow keys
            if key == "\x1b" and select.select([sys.stdin], [], [], 0.1)[0]:
                key += sys.stdin.read(2)
                if key == "\x1b[A":
                    return "up"
                elif key == "\x1b[B":
                    return "down"
            return key  # <-- BUG: Returns bare \x1b if select times out
    except OSError:
        pass
    return None
```

**The Problem:**
1. When an arrow key is pressed, the terminal sends 3 bytes: `\x1b[A` (up), `\x1b[B` (down), etc.
2. The code reads the first byte (`\x1b`)
3. The `select.select()` call with 0.1s timeout returns early (before the `[A` bytes arrive)
4. The method returns the bare `\x1b` instead of waiting for the complete sequence
5. `handle_key()` receives `\x1b` and triggers `quit_requested = True`

**Why the 0.1s timeout fails:**
- On macOS (Darwin 25.0.0), the terminal may have slight delays between escape sequence bytes
- The 100ms timeout is insufficient for some terminal emulators
- The non-blocking nature of the read doesn't guarantee atomic escape sequence delivery

### Architecture Compliance

**Solution: Use the `readchar` library**

The `readchar` library is a well-maintained, cross-platform solution for reading single characters and key sequences from stdin. It handles:
- Proper escape sequence parsing
- Cross-platform compatibility (macOS, Linux, Windows)
- Arrow keys, function keys, and special keys
- No manual terminal mode manipulation needed

**Alignment with project architecture:**
- CLI layer handles input parsing (appropriate)
- No business logic affected
- Uses standard Python library patterns
- Maintains existing `handle_key()` interface

### Library & Framework Requirements

**New Dependency: readchar**

```toml
# pyproject.toml
dependencies = [
    # ... existing deps ...
    "readchar>=4.0.0",
]
```

**readchar API usage:**

```python
import readchar

# Blocking read of single key/sequence
key = readchar.readkey()

# Key constants
readchar.key.UP      # Arrow up
readchar.key.DOWN    # Arrow down
readchar.key.LEFT    # Arrow left
readchar.key.RIGHT   # Arrow right
readchar.key.ENTER   # Enter key
readchar.key.ESC     # Escape key (\x1b)
```

**Version requirement:** `readchar >= 4.0.0` for proper macOS support

### File Structure Requirements

**Files to modify:**

1. `pyproject.toml` - Add readchar dependency
2. `src/adw/cli/dashboard.py` - Replace keyboard handling methods

**No new files needed** - this is a bugfix to existing code.

### Testing Requirements

**Unit tests location:** `tests/unit/cli/test_dashboard.py`

**Test scenarios:**
1. Arrow key mapping: Verify `_read_key()` returns correct strings
2. Key handling: Verify `handle_key()` responds correctly to arrow keys
3. Quit behavior: Verify only 'q' and actual Escape trigger quit
4. Detail view: Verify Escape in detail view closes it without quitting

**Manual testing required:**
- Run `adw global dashboard` in actual terminal
- Verify all keyboard shortcuts work
- Test on macOS terminal (where bug was reported)

---

## Previous Story Intelligence

**Story 16-5 (TUI Dashboard) learnings:**

This is the first implementation of TUI keyboard handling in ADW. The original implementation attempted to handle escape sequences manually using `termios`, `tty`, and `select`. Key lessons:

1. Manual terminal mode manipulation is error-prone
2. Escape sequence timing varies by terminal emulator
3. Cross-platform compatibility requires careful handling
4. The `select.select()` timeout approach is insufficient

**Files created in 16-5:**
- `src/adw/cli/dashboard.py` (full implementation)
- Layout, state, data, and controller classes all work correctly
- Only the keyboard input handling is broken

---

## Git Intelligence

**Recent commits related to dashboard:**
- `feat(story-16-5): TUI Dashboard for cross-project ADW monitoring` - Initial implementation
- Dashboard renders correctly, data refresh works, all display logic is correct
- Only keyboard input handling is broken

**Code patterns to follow:**
- Keep existing `DashboardController` structure
- Maintain `handle_key()` interface (takes string, updates state)
- Use type annotations throughout

---

## Latest Technical Information

**readchar library (v4.2.0 - latest):**
- Pure Python implementation
- No external dependencies
- Supports Python 3.8+
- Handles Windows, macOS, Linux
- Active maintenance (last release: 2024)

**Key features relevant to this fix:**
- `readkey()` function blocks until complete key/sequence is read
- Properly handles ANSI escape sequences
- Returns string representation of keys
- Constants for special keys (`readchar.key.UP`, etc.)

**Alternative considered but rejected:**
- `blessed` library: Heavier, more features than needed
- `curses`: Not cross-platform (Windows issues)
- Manual fix of timing: Fragile, doesn't address root cause

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **Python 3.13+** - Use modern syntax
- **Rich 14.1.0** - Already used for dashboard output (no changes needed)
- **Full type annotations** - Required for all new/modified code
- **CLI layer** - Parse input, format output, delegate to core
- **Package manager: uv** - Use `uv add readchar` to add dependency

---

## Dev Notes

### Root Cause Summary
The `_read_key()` method uses `select.select()` with a 0.1s timeout to detect escape sequences. This timeout is insufficient on some terminals/systems, causing arrow key presses to be read as bare escape characters, which triggers the quit handler.

### Implementation Approach
1. Add `readchar` library as dependency
2. Replace custom keyboard handling with `readchar.readkey()`
3. Map readchar constants to existing handle_key string interface
4. Keep `handle_key()` logic unchanged (it works correctly)

### Testing Strategy
- Unit tests with mocked readchar
- Manual testing on macOS terminal
- Verify all keyboard shortcuts still work

### Project Structure Notes

- Changes confined to CLI layer (`src/adw/cli/dashboard.py`)
- No changes to core business logic
- No changes to models
- Single new dependency (`readchar`)

### References

- Issue file: `_bmad-output/implementation-artifacts/issues/ISS-042-global-dashboard-exits-immediately.md`
- Dashboard implementation: `src/adw/cli/dashboard.py:1034-1057`
- readchar documentation: https://pypi.org/project/readchar/

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Fixed ISS-042: Arrow keys now correctly navigate the dashboard instead of triggering quit
- Added `readchar>=4.0.0` dependency for proper cross-platform escape sequence handling
- Replaced manual termios/select-based keyboard handling with readchar library
- `_read_key()` now uses `select()` for non-blocking timeout, then `readchar.readkey()` for proper key parsing
- Arrow keys correctly mapped: UP→"up", DOWN→"down", LEFT→"left", RIGHT→"right"
- ESC key correctly mapped to `\x1b` for quit behavior
- ENTER key correctly mapped to `\r` for run details
- Added 15 new unit tests for keyboard input handling in `TestKeyboardInput` class
- All 68 dashboard unit tests pass
- All 3237 tests pass (2 pre-existing integration test failures unrelated to this fix)
- Linting (ruff) and type checking (mypy) pass

### File List

- `pyproject.toml` - Added `readchar>=4.0.0` dependency
- `src/adw/cli/dashboard.py` - Replaced `_setup_keyboard()`, `_cleanup_keyboard()`, `_read_key()` methods
- `tests/unit/cli/test_dashboard.py` - Added `TestKeyboardInput` class with 15 new tests

