# Issue: Init wizard UX improvements - navigation, phase selection, and configuration flow

**ID:** ISS-043
**Severity:** Major
**Type:** UX Issue
**Status:** reported
**Reported:** 2026-01-31
**Reporter:** Ivo

## Related

- **Epic:** Epic 14 (Interactive Init Wizard)
- **Story:** N/A
- **Component:** Init Wizard

## Description

Multiple UX issues in the init wizard affecting usability and configuration flow. This issue consolidates 8 related problems discovered during wizard usage.

## Issues

### 1. Ship Phase Not in Phase Selection
**Current:** `AVAILABLE_PHASES = ["plan", "build", "validate", "document"]` in `phases.py:20`
**Problem:** Ship is handled as a separate wizard step, not selectable alongside other phases for customization
**Fix:** Add `"ship"` to `AVAILABLE_PHASES` and route ship configuration through the phases step when selected

### 2. Ship Settings Don't Follow Common Pattern
**Current:** Ship step (`ship.py:50-109`) jumps directly to ship-specific configs (commands, hooks, PR settings)
**Problem:** No enabled/timeout/input_files prompts like other phases have
**Fix:** In `_configure_phase()` for ship, first prompt for enabled, timeout, input_files (common config) then call existing ship-specific functions

### 3. Navigation Keys (n/b/c) Don't Work
**Current:** Navigation hints shown in welcome (`flow.py:195-198`) but prompts use `rich.prompt.Prompt.ask()` with no navigation handling
**Problem:** Prompts don't check for `n`, `b`, `c` input - they just accept values as literal input
**Fix:** Create a wrapper prompt function that intercepts navigation keys and raises appropriate exceptions/signals to the flow controller

### 4. Project Registration is Placeholder
**Current:** `global_registry.py` collects name but doesn't actually register. The `register_project_in_global_dashboard()` in `summary.py:552` imports `ProjectRegistryManager` but doesn't call it
**Problem:** Registration step collects data but never persists it
**Fix:** Implement actual registration call in summary step after file generation succeeds

### 5. Must Type "other" Before Custom Entry
**Current:** `basics.py:191-196` uses `choices=SUPPORTED_LANGUAGES` which restricts input to the list
**Problem:** Rich's `Prompt.ask()` with `choices` won't accept unlisted values - user must select "other" first, then type custom value
**Fix:** Remove `choices` constraint, show options as numbered list, accept either number or any typed value directly

### 6. Validate Phase Missing Linter Commands
**Current:** `_configure_validate_phase()` in `phases.py:207-249` has no linter config
**Problem:** No option to add linter commands for the validate phase
**Fix:** Add `_prompt_linter_commands()` similar to `_prompt_post_publish_hooks()` - loop to collect multiple linter commands, store in config, and integrate into validate phase implementation

### 7. Auto-merge NO Doesn't Skip Follow-up Questions
**Current:** `_prompt_pr_settings()` in `ship.py:203-220` always asks all 3 questions
**Problem:** If auto-merge is `False`, merge_strategy and delete_branch questions are irrelevant but still asked
**Fix:** Wrap the merge_method and delete_branch prompts in `if merge_on_success:` conditional

### 8. Default Timeouts Too Short
**Current:** `phases.py:23-28`
```python
"plan": 300,      # 5 minutes
"build": 600,     # 10 minutes
"document": 300,  # 5 minutes
```
**Problem:** Default timeouts are too aggressive for typical LLM operations
**Fix:** Change to:
```python
"plan": 900,      # 15 minutes
"build": 1800,    # 30 minutes
"document": 900,  # 15 minutes
```

## Reproduction Steps

1. Run `adw init --wizard`
2. Observe ship phase is not among customizable phases in step 6
3. Try pressing `b` to go back - it's interpreted as input, not navigation
4. Select language, try typing a custom language directly - not allowed
5. Configure ship phase - no enabled/timeout/input_files questions asked
6. Configure validate phase - no linter command option available
7. Say NO to auto-merge - still asked about merge strategy and delete branch
8. Check default timeouts - plan is only 5 minutes

## Expected Behavior

1. Ship should appear in phase selection list
2. Ship configuration should start with common options (enabled, timeout, input files)
3. `n`, `b`, `c` keys should navigate the wizard
4. Project registration should actually register the project
5. Custom language/platform should be directly typeable
6. Validate phase should allow configuring multiple linter commands
7. If auto-merge is NO, skip merge strategy and delete branch questions
8. Default timeouts should be plan:900, build:1800, document:900

## Actual Behavior

See issues 1-8 above.

## Impact

- Users cannot customize ship phase alongside other phases
- Navigation is broken, making the wizard harder to use
- Redundant questions asked even when answers are irrelevant
- Missing functionality (linter commands, project registration)
- Default timeouts may cause premature phase failures

## User Impact Score

- **Users Affected:** All wizard users
- **Frequency:** Every wizard run

## Workaround

- Manually edit generated config files after wizard completes
- Use `--no-interactive` mode and configure manually

## Environment

- **OS:** macOS
- **App Version:** 0.1.42
- **DPI Scaling:** N/A

## Evidence

### Screenshots

N/A

### Logs

N/A

### Screen Recording

N/A

## Resolution

- **Fix Story:** ux-fix-ISS-043-init-wizard-ux-improvements.md
- **Fixed In:** Pending
- **Verified By:** Pending
- **Verified Date:** Pending

## Notes

This is a consolidation of 8 related UX issues. Implementation should address all items to ensure consistent wizard experience.

**Files to modify:**
- `src/adw/cli/wizard/phases.py` - Issues 1, 2, 6, 8
- `src/adw/cli/wizard/ship.py` - Issues 2, 7
- `src/adw/cli/wizard/flow.py` - Issue 3
- `src/adw/cli/wizard/basics.py` - Issue 5
- `src/adw/cli/wizard/global_registry.py` - Issue 4
- `src/adw/cli/wizard/summary.py` - Issue 4
