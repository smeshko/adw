# Issue: Global dashboard exits immediately after display

**ID:** ISS-042
**Severity:** Critical
**Type:** Bug
**Status:** fixed
**Reported:** 2026-01-26
**Reporter:** Ivo

## Related

- **Epic:** 16
- **Story:** 16-5
- **Component:** TUI Dashboard

## Description

The `adw global dashboard` command displays the dashboard once then exits when the user presses an arrow key, returning control to the terminal instead of navigating.

Investigation revealed that arrow key presses are being read as a bare escape character (`\x1b`) instead of the full escape sequence (e.g., `\x1b[A` for up arrow). The bare `\x1b` triggers the quit handler, causing immediate exit. The escape sequence handling is not correctly reading the follow-up bytes that distinguish arrow keys from the Escape key.

## Reproduction Steps

1. Run `adw global dashboard`
2. Dashboard renders and displays correctly
3. Press any arrow key (up/down/left/right)
4. Dashboard immediately exits, returning control to terminal

## Expected Behavior

Dashboard stays interactive, responds to keyboard input (arrow keys for navigation, 'r' for refresh, 'q' to quit), and continues running until user explicitly quits.

## Actual Behavior

Dashboard renders correctly but exits when arrow keys are pressed. Debug investigation confirmed:
- Arrow key press triggers `quit_requested` becoming `True`
- Arrow keys are being read as bare `key='\x1b'` instead of full sequences like `\x1b[A`
- The escape sequence reader is not correctly capturing the `[A`, `[B`, `[C`, `[D` follow-up bytes

## Impact

TUI Dashboard feature (Story 16-5) is completely unusable. Users cannot monitor runs across projects interactively.

## User Impact Score

- **Users Affected:** All users attempting to use global dashboard
- **Frequency:** 100% - occurs on every invocation

## Workaround

None identified.

**Attempted fixes (all failed):**
1. `termios.tcflush()` - Flush stdin buffer after setting cbreak mode to clear stray characters
2. Improved escape sequence handling - Increased timeout from 50ms to 200ms, better CSI sequence parsing
3. Startup grace period - Ignore escape key presses for first 0.5-1.0 seconds

## Environment

- **OS:** macOS (Darwin 25.0.0)
- **App Version:** 0.1.41
- **Terminal:** User's terminal environment (appears to send escape chars during Rich Live init)

## Evidence

### Screenshots

N/A

### Logs

Debug output confirmed: `key='\x1b'` was being read within the first few loop iterations after dashboard startup.

### Screen Recording

N/A

## Resolution

- **Fix Story:** bugfix-ISS-042-global-dashboard-exits-immediately.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

The root cause is that escape sequences from arrow keys are not being read correctly. When an arrow key is pressed, the terminal sends a sequence like `\x1b[A` (3 bytes), but only the first byte (`\x1b`) is being read before the loop continues, causing the escape handler to trigger.

**Potential solutions:**
- Use `select()` or non-blocking read with proper timeout to wait for complete escape sequences
- Switch to a dedicated terminal input library (e.g., `blessed`, `readchar`, or Rich's console input)
- Investigate how Textual handles keyboard input (it successfully handles arrow keys)
- Ensure stdin is in raw mode (not just cbreak) and escape sequence parsing waits for complete sequences
